# routes/drivers.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..database import supabase

router = APIRouter()


class LocationUpdate(BaseModel):
    latitude: float
    longitude: float


# ================================================================
# GET ALL DRIVERS
# ================================================================

@router.get("/")
async def get_drivers():
    """Get all drivers."""
    result = supabase.table('drivers').select('*').execute()
    return result.data


# ================================================================
# GET AVAILABLE DRIVERS (for passenger search)
# ================================================================

@router.get("/available")
async def get_available_drivers():
    """Get all available drivers (status: idle or en-route)."""
    result = supabase.table('drivers').select('*').in_('status', ['idle', 'en-route']).execute()
    return result.data


# ================================================================
# GET SINGLE DRIVER
# ================================================================

@router.get("/{driver_id}")
async def get_driver(driver_id: str):
    """Get driver by ID."""
    result = supabase.table('drivers').select('*').eq('driver_id', driver_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return result.data[0]


# ================================================================
# GET DRIVER STATS
# ================================================================

@router.get("/{driver_id}/stats")
async def get_driver_stats(driver_id: str):
    """Get statistics for a specific driver."""
    # Get driver info
    driver_result = supabase.table('drivers').select('*').eq('driver_id', driver_id).execute()
    if not driver_result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    driver = driver_result.data[0]
    
    # Get all trips for this driver
    trips_result = supabase.table('trips').select('*').eq('driver_id', driver_id).execute()
    trips = trips_result.data
    
    # Completed trips count
    completed_trips = [t for t in trips if t.get('status') == 'completed']
    completed_count = len(completed_trips)
    
    # Calculate total earnings from performance metrics
    total_earnings = 0
    for trip in trips:
        metrics_result = supabase.table('performance_metrics').select('driver_earnings').eq('trip_id', trip['trip_id']).execute()
        if metrics_result.data:
            total_earnings += metrics_result.data[0].get('driver_earnings', 0)
    
    # Get available deliveries (pending)
    deliveries_result = supabase.table('delivery_tasks').select('*').eq('status', 'pending').execute()
    available_deliveries = len(deliveries_result.data)
    
    # Get current trip (if any)
    current_trip = None
    for trip in trips:
        if trip.get('status') in ['planned', 'in_progress']:
            current_trip = trip
            break
    
    return {
        "driver": driver,
        "stats": {
            "total_earnings": round(total_earnings, 2),
            "completed_trips": completed_count,
            "available_deliveries": available_deliveries,
            "current_trip": current_trip
        }
    }


# ================================================================
# GET DRIVER'S CURRENT TRIP
# ================================================================

@router.get("/{driver_id}/current-trip")
async def get_driver_current_trip(driver_id: str):
    """Get the driver's current active trip."""
    trips_result = supabase.table('trips').select('*').eq('driver_id', driver_id).execute()
    trips = trips_result.data
    
    # Find active trip (planned or in_progress)
    active_trip = None
    for trip in trips:
        if trip.get('status') in ['planned', 'in_progress']:
            active_trip = trip
            break
    
    if not active_trip:
        return {"has_active_trip": False, "trip": None}
    
    # Get ride requests for this trip
    request_ids = active_trip.get('request_ids', [])
    ride_details = []
    for req_id in request_ids:
        ride_result = supabase.table('ride_requests').select('*').eq('request_id', req_id).execute()
        if ride_result.data:
            ride_details.append(ride_result.data[0])
    
    # Get delivery tasks for this trip
    task_ids = active_trip.get('task_ids', [])
    task_details = []
    for task_id in task_ids:
        task_result = supabase.table('delivery_tasks').select('*').eq('task_id', task_id).execute()
        if task_result.data:
            task_details.append(task_result.data[0])
    
    return {
        "has_active_trip": True,
        "trip": active_trip,
        "rides": ride_details,
        "tasks": task_details
    }


# ================================================================
# UPDATE DRIVER LOCATION
# ================================================================

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


# ================================================================
# UPDATE DRIVER STATUS (IMPORTANT FOR ONLINE/OFFLINE TOGGLE)
# ================================================================

@router.put("/{driver_id}/status")
async def update_driver_status(driver_id: str, status: str):
    """Update driver's status.
    
    Valid statuses:
    - idle: Online and available for rides
    - en-route: On the way to pickup
    - occupied: Currently with passenger(s)
    - delivering: Currently delivering a package
    - offline: Offline, not accepting rides
    """
    valid_statuses = ["idle", "en-route", "occupied", "delivering", "offline"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Update the driver's status in the database
    result = supabase.table('drivers').update({'status': status}).eq('driver_id', driver_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    return {
        "message": "Status updated successfully",
        "driver_id": driver_id,
        "new_status": status
    }


# ================================================================
# UPDATE DRIVER CAPACITY
# ================================================================

@router.put("/{driver_id}/capacity")
async def update_driver_capacity(driver_id: str, max_passengers: int):
    """Update driver's maximum passenger capacity for pooling."""
    if max_passengers < 1 or max_passengers > 4:
        raise HTTPException(status_code=400, detail="Max passengers must be between 1 and 4")
    
    result = supabase.table('drivers').update({'max_passengers': max_passengers}).eq('driver_id', driver_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    return {"message": "Capacity updated", "max_passengers": max_passengers}


# ================================================================
# GET DRIVER OFFERS (for passenger matching)
# ================================================================

@router.get("/{driver_id}/offers")
async def get_driver_offers(driver_id: str):
    """Get pending ride offers for a driver."""
    result = supabase.table('ride_offers').select('*, ride_requests(*)').eq('driver_id', driver_id).eq('status', 'pending').execute()
    
    offers = []
    for offer in result.data:
        ride = offer.get('ride_requests', {})
        offers.append({
            "offer_id": offer['offer_id'],
            "passenger_id": offer['passenger_id'],
            "passenger_name": ride.get('passenger_name', 'Unknown'),
            "pickup_lat": ride.get('origin_latitude'),
            "pickup_lng": ride.get('origin_longitude'),
            "dropoff_lat": ride.get('destination_latitude'),
            "dropoff_lng": ride.get('destination_longitude'),
            "ride_type": ride.get('ride_type', 'solo'),
            "expires_at": offer['expires_at']
        })
    
    return offers