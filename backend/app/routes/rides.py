# routes/rides.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

from ..database import supabase

router = APIRouter()

class RideRequestCreate(BaseModel):
    passenger_id: str
    origin_latitude: float
    origin_longitude: float
    destination_latitude: float
    destination_longitude: float
    pickup_time_window_start: Optional[str] = None
    pickup_time_window_end: Optional[str] = None

@router.post("/request")
async def request_ride(req: RideRequestCreate):
    """Create a new ride request."""
    request_id = str(uuid.uuid4())
    
    data = {
        'request_id': request_id,
        'passenger_id': req.passenger_id,
        'origin_latitude': req.origin_latitude,
        'origin_longitude': req.origin_longitude,
        'destination_latitude': req.destination_latitude,
        'destination_longitude': req.destination_longitude,
        'status': 'pending'
    }
    
    result = supabase.table('ride_requests').insert(data).execute()
    
    return result.data[0] if result.data else {"request_id": request_id}

@router.get("/pending")
async def get_pending_rides():
    """Get all pending ride requests."""
    result = supabase.table('ride_requests').select('*').eq('status', 'pending').execute()
    return result.data

@router.get("/{request_id}")
async def get_ride(request_id: str):
    """Get ride request by ID."""
    result = supabase.table('ride_requests').select('*').eq('request_id', request_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return result.data[0]

@router.put("/{request_id}/status")
async def update_ride_status(request_id: str, status: str):
    """Update ride request status."""
    valid_statuses = ["pending", "matched", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = supabase.table('ride_requests').update({'status': status}).eq('request_id', request_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return {"message": "Status updated"}