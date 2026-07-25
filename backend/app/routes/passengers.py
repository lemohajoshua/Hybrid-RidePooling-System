# routes/passengers.py
from fastapi import APIRouter, HTTPException

from ..database import supabase

router = APIRouter()


def _enrich_with_pool_partner(ride: dict) -> dict:
    ride = dict(ride)
    if ride.get('pool_group_id'):
        partner = supabase.table('ride_requests').select('passenger_name, passenger_id') \
            .eq('pool_group_id', ride['pool_group_id']) \
            .neq('request_id', ride['request_id']) \
            .execute()
        if partner.data:
            ride['pool_partner_name'] = partner.data[0].get('passenger_name')
    return ride


@router.get("/")
async def get_passengers():
    result = supabase.table('passengers').select('*').execute()
    return result.data


@router.get("/{passenger_id}")
async def get_passenger(passenger_id: str):
    result = supabase.table('passengers').select('*').eq('passenger_id', passenger_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return result.data[0]


@router.get("/{passenger_id}/wallet")
async def get_passenger_wallet(passenger_id: str):
    result = supabase.table('passengers').select('wallet_balance, avg_rating, rating_count').eq('passenger_id', passenger_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return result.data[0]


@router.get("/{passenger_id}/rides")
async def get_passenger_rides(passenger_id: str):
    """Full ride history for a passenger, most recent first."""
    result = supabase.table('ride_requests').select('*') \
        .eq('passenger_id', passenger_id) \
        .order('request_time', desc=True) \
        .execute()
    return result.data


@router.get("/{passenger_id}/active-ride")
async def get_passenger_active_ride(passenger_id: str):
    """
    The passenger's current in-flight ride request, if any:
    - 'pending_pool'  -> waiting for another passenger to be matched with
    - 'requested'     -> matched/assigned, waiting on the driver's decision
    - 'accepted'      -> driver is on the way
    Polled by the passenger page so it can update without a page refresh.
    """
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
async def get_passenger_stats(passenger_id: str):
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
