# routes/rides.py
from fastapi import APIRouter, HTTPException, Depends
import uuid
from datetime import datetime, timezone

from ..database import supabase
from ..models import RideRequestCreate, RideDecision
from ..algorithms import haversine, InsertionHeuristic
from ..token_auth import get_current_user, require_self

router = APIRouter()

LEGACY_STATUSES = ["pending", "matched", "completed", "cancelled"]
ALL_STATUSES = LEGACY_STATUSES + ["requested", "accepted", "rejected", "pending_pool"]

insertion_heuristic = InsertionHeuristic(max_detour_factor=1.20)

# Fare model shared with the frontend's estimate (assets/js/... calculates the
# same numbers for display before submitting - this is the authoritative value).
BASE_FARE = 800
PER_KM_RATE = 80
POOL_DISCOUNT = 0.70
POOL_MATCH_DEST_RADIUS_KM = 2.0  # "similar destination" tolerance for Algorithm 1


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

    - `driver_id` provided -> sent straight to that driver (status='requested').
    - `is_pooled=True` and no `driver_id` -> real auto-matching:
      Algorithm 1 (Insertion Heuristic) is run against any other passenger
      already waiting for a pool match with a similar destination. If a
      feasible shared route + an available driver is found, both requests
      are matched to that driver in one shot (status='requested',
      pool_group_id set on both). If not, this request is parked as
      'pending_pool' until either a match arrives or it's cancelled.
    - `is_pooled=False` and no `driver_id` -> old unassigned 'pending' flow
      (used by the automated /simulation engine).
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

    # --- Explicit driver chosen by the passenger ---
    if req.driver_id:
        driver_result = supabase.table('drivers').select('*').eq('driver_id', req.driver_id).execute()
        if not driver_result.data:
            raise HTTPException(status_code=404, detail="Driver not found")
        driver = driver_result.data[0]
        if not driver.get('is_online') or driver.get('status') != 'idle':
            raise HTTPException(status_code=409, detail="That driver is no longer available - please pick another driver")
        data['driver_id'] = req.driver_id
        data['status'] = 'requested'
        result = supabase.table('ride_requests').insert(data).execute()
        return result.data[0] if result.data else data

    # --- Auto-matched pooling ---
    if req.is_pooled:
        waiting = supabase.table('ride_requests').select('*') \
            .eq('status', 'pending_pool') \
            .eq('is_pooled', True) \
            .neq('passenger_id', req.passenger_id) \
            .execute()

        match_candidate = None
        for candidate in (waiting.data or []):
            cand_dest = (candidate['destination_latitude'], candidate['destination_longitude'])
            if haversine(cand_dest[0], cand_dest[1], destination[0], destination[1]) <= POOL_MATCH_DEST_RADIUS_KM:
                match_candidate = candidate
                break

        if match_candidate:
            # Find the nearest available driver to run Algorithm 1 against
            drivers_result = supabase.table('drivers').select('*') \
                .eq('is_online', True).eq('status', 'idle').execute()

            mid_lat = (origin[0] + match_candidate['origin_latitude']) / 2
            mid_lng = (origin[1] + match_candidate['origin_longitude']) / 2

            best_driver = None
            best_dist = float('inf')
            for d in (drivers_result.data or []):
                dist = haversine(d['current_latitude'], d['current_longitude'], mid_lat, mid_lng)
                if dist < best_dist:
                    best_dist = dist
                    best_driver = d

            if best_driver:
                driver_position = (best_driver['current_latitude'], best_driver['current_longitude'])
                existing_route = [
                    (match_candidate['origin_latitude'], match_candidate['origin_longitude']),
                    (match_candidate['destination_latitude'], match_candidate['destination_longitude'])
                ]
                match_result = insertion_heuristic.find_match(existing_route, driver_position, origin, destination)

                if match_result is not None:
                    pool_group_id = str(uuid.uuid4())

                    # Update the passenger who was already waiting
                    supabase.table('ride_requests').update({
                        'driver_id': best_driver['driver_id'],
                        'status': 'requested',
                        'pool_group_id': pool_group_id
                    }).eq('request_id', match_candidate['request_id']).execute()

                    # Insert this passenger, pre-matched to the same driver
                    data['driver_id'] = best_driver['driver_id']
                    data['status'] = 'requested'
                    data['pool_group_id'] = pool_group_id
                    result = supabase.table('ride_requests').insert(data).execute()
                    return result.data[0] if result.data else data

        # No match yet - park this request and wait for one
        data['status'] = 'pending_pool'
        result = supabase.table('ride_requests').insert(data).execute()
        return result.data[0] if result.data else data

    # --- Legacy unassigned request (used by the simulation engine) ---
    result = supabase.table('ride_requests').insert(data).execute()
    return result.data[0] if result.data else data


@router.put("/{request_id}/cancel")
async def cancel_ride(request_id: str):
    """Cancel a request that's still pending/pending_pool/requested (e.g. a
    passenger waiting for a pool match who wants to book solo instead)."""
    result = supabase.table('ride_requests').update({'status': 'cancelled'}).eq('request_id', request_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return {"message": "Cancelled"}


@router.get("/pending")
async def get_pending_rides():
    """Unassigned ride requests - used by the automated simulation."""
    result = supabase.table('ride_requests').select('*').eq('status', 'pending').execute()
    return result.data


@router.get("/driver/{driver_id}/incoming")
async def get_incoming_requests_for_driver(driver_id: str):
    """Ride requests currently awaiting this driver's decision."""
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
    """
    require_self(current_user, decision.driver_id, expected_role='driver')

    ride_result = supabase.table('ride_requests').select('*').eq('request_id', request_id).execute()
    if not ride_result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    ride = ride_result.data[0]

    if ride.get('driver_id') != decision.driver_id:
        raise HTTPException(status_code=403, detail="This ride request was not sent to this driver")
    if ride.get('status') != 'requested':
        raise HTTPException(status_code=409, detail=f"This request has already been {ride.get('status')}")
    if decision.decision not in ('accept', 'reject'):
        raise HTTPException(status_code=400, detail="decision must be 'accept' or 'reject'")

    new_status = 'accepted' if decision.decision == 'accept' else 'rejected'
    now = datetime.now(timezone.utc).isoformat()

    ids_to_update = [request_id]
    if ride.get('pool_group_id'):
        pool_mates = supabase.table('ride_requests').select('request_id') \
            .eq('pool_group_id', ride['pool_group_id']).execute()
        ids_to_update = [r['request_id'] for r in pool_mates.data]

    for rid in ids_to_update:
        supabase.table('ride_requests').update({
            'status': new_status,
            'responded_at': now
        }).eq('request_id', rid).execute()

    if decision.decision == 'accept':
        supabase.table('drivers').update({'status': 'en-route'}).eq('driver_id', decision.driver_id).execute()

    return {"message": f"Ride {new_status}", "request_id": request_id, "status": new_status, "pooled_request_ids": ids_to_update}


@router.put("/{request_id}/complete")
async def complete_ride(request_id: str, driver_id: str, current_user: dict = Depends(get_current_user)):
    """
    Driver marks a ride as completed. This is where the simple in-app
    payment happens: the stored fare is deducted from the passenger's
    wallet and credited to the driver's earnings, and a payment record is
    written. (This is a simulated wallet, not a real payment gateway -
    there's no card/bank integration here.) If the ride was pooled, the
    paired request is completed and paid the same way.
    """
    require_self(current_user, driver_id, expected_role='driver')

    ride_result = supabase.table('ride_requests').select('*').eq('request_id', request_id).execute()
    if not ride_result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    ride = ride_result.data[0]

    if ride.get('driver_id') != driver_id:
        raise HTTPException(status_code=403, detail="This ride is not assigned to this driver")
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

    return {"message": "Ride completed", "earned": total_earned, "request_ids": [r['request_id'] for r in rides_to_complete]}
