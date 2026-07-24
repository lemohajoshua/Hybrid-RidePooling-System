# routes/passengers.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime, timedelta
import math

from ..database import supabase

router = APIRouter()


class RideRequestData(BaseModel):
    passenger_id: str
    origin_latitude: float
    origin_longitude: float
    destination_latitude: float
    destination_longitude: float
    ride_type: str = "solo"
    pickup_time_window_start: Optional[str] = None
    pickup_time_window_end: Optional[str] = None


class DriverSelectData(BaseModel):
    passenger_id: str
    driver_id: str
    ride_request_id: str


class DriverResponseData(BaseModel):
    offer_id: str
    driver_id: str
    action: str  # "accept" or "reject"


# ================================================================
# GET ALL PASSENGERS
# ================================================================

@router.get("/")
async def get_passengers():
    """Get all passengers."""
    result = supabase.table('passengers').select('*').execute()
    return result.data


# ================================================================
# GET SINGLE PASSENGER
# ================================================================

@router.get("/{passenger_id}")
async def get_passenger(passenger_id: str):
    """Get passenger by ID."""
    result = supabase.table('passengers').select('*').eq('passenger_id', passenger_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return result.data[0]


# ================================================================
# GET PASSENGER RIDES
# ================================================================

@router.get("/{passenger_id}/rides")
async def get_passenger_rides(passenger_id: str):
    """Get all ride requests for a passenger."""
    result = supabase.table('ride_requests').select('*').eq('passenger_id', passenger_id).execute()
    return result.data


# ================================================================
# AVAILABLE DRIVERS (For Passenger to Select)
# ================================================================

@router.get("/available-drivers")
async def get_available_drivers():
    """
    Get all available drivers with current passenger count.
    Returns drivers with status 'idle' or 'en-route' and not at capacity.
    """
    try:
        result = supabase.table('drivers').select('*').in_('status', ['idle', 'en-route']).execute()
        drivers = result.data
        
        if not drivers:
            return []
        
        for driver in drivers:
            max_pass = driver.get('max_passengers', 2)
            driver['max_passengers'] = max_pass
            
            trips_result = supabase.table('trips').select('*').eq('driver_id', driver['driver_id']).in_('status', ['planned', 'in_progress']).execute()
            active_trips = trips_result.data
            
            passenger_count = 0
            for trip in active_trips:
                request_ids = trip.get('request_ids', [])
                passenger_count += len(request_ids)
            
            driver['current_passengers'] = passenger_count
            driver['available_seats'] = max_pass - passenger_count
            
        return drivers
        
    except Exception as e:
        print(f"Error in available-drivers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# CREATE RIDE REQUEST (Passenger)
# ================================================================

@router.post("/request-ride")
async def request_ride(ride_data: RideRequestData):
    """Create a new ride request."""
    request_id = str(uuid.uuid4())
    
    passenger_result = supabase.table('passengers').select('name').eq('passenger_id', ride_data.passenger_id).execute()
    passenger_name = passenger_result.data[0]['name'] if passenger_result.data else "Unknown"
    
    data = {
        'request_id': request_id,
        'passenger_id': ride_data.passenger_id,
        'passenger_name': passenger_name,
        'origin_latitude': ride_data.origin_latitude,
        'origin_longitude': ride_data.origin_longitude,
        'destination_latitude': ride_data.destination_latitude,
        'destination_longitude': ride_data.destination_longitude,
        'ride_type': ride_data.ride_type,
        'is_pooled': ride_data.ride_type == 'pooled',
        'status': 'pending',
        'pickup_time_window_start': ride_data.pickup_time_window_start,
        'pickup_time_window_end': ride_data.pickup_time_window_end
    }
    
    result = supabase.table('ride_requests').insert(data).execute()
    
    return result.data[0] if result.data else {"request_id": request_id}


# ================================================================
# SELECT DRIVER (Passenger chooses a driver)
# ================================================================

@router.post("/select-driver")
async def select_driver(selection: DriverSelectData):
    """Passenger selects a driver for their ride."""
    
    ride_result = supabase.table('ride_requests').select('*').eq('request_id', selection.ride_request_id).execute()
    if not ride_result.data:
        raise HTTPException(status_code=404, detail="Ride request not found")
    ride = ride_result.data[0]
    
    if ride['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Ride request is no longer pending")
    
    driver_result = supabase.table('drivers').select('*').eq('driver_id', selection.driver_id).execute()
    if not driver_result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    driver = driver_result.data[0]
    
    if ride['is_pooled']:
        trips_result = supabase.table('trips').select('*').eq('driver_id', selection.driver_id).in_('status', ['planned', 'in_progress']).execute()
        current_passengers = 0
        for trip in trips_result.data:
            request_ids = trip.get('request_ids', [])
            current_passengers += len(request_ids)
        
        max_pass = driver.get('max_passengers', 2)
        if current_passengers >= max_pass:
            raise HTTPException(status_code=400, detail="Driver is at full capacity")
    
    offer_id = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(minutes=2)
    
    offer_data = {
        'offer_id': offer_id,
        'passenger_id': selection.passenger_id,
        'driver_id': selection.driver_id,
        'ride_request_id': selection.ride_request_id,
        'status': 'pending',
        'expires_at': expires_at.isoformat()
    }
    
    supabase.table('ride_offers').insert(offer_data).execute()
    
    supabase.table('ride_requests').update({
        'status': 'pending_driver_response',
        'driver_id': selection.driver_id,
        'offer_id': offer_id
    }).eq('request_id', selection.ride_request_id).execute()
    
    return {
        "offer_id": offer_id,
        "driver_id": selection.driver_id,
        "status": "pending",
        "expires_at": expires_at.isoformat(),
        "message": "Offer sent to driver. Waiting for response..."
    }


# ================================================================
# DRIVER RESPONSE (Accept/Reject)
# ================================================================

@router.post("/driver-response")
async def driver_response(response: DriverResponseData):
    """Driver accepts or rejects a ride offer."""
    
    offer_result = supabase.table('ride_offers').select('*').eq('offer_id', response.offer_id).execute()
    if not offer_result.data:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer = offer_result.data[0]
    
    if offer['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Offer already responded to")
    
    expires_at = datetime.fromisoformat(offer['expires_at'].replace('Z', '+00:00'))
    if datetime.now() > expires_at:
        supabase.table('ride_offers').update({'status': 'expired'}).eq('offer_id', response.offer_id).execute()
        supabase.table('ride_requests').update({'status': 'expired'}).eq('request_id', offer['ride_request_id']).execute()
        raise HTTPException(status_code=400, detail="Offer has expired")
    
    supabase.table('ride_offers').update({
        'status': response.action,
        'updated_at': datetime.now().isoformat()
    }).eq('offer_id', response.offer_id).execute()
    
    if response.action == 'accept':
        trip_id = str(uuid.uuid4())
        ride_request_result = supabase.table('ride_requests').select('*').eq('request_id', offer['ride_request_id']).execute()
        ride = ride_request_result.data[0]
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = haversine(ride['origin_latitude'], ride['origin_longitude'], 
                            ride['destination_latitude'], ride['destination_longitude'])
        
        supabase.table('trips').insert({
            'trip_id': trip_id,
            'driver_id': response.driver_id,
            'request_ids': [offer['ride_request_id']],
            'total_distance': distance,
            'status': 'planned',
            'start_time': datetime.now().isoformat()
        }).execute()
        
        supabase.table('ride_requests').update({
            'status': 'accepted',
            'driver_id': response.driver_id
        }).eq('request_id', offer['ride_request_id']).execute()
        
        return {
            "status": "accepted",
            "trip_id": trip_id,
            "message": "Ride accepted! Driver is on the way."
        }
    
    else:
        supabase.table('ride_requests').update({
            'status': 'rejected'
        }).eq('request_id', offer['ride_request_id']).execute()
        return {
            "status": "rejected",
            "message": "Driver rejected your request."
        }


# ================================================================
# OFFER STATUS (Passenger polls this)
# ================================================================

@router.get("/offer-status/{offer_id}")
async def get_offer_status(offer_id: str):
    """Passenger checks the status of their offer."""
    result = supabase.table('ride_offers').select('*, ride_requests(*)').eq('offer_id', offer_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer = result.data[0]
    ride = offer.get('ride_requests', {})
    return {
        "offer_id": offer['offer_id'],
        "status": offer['status'],
        "driver_id": offer['driver_id'],
        "ride_status": ride.get('status', 'unknown'),
        "expires_at": offer['expires_at'],
        "updated_at": offer['updated_at']
    }


# ================================================================
# DRIVER OFFERS (Driver polls this for pending requests)
# ================================================================

@router.get("/driver-offers/{driver_id}")
async def get_driver_offers(driver_id: str):
    """Driver checks for pending offers."""
    result = supabase.table('ride_offers').select('*, ride_requests(*)').eq('driver_id', driver_id).eq('status', 'pending').execute()
    offers = []
    for offer in result.data:
        ride = offer.get('ride_requests', {})
        offers.append({
            "offer_id": offer['offer_id'],
            "passenger_id": offer['passenger_id'],
            "ride_request_id": offer['ride_request_id'],
            "pickup_lat": ride.get('origin_latitude'),
            "pickup_lng": ride.get('origin_longitude'),
            "dropoff_lat": ride.get('destination_latitude'),
            "dropoff_lng": ride.get('destination_longitude'),
            "passenger_name": ride.get('passenger_name', 'Unknown'),
            "ride_type": ride.get('ride_type', 'solo'),
            "expires_at": offer['expires_at']
        })
    return offers