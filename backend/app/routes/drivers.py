# routes/drivers.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import supabase

router = APIRouter()

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

@router.get("/")
async def get_drivers():
    """Get all drivers."""
    result = supabase.table('drivers').select('*').execute()
    return result.data

@router.get("/available")
async def get_available_drivers():
    """Get all available drivers."""
    result = supabase.table('drivers').select('*').in_('status', ['idle', 'en-route']).execute()
    return result.data

@router.get("/{driver_id}")
async def get_driver(driver_id: str):
    """Get driver by ID."""
    result = supabase.table('drivers').select('*').eq('driver_id', driver_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return result.data[0]

@router.put("/{driver_id}/location")
async def update_driver_location(driver_id: str, location: LocationUpdate):
    """Update driver's current location."""
    result = supabase.table('drivers').update({
        'current_latitude': location.latitude,
        'current_longitude': location.longitude
    }).eq('driver_id', driver_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return {"message": "Location updated"}

@router.put("/{driver_id}/status")
async def update_driver_status(driver_id: str, status: str):
    """Update driver's status."""
    valid_statuses = ["idle", "en-route", "occupied", "delivering", "offline"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = supabase.table('drivers').update({'status': status}).eq('driver_id', driver_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return {"message": "Status updated"}