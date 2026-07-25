# routes/tracking.py
from fastapi import APIRouter

from ..routing import get_route_geometry, get_route_distance, get_route_duration

router = APIRouter()


@router.get("/route")
async def get_route(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float):
    """
    Route geometry + distance/duration for drawing a live route line on the
    map (used once a ride is accepted, to show driver -> pickup -> destination).
    Falls back gracefully (empty geometry) if no OSRM server is configured -
    the frontend just skips drawing the line and shows markers only.
    """
    origin = (origin_lat, origin_lng)
    destination = (dest_lat, dest_lng)

    geometry = get_route_geometry(origin, destination) or []
    distance_km = get_route_distance(origin, destination)
    duration_min = get_route_duration(origin, destination)

    return {
        "geometry": [[lat, lng] for lat, lng in geometry],
        "distance_km": round(distance_km, 2),
        "duration_min": round(duration_min, 1)
    }
