# routes/analytics.py
from fastapi import APIRouter
from datetime import datetime
from collections import Counter

from ..database import supabase
from ..spatial import get_zone_type

router = APIRouter()


def _parse_hour(timestamp_str: str):
    if not timestamp_str:
        return None
    try:
        ts = timestamp_str.replace('Z', '+00:00')
        return datetime.fromisoformat(ts).hour
    except (ValueError, TypeError):
        return None


@router.get("/demand")
async def get_demand_analytics():
    """
    Objective 1: how ride demand varies across urban/rural areas over time.
    Aggregates real ride_requests + delivery_tasks by hour-of-day and by
    zone, so this is driven by actual data rather than only existing as
    zone constants inside algorithms.py.
    """
    rides_result = supabase.table('ride_requests').select(
        'request_time, origin_latitude, origin_longitude, is_pooled, status'
    ).execute()
    rides = rides_result.data or []

    deliveries_result = supabase.table('delivery_tasks').select(
        'pickup_latitude, pickup_longitude, status'
    ).execute()
    deliveries = deliveries_result.data or []

    hourly_counter = Counter()
    zone_counter = Counter()
    pooled_count = 0

    for r in rides:
        hour = _parse_hour(r.get('request_time'))
        if hour is not None:
            hourly_counter[hour] += 1

        zone = get_zone_type(r.get('origin_latitude', 0), r.get('origin_longitude', 0))
        zone_counter[zone] += 1

        if r.get('is_pooled'):
            pooled_count += 1

    delivery_zone_counter = Counter()
    for d in deliveries:
        zone = get_zone_type(d.get('pickup_latitude', 0), d.get('pickup_longitude', 0))
        delivery_zone_counter[zone] += 1

    hourly_breakdown = [{"hour": h, "count": hourly_counter.get(h, 0)} for h in range(24)]

    return {
        "total_rides": len(rides),
        "total_deliveries": len(deliveries),
        "pooled_rides": pooled_count,
        "pooled_ratio": round(pooled_count / len(rides), 3) if rides else 0,
        "hourly_ride_demand": hourly_breakdown,
        "ride_zone_breakdown": {
            "urban": zone_counter.get('urban', 0),
            "peri-urban": zone_counter.get('peri-urban', 0),
            "rural": zone_counter.get('rural', 0)
        },
        "delivery_zone_breakdown": {
            "urban": delivery_zone_counter.get('urban', 0),
            "peri-urban": delivery_zone_counter.get('peri-urban', 0),
            "rural": delivery_zone_counter.get('rural', 0)
        }
    }
