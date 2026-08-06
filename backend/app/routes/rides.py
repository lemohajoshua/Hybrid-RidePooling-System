# routes/rides.py
from fastapi import APIRouter, HTTPException, Depends
import uuid
from datetime import datetime, timezone

from ..database import supabase
from ..models import RideRequestCreate, RideDecision
from ..algorithms import haversine, InsertionHeuristic
from ..token_auth import get_current_user, require_self
from ..audit import log_action

router = APIRouter()

LEGACY_STATUSES = ["pending", "matched", "completed", "cancelled"]
ALL_STATUSES = LEGACY_STATUSES + ["requested", "accepted", "rejected", "pending_pool"]

insertion_heuristic = InsertionHeuristic(max_detour_factor=1.20)

# Fare model shared with the frontend's estimate (assets/js/... calculates the
# same numbers for display before submitting - this is the authoritative value).
BASE_FARE = 800
PER_KM_RATE = 80
POOL_DISCOUNT = 0.70


def calculate_fare(origin, destination, is_pooled: bool) -> float:
    distance_km = haversine(origin[0], origin[1], destination[0], destination[1])
    fare = BASE_FARE + distance_km * PER_KM_RATE
    if is_pooled:
        fare *= POOL_DISCOUNT
    return round(fare, 2)


def _enrich_with_pool_partner(ride: dict) -> dict:
    """Attach the other passenger's name if this ride is part of a pool."""
    ride = dict(ride)
    if ride.get('pool_group_id'):
        partner = supabase.table('ride_requests').select('passenger_name, passenger_id') \
            .eq('pool_group_id', ride['pool_group_id']) \
            .neq('request_id', ride['request_id']) \
            .execute()
        if partner.data:
            ride['pool_partner_name'] = partner.data[0].get('passenger_name')
    return ride


# ================================================================
# CREATE A RIDE REQUEST
# ================================================================

@router.post("/request")
async def request_ride(req: RideRequestCreate):
    """
    Create a new ride request.

    - Solo (`is_pooled=False`) with `driver_id` -> sent straight to that
      driver (status='requested').
    - Pooled (`is_pooled=True`) with `driver_id` -> the passenger has picked
      a driver and is opening a pool that a second passenger can see and
      join (status='pending_pool'). The driver is NOT notified yet - only
      once someone joins (see /join below) does it become 'requested'.
    - No `driver_id` at all -> legacy unassigned 'pending' flow, used only
      by the automated /simulation engine, not the real passenger flow.
    """
    request_id = str(uuid.uuid4())
    origin = (req.origin_latitude, req.origin_longitude)
    destination = (req.destination_latitude, req.destination_longitude)
    fare = calculate_fare(origin, destination, req.is_pooled)

    data = {
        'request_id': request_id,
        'passenger_id': req.passenger_id,
        'passenger_name': req.passenger_name,
        'origin_latitude': req.origin_latitude,
        'origin_longitude': req.origin_longitude,
        'destination_latitude': req.destination_latitude,
        'destination_longitude': req.destination_longitude,
        'is_pooled': req.is_pooled,
        'fare': fare,
        'status': 'pending'
    }

    if req.driver_id:
        driver_result = supabase.table('drivers').select('*').eq('driver_id', req.driver_id).execute()
        if not driver_result.data:
            raise HTTPException(status_code=404, detail="Driver not found")
        driver = driver_result.data[0]
        if not driver.get('is_online') or driver.get('status') != 'idle':
            raise HTTPException(status_code=409, detail="That driver is no longer available - please pick another driver")

        data['driver_id'] = req.driver_id
        data['status'] = 'pending_pool' if req.is_pooled else 'requested'
        result = supabase.table('ride_requests').insert(data).execute()
        return result.data[0] if result.data else data

    # --- Legacy unassigned request (used by the simulation engine) ---
    result = supabase.table('ride_requests').insert(data).execute()
    return result.data[0] if result.data else data


@router.get("/open-pools")
async def get_open_pools(exclude_passenger_id: str = None):
    """
    Pool requests that already have a driver chosen and are waiting for a
    second passenger to join. Shown to other passengers as "pool rides you
    can join" instead of the system silently picking a partner for them.
    """
    query = supabase.table('ride_requests').select('*').eq('status', 'pending_pool')
    result = query.execute()
    pools = result.data or []
    if exclude_passenger_id:
        pools = [p for p in pools if p['passenger_id'] != exclude_passenger_id]
    return pools


@router.put("/{request_id}/join")
async def join_pool(request_id: str, req: RideRequestCreate):
    """
    A second passenger joins an existing open pool. Algorithm 1 (Insertion
    Heuristic) checks that adding this passenger's pickup/dropoff to the
    first passenger's route + driver is actually feasible (within the
    detour threshold) before allowing the join - so this is still
    algorithm-validated, just triggered by the passenger's choice instead
    of happening silently.
    """
    target_result = supabase.table('ride_requests').select('*').eq('request_id', request_id).execute()
    if not target_result.data:
        raise HTTPException(status_code=404, detail="That pool ride no longer exists")
    target = target_result.data[0]

    if target.get('status') != 'pending_pool' or not target.get('driver_id'):
        raise HTTPException(status_code=409, detail="This pool ride is no longer open - please pick another")
    if target['passenger_id'] == req.passenger_id:
        raise HTTPException(status_code=400, detail="You can't join your own pool request")

    driver_result = supabase.table('drivers').select('*').eq('driver_id', target['driver_id']).execute()
    if not driver_result.data:
        raise HTTPException(status_code=404, detail="Driver for this pool is no longer available")
    driver = driver_result.data[0]
    if driver.get('current_latitude') is None or driver.get('current_longitude') is None:
        raise HTTPException(status_code=409, detail="Can't verify this route right now - please try another pool")

    driver_position = (driver['current_latitude'], driver['current_longitude'])
    existing_route = [
        (target['origin_latitude'], target['origin_longitude']),
        (target['destination_latitude'], target['destination_longitude'])
    ]
    new_pickup = (req.origin_latitude, req.origin_longitude)
    new_dropoff = (req.destination_latitude, req.destination_longitude)

    match_result = insertion_heuristic.find_match(existing_route, driver_position, new_pickup, new_dropoff)
    if match_result is None:
        raise HTTPException(status_code=409, detail="Your route is too far out of the way to join this pool - try another one or go solo")

    pool_group_id = str(uuid.uuid4())
    now_fare = calculate_fare(new_pickup, new_dropoff, True)

    supabase.table('ride_requests').update({
        'status': 'requested',
        'pool_group_id': pool_group_id
    }).eq('request_id', target['request_id']).execute()

    joiner_data = {
        'request_id': str(uuid.uuid4()),
        'passenger_id': req.passenger_id,
        'passenger_name': req.passenger_name,
        'origin_latitude': req.origin_latitude,
        'origin_longitude': req.origin_longitude,
        'destination_latitude': req.destination_latitude,
        'destination_longitude': req.destination_longitude,
        'is_pooled': True,
        'fare': now_fare,
        'driver_id': target['driver_id'],
        'status': 'requested',
        'pool_group_id': pool_group_id
    }
    result = supabase.table('ride_requests').insert(joiner_data).execute()

    return result.data[0] if result.data else joiner_data


@router.put("/{request_id}/cancel")
async def cancel_ride(request_id: str):
    """
    Cancel a ride request - whether it's still waiting for a pool match,
    waiting on a driver's decision, or already accepted (e.g. the driver is
    taking too long and the passenger wants to give up and try again).

    If it was already 'accepted', the assigned driver is freed back to
    'idle' so they can take new requests - unless they still have another
    active leg of the same pooled trip, in which case they stay busy with
    that.
    """
    ride_result = supabase.table('ride_requests').select('*').eq('request_id', request_id).execute()
    if not ride_result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    ride = ride_result.data[0]

    if ride.get('status') in ('completed', 'cancelled', 'rejected'):
        raise HTTPException(status_code=409, detail=f"This ride is already {ride.get('status')} and can't be cancelled")

    was_accepted = ride.get('status') == 'accepted'
    driver_id = ride.get('driver_id')

    supabase.table('ride_requests').update({'status': 'cancelled'}).eq('request_id', request_id).execute()

    if was_accepted and driver_id:
        other_active = supabase.table('ride_requests').select('request_id') \
            .eq('driver_id', driver_id).eq('status', 'accepted') \
            .neq('request_id', request_id).execute()
        if not other_active.data:
            driver_result = supabase.table('drivers').select('is_online').eq('driver_id', driver_id).execute()
            if driver_result.data:
                new_status = 'idle' if driver_result.data[0].get('is_online') else 'offline'
                supabase.table('drivers').update({'status': new_status}).eq('driver_id', driver_id).execute()

    log_action(ride.get('passenger_id'), 'passenger', 'ride_cancelled', {'request_id': request_id, 'was_accepted': was_accepted})
    return {"message": "Cancelled", "was_accepted": was_accepted}


@router.get("/pending")
async def get_pending_rides():
    """Unassigned ride requests - used by the automated simulation."""
    result = supabase.table('ride_requests').select('*').eq('status', 'pending').execute()
    return result.data


@router.get("/driver/{driver_id}/active")
async def get_driver_active_ride(driver_id: str, current_user: dict = Depends(get_current_user)):
    """
    The driver's current accepted-and-in-progress ride, if any. Polled by
    the driver page so it notices if a passenger cancels after acceptance
    (e.g. the driver was taking too long) - including the pooled case,
    where cancelling one passenger's leg should leave the driver still
    showing the other passenger's leg as active, not just going blank.
    """
    require_self(current_user, driver_id, expected_role='driver')
    result = supabase.table('ride_requests').select('*') \
        .eq('driver_id', driver_id).eq('status', 'accepted') \
        .order('responded_at', desc=True).limit(1).execute()
    if not result.data:
        return {"has_active_ride": False, "ride": None}
    return {"has_active_ride": True, "ride": _enrich_with_pool_partner(result.data[0])}


@router.get("/driver/{driver_id}/incoming")
async def get_incoming_requests_for_driver(driver_id: str, current_user: dict = Depends(get_current_user)):
    """Ride requests currently awaiting this driver's decision."""
    require_self(current_user, driver_id, expected_role='driver')
    result = supabase.table('ride_requests').select('*') \
        .eq('driver_id', driver_id) \
        .eq('status', 'requested') \
        .order('request_time', desc=True) \
        .execute()
    return [_enrich_with_pool_partner(r) for r in result.data]


@router.get("/{request_id}")
async def get_ride(request_id: str):
    result = supabase.table('ride_requests').select('*').eq('request_id', request_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return _enrich_with_pool_partner(result.data[0])


@router.put("/{request_id}/status")
async def update_ride_status(request_id: str, status: str):
    """Manually set a ride request's status (admin/simulation use)."""
    if status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    result = supabase.table('ride_requests').update({'status': status}).eq('request_id', request_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return {"message": "Status updated"}


@router.put("/{request_id}/respond")
async def respond_to_ride(request_id: str, decision: RideDecision, current_user: dict = Depends(get_current_user)):
    """
    A driver accepts or rejects a ride request. If it's part of a pool
    (pool_group_id set), the same decision is applied to both passengers'
    requests at once - they were matched together, so they're accepted or
    declined together.

    The acting driver is taken from the verified token, not from
    decision.driver_id - this avoids a confusing "another user's behalf"
    error if the browser's cached driver_id is stale (e.g. multiple test
    accounts logged in across tabs of the same browser, which share
    localStorage). If the token doesn't belong to the driver this ride
    was actually sent to, that now surfaces as the correct, clearer error.
    """
    if current_user.get('role') != 'driver':
        raise HTTPException(status_code=403, detail="This action requires a driver account")
    driver_id = current_user['id']

    ride_result = supabase.table('ride_requests').select('*').eq('request_id', request_id).execute()
    if not ride_result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    ride = ride_result.data[0]

    if ride.get('driver_id') != driver_id:
        raise HTTPException(status_code=403, detail="This ride request was not sent to this driver - you may be logged in as a different driver in this browser tab, try logging in again")
    if ride.get('status') != 'requested':
        raise HTTPException(status_code=409, detail=f"This request has already been {ride.get('status')}")
    if decision.decision not in ('accept', 'reject'):
        raise HTTPException(status_code=400, detail="decision must be 'accept' or 'reject'")

    new_status = 'accepted' if decision.decision == 'accept' else 'rejected'
    now = datetime.now(timezone.utc).isoformat()

    ids_to_update = [request_id]
    if ride.get('pool_group_id'):
        pool_mates = supabase.table('ride_requests').select('request_id') \
            .eq('pool_group_id', ride['pool_group_id']) \
            .eq('status', 'requested') \
            .execute()
        ids_to_update = [r['request_id'] for r in pool_mates.data]

    for rid in ids_to_update:
        supabase.table('ride_requests').update({
            'status': new_status,
            'responded_at': now
        }).eq('request_id', rid).execute()

    if decision.decision == 'accept':
        supabase.table('drivers').update({'status': 'en-route'}).eq('driver_id', driver_id).execute()

    log_action(driver_id, 'driver', f'ride_{new_status}', {'request_id': request_id, 'pooled_request_ids': ids_to_update})
    return {"message": f"Ride {new_status}", "request_id": request_id, "status": new_status, "pooled_request_ids": ids_to_update}


@router.put("/{request_id}/complete")
async def complete_ride(request_id: str, current_user: dict = Depends(get_current_user)):
    """
    Driver marks a ride as completed. This is where the simple in-app
    payment happens: the stored fare is deducted from the passenger's
    wallet and credited to the driver's earnings, and a payment record is
    written. (This is a simulated wallet, not a real payment gateway -
    there's no card/bank integration here.) If the ride was pooled, the
    paired request is completed and paid the same way.

    The acting driver is taken from the verified token (see the note on
    /respond above for why).
    """
    if current_user.get('role') != 'driver':
        raise HTTPException(status_code=403, detail="This action requires a driver account")
    driver_id = current_user['id']

    ride_result = supabase.table('ride_requests').select('*').eq('request_id', request_id).execute()
    if not ride_result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    ride = ride_result.data[0]

    if ride.get('driver_id') != driver_id:
        raise HTTPException(status_code=403, detail="This ride is not assigned to this driver - you may be logged in as a different driver in this browser tab, try logging in again")
    if ride.get('status') != 'accepted':
        raise HTTPException(status_code=409, detail="Only an accepted ride can be completed")

    rides_to_complete = [ride]
    if ride.get('pool_group_id'):
        pool_mates = supabase.table('ride_requests').select('*') \
            .eq('pool_group_id', ride['pool_group_id']).execute()
        rides_to_complete = pool_mates.data

    now = datetime.now(timezone.utc).isoformat()
    total_earned = 0.0

    for r in rides_to_complete:
        fare = r.get('fare') or 0
        supabase.table('ride_requests').update({
            'status': 'completed',
            'completed_at': now
        }).eq('request_id', r['request_id']).execute()

        passenger_result = supabase.table('passengers').select('wallet_balance').eq('passenger_id', r['passenger_id']).execute()
        if passenger_result.data:
            new_balance = (passenger_result.data[0].get('wallet_balance') or 0) - fare
            supabase.table('passengers').update({'wallet_balance': new_balance}).eq('passenger_id', r['passenger_id']).execute()

        supabase.table('payments').insert({
            'payment_id': str(uuid.uuid4()),
            'request_id': r['request_id'],
            'passenger_id': r['passenger_id'],
            'driver_id': driver_id,
            'amount': fare,
            'status': 'completed'
        }).execute()

        total_earned += fare

    driver_result = supabase.table('drivers').select('total_earnings, is_online').eq('driver_id', driver_id).execute()
    if driver_result.data:
        d = driver_result.data[0]
        new_earnings = (d.get('total_earnings') or 0) + total_earned
        new_status = 'idle' if d.get('is_online') else 'offline'
        supabase.table('drivers').update({
            'total_earnings': new_earnings,
            'status': new_status
        }).eq('driver_id', driver_id).execute()

    log_action(driver_id, 'driver', 'ride_completed', {'request_ids': [r['request_id'] for r in rides_to_complete], 'earned': total_earned})
    return {"message": "Ride completed", "earned": total_earned, "request_ids": [r['request_id'] for r in rides_to_complete]}
