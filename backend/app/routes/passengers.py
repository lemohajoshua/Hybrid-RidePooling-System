# routes/passengers.py
from fastapi import APIRouter, HTTPException, Depends

from ..database import supabase
from ..token_auth import get_current_user, require_self

router = APIRouter()


def _enrich_with_pool_partner(ride: dict) -> dict:
    ride = dict(ride)
    if ride.get('pool_group_id'):
        partner = supabase.table('ride_requests').select('passenger_name, passenger_id, status') \
            .eq('pool_group_id', ride['pool_group_id']) \
            .neq('request_id', ride['request_id']) \
            .execute()
        if partner.data:
            ride['pool_partner_name'] = partner.data[0].get('passenger_name')
            ride['pool_partner_status'] = partner.data[0].get('status')
    return ride


@router.get("/{passenger_id}")
async def get_passenger(passenger_id: str, current_user: dict = Depends(get_current_user)):
    """A passenger's own profile. Requires being logged in as that passenger -
    this is personal data (name, phone, email), not something another
    passenger or a driver should be able to look up by ID."""
    require_self(current_user, passenger_id, expected_role='passenger')
    result = supabase.table('passengers').select('*').eq('passenger_id', passenger_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return result.data[0]


@router.get("/{passenger_id}/wallet")
async def get_passenger_wallet(passenger_id: str, current_user: dict = Depends(get_current_user)):
    require_self(current_user, passenger_id, expected_role='passenger')
    result = supabase.table('passengers').select('wallet_balance, avg_rating, rating_count').eq('passenger_id', passenger_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return result.data[0]


@router.get("/{passenger_id}/rides")
async def get_passenger_rides(passenger_id: str, current_user: dict = Depends(get_current_user)):
    """Full ride history for a passenger, most recent first."""
    require_self(current_user, passenger_id, expected_role='passenger')
    result = supabase.table('ride_requests').select('*') \
        .eq('passenger_id', passenger_id) \
        .order('request_time', desc=True) \
        .execute()
    return result.data


@router.get("/{passenger_id}/active-ride")
async def get_passenger_active_ride(passenger_id: str, current_user: dict = Depends(get_current_user)):
    """
    The passenger's current in-flight ride request, if any:
    - 'pending_pool'  -> waiting for another passenger to be matched with
    - 'requested'     -> matched/assigned, waiting on the driver's decision
    - 'accepted'      -> driver is on the way
    Polled by the passenger page so it can update without a page refresh.
    """
    require_self(current_user, passenger_id, expected_role='passenger')
    result = supabase.table('ride_requests').select('*') \
        .eq('passenger_id', passenger_id) \
        .in_('status', ['pending_pool', 'requested', 'accepted']) \
        .order('request_time', desc=True) \
        .limit(1) \
        .execute()

    if not result.data:
        return {"has_active_ride": False, "ride": None}

    return {"has_active_ride": True, "ride": _enrich_with_pool_partner(result.data[0])}


@router.get("/{passenger_id}/stats")
async def get_passenger_stats(passenger_id: str, current_user: dict = Depends(get_current_user)):
    require_self(current_user, passenger_id, expected_role='passenger')
    passenger_result = supabase.table('passengers').select('*').eq('passenger_id', passenger_id).execute()
    if not passenger_result.data:
        raise HTTPException(status_code=404, detail="Passenger not found")

    rides_result = supabase.table('ride_requests').select('*').eq('passenger_id', passenger_id).execute()
    rides = rides_result.data

    completed = [r for r in rides if r.get('status') == 'completed']
    pooled = [r for r in rides if r.get('is_pooled')]

    return {
        "passenger": passenger_result.data[0],
        "stats": {
            "total_rides": len(rides),
            "completed_rides": len(completed),
            "pooled_rides": len(pooled)
        }
    }
