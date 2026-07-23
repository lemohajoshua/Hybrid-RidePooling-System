# routes/passengers.py
from fastapi import APIRouter, HTTPException

from ..database import supabase

router = APIRouter()

@router.get("/")
async def get_passengers():
    """Get all passengers."""
    result = supabase.table('passengers').select('*').execute()
    return result.data

@router.get("/{passenger_id}")
async def get_passenger(passenger_id: str):
    """Get passenger by ID."""
    result = supabase.table('passengers').select('*').eq('passenger_id', passenger_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return result.data[0]

@router.get("/{passenger_id}/rides")
async def get_passenger_rides(passenger_id: str):
    """Get all ride requests for a passenger."""
    result = supabase.table('ride_requests').select('*').eq('passenger_id', passenger_id).execute()
    return result.data