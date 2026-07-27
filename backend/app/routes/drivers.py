# routes/drivers.py
from fastapi import APIRouter, HTTPException, Depends

from ..database import supabase
from ..models import LocationUpdate, StatusUpdate, OnlineToggle, CapacityUpdate
from ..algorithms import haversine, ModeSwitcher, DeadheadReductionScorer, URBAN_ZONES
from ..token_auth import get_current_user, require_self

router = APIRouter()

VALID_STATUSES = ["idle", "en-route", "occupied", "delivering", "offline"]

mode_switcher = ModeSwitcher(demand_threshold=2.0)
deadhead_scorer = DeadheadReductionScorer(high_demand_zones=URBAN_ZONES)

DEMAND_SEARCH_RADIUS_KM = 5.0
ZONE_NAMES = {
    (5.483, 7.035): "Owerri Municipal",
    (5.478, 7.025): "World Bank",
    (5.414, 7.016): "FUTO",
    (5.460, 7.040): "Concorde",
}


@router.get("/")
async def get_drivers():
    result = supabase.table('drivers').select('*').execute()
    return result.data


@router.get("/available")
async def get_available_drivers():
    """Drivers who are online AND free to take a new ride right now."""
    result = supabase.table('drivers').select('*') \
        .eq('is_online', True) \
        .eq('status', 'idle') \
        .execute()
    return result.data


@router.get("/{driver_id}")
async def get_driver(driver_id: str):
    result = supabase.table('drivers').select('*').eq('driver_id', driver_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return result.data[0]


@router.get("/{driver_id}/earnings")
async def get_driver_earnings(driver_id: str):
    result = supabase.table('drivers').select('total_earnings, avg_rating, rating_count').eq('driver_id', driver_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return result.data[0]


@router.get("/{driver_id}/suggested-mode")
async def get_suggested_mode(driver_id: str):
    """
    Algorithm 3 (Hybrid Mode Switching), running live for a real driver
    instead of only inside the simulation. Looks at unmatched ride demand
    and pending delivery tasks near the driver's current location and
    recommends ride-pooling vs delivery vs repositioning.
    """
    driver_result = supabase.table('drivers').select('*').eq('driver_id', driver_id).execute()
    if not driver_result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    driver = driver_result.data[0]
    if driver.get('current_latitude') is None or driver.get('current_longitude') is None:
        return {"mode": "unknown", "nearby_ride_demand": 0, "nearby_delivery_tasks": 0,
                "note": "Your location hasn't been detected yet - allow location access in your browser."}
    driver_location = (driver['current_latitude'], driver['current_longitude'])

    all_rides = supabase.table('ride_requests').select('*').in_('status', ['pending', 'pending_pool']).execute()
    nearby_passengers = [
        r for r in (all_rides.data or [])
        if haversine(driver_location[0], driver_location[1], r['origin_latitude'], r['origin_longitude']) <= DEMAND_SEARCH_RADIUS_KM
    ]

    all_deliveries = supabase.table('delivery_tasks').select('*').eq('status', 'pending').execute()
    nearby_deliveries = [
        d for d in (all_deliveries.data or [])
        if haversine(driver_location[0], driver_location[1], d['pickup_latitude'], d['pickup_longitude']) <= DEMAND_SEARCH_RADIUS_KM * 2
    ]

    decision = mode_switcher.decide_mode(driver_location, nearby_passengers, nearby_deliveries, deadhead_scorer)

    result = {
        "mode": decision['mode'],
        "nearby_ride_demand": len(nearby_passengers),
        "nearby_delivery_tasks": len(nearby_deliveries),
    }

    if decision['mode'] == 'idle':
        # Lightweight "predictive positioning": point the driver toward the
        # nearest known high-demand zone rather than leaving them guessing.
        nearest_zone, nearest_dist, nearest_name = None, float('inf'), None
        for zone in URBAN_ZONES:
            dist = haversine(driver_location[0], driver_location[1], zone[0], zone[1])
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_zone = zone
                nearest_name = ZONE_NAMES.get(zone, "a high-demand zone")
        result["reposition_suggestion"] = {
            "zone_name": nearest_name,
            "latitude": nearest_zone[0] if nearest_zone else None,
            "longitude": nearest_zone[1] if nearest_zone else None,
            "distance_km": round(nearest_dist, 1) if nearest_zone else None
        } if nearest_zone else None
    elif decision['mode'] == 'delivery':
        result["best_delivery_task"] = decision.get('assignment')
        result["score"] = decision.get('score')

    return result


@router.get("/{driver_id}/stats")
async def get_driver_stats(driver_id: str):
    driver_result = supabase.table('drivers').select('*').eq('driver_id', driver_id).execute()
    if not driver_result.data:
        raise HTTPException(status_code=404, detail="Driver not found")

    driver = driver_result.data[0]

    trips_result = supabase.table('trips').select('*').eq('driver_id', driver_id).execute()
    trips = trips_result.data

    completed_trips = [t for t in trips if t.get('status') == 'completed']
    completed_count = len(completed_trips)

    total_earnings = 0
    for trip in trips:
        metrics_result = supabase.table('performance_metrics').select('driver_earnings').eq('trip_id', trip['trip_id']).execute()
        if metrics_result.data:
            total_earnings += metrics_result.data[0].get('driver_earnings', 0)

    deliveries_result = supabase.table('delivery_tasks').select('*').eq('status', 'pending').execute()
    available_deliveries = len(deliveries_result.data)

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


@router.get("/{driver_id}/current-trip")
async def get_driver_current_trip(driver_id: str):
    trips_result = supabase.table('trips').select('*').eq('driver_id', driver_id).execute()
    trips = trips_result.data

    active_trip = None
    for trip in trips:
        if trip.get('status') in ['planned', 'in_progress']:
            active_trip = trip
            break

    if not active_trip:
        return {"has_active_trip": False, "trip": None}

    request_ids = active_trip.get('request_ids', [])
    ride_details = []
    for req_id in request_ids:
        ride_result = supabase.table('ride_requests').select('*').eq('request_id', req_id).execute()
        if ride_result.data:
            ride_details.append(ride_result.data[0])

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


@router.get("/{driver_id}/ride-requests")
async def get_driver_ride_requests(driver_id: str):
    """Ride requests sent straight to this driver, still awaiting a decision."""
    result = supabase.table('ride_requests').select('*') \
        .eq('driver_id', driver_id) \
        .eq('status', 'requested') \
        .order('request_time', desc=True) \
        .execute()
    return result.data


@router.put("/{driver_id}/location")
async def update_driver_location(driver_id: str, location: LocationUpdate, current_user: dict = Depends(get_current_user)):
    require_self(current_user, driver_id, expected_role='driver')
    result = supabase.table('drivers').update({
        'current_latitude': location.latitude,
        'current_longitude': location.longitude
    }).eq('driver_id', driver_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return {"message": "Location updated"}


@router.put("/{driver_id}/status")
async def update_driver_status(driver_id: str, body: StatusUpdate, current_user: dict = Depends(get_current_user)):
    require_self(current_user, driver_id, expected_role='driver')
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    result = supabase.table('drivers').update({'status': body.status}).eq('driver_id', driver_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return {"message": "Status updated", "status": body.status}


@router.put("/{driver_id}/online")
async def set_driver_online(driver_id: str, body: OnlineToggle, current_user: dict = Depends(get_current_user)):
    require_self(current_user, driver_id, expected_role='driver')

    driver_result = supabase.table('drivers').select('status').eq('driver_id', driver_id).execute()
    if not driver_result.data:
        raise HTTPException(status_code=404, detail="Driver not found")

    current_status = driver_result.data[0]['status']
    update = {'is_online': body.is_online}

    if body.is_online:
        if current_status == 'offline':
            update['status'] = 'idle'
    else:
        update['status'] = 'offline'

    supabase.table('drivers').update(update).eq('driver_id', driver_id).execute()
    return {"message": "Online status updated", "is_online": body.is_online, "status": update.get('status', current_status)}


@router.put("/{driver_id}/capacity")
async def update_driver_capacity(driver_id: str, body: CapacityUpdate, current_user: dict = Depends(get_current_user)):
    require_self(current_user, driver_id, expected_role='driver')
    if body.vehicle_capacity < 1 or body.vehicle_capacity > 4:
        raise HTTPException(status_code=400, detail="Capacity must be between 1 and 4")
    result = supabase.table('drivers').update({'vehicle_capacity': body.vehicle_capacity}).eq('driver_id', driver_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    return {"message": "Capacity updated", "vehicle_capacity": body.vehicle_capacity}
