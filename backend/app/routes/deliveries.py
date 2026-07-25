# routes/deliveries.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from ..database import supabase
from ..algorithms import DeadheadReductionScorer, URBAN_ZONES
from ..token_auth import get_current_user, require_self

router = APIRouter()

deadhead_scorer = DeadheadReductionScorer(high_demand_zones=URBAN_ZONES)

# Flat delivery fee model (kept simple and separate from the ride fare model)
DELIVERY_BASE_FEE = 500


class DeliveryTaskCreate(BaseModel):
    sender_name: str
    sender_phone: str
    pickup_latitude: float
    pickup_longitude: float
    dropoff_latitude: float
    dropoff_longitude: float
    pickup_time_window_start: Optional[str] = None
    pickup_time_window_end: Optional[str] = None
    dropoff_time_window_start: Optional[str] = None
    dropoff_time_window_end: Optional[str] = None
    package_description: Optional[str] = None


class DeliveryAssign(BaseModel):
    driver_id: str


class DeliveryStatusUpdate(BaseModel):
    status: str
    driver_id: str


@router.post("/create")
async def create_delivery(req: DeliveryTaskCreate):
    """Create a new delivery task (sender side)."""
    task_id = str(uuid.uuid4())

    data = {
        'task_id': task_id,
        'sender_name': req.sender_name,
        'sender_phone': req.sender_phone,
        'pickup_latitude': req.pickup_latitude,
        'pickup_longitude': req.pickup_longitude,
        'dropoff_latitude': req.dropoff_latitude,
        'dropoff_longitude': req.dropoff_longitude,
        'package_description': req.package_description,
        'status': 'pending'
    }

    result = supabase.table('delivery_tasks').insert(data).execute()
    return result.data[0] if result.data else {"task_id": task_id}


@router.get("/pending")
async def get_pending_deliveries():
    """All pending/assigned delivery tasks (sender-facing, unscored)."""
    result = supabase.table('delivery_tasks').select('*').in_('status', ['pending', 'assigned']).execute()
    return result.data


@router.get("/available")
async def get_available_deliveries(driver_lat: float, driver_lng: float):
    """
    Delivery tasks a driver could take right now, ranked by Algorithm 2
    (Deadhead Reduction Score) for the driver's current position - the
    task that best turns their empty-driving distance into paid work comes
    first, rather than just whatever was posted first.
    """
    result = supabase.table('delivery_tasks').select('*').eq('status', 'pending').execute()
    tasks = result.data or []

    scored = []
    for t in tasks:
        pickup = (t.get('pickup_latitude', 0), t.get('pickup_longitude', 0))
        dropoff = (t.get('dropoff_latitude', 0), t.get('dropoff_longitude', 0))
        score = deadhead_scorer.calculate_score((driver_lat, driver_lng), pickup, dropoff)
        scored.append({**t, 'deadhead_score': round(score, 3)})

    scored.sort(key=lambda t: t['deadhead_score'], reverse=True)
    return scored


@router.get("/driver/{driver_id}/tasks")
async def get_driver_tasks(driver_id: str):
    """This driver's active (not yet delivered) delivery tasks."""
    result = supabase.table('delivery_tasks').select('*') \
        .eq('driver_id', driver_id) \
        .in_('status', ['assigned', 'picked_up']) \
        .execute()
    return result.data


@router.get("/{task_id}")
async def get_delivery(task_id: str):
    result = supabase.table('delivery_tasks').select('*').eq('task_id', task_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Delivery task not found")
    return result.data[0]


@router.put("/{task_id}/assign")
async def assign_delivery(task_id: str, body: DeliveryAssign, current_user: dict = Depends(get_current_user)):
    """A driver accepts a delivery task."""
    require_self(current_user, body.driver_id, expected_role='driver')

    task_result = supabase.table('delivery_tasks').select('*').eq('task_id', task_id).execute()
    if not task_result.data:
        raise HTTPException(status_code=404, detail="Delivery task not found")
    task = task_result.data[0]
    if task.get('status') != 'pending':
        raise HTTPException(status_code=409, detail="This delivery task is no longer available")

    driver_result = supabase.table('drivers').select('*').eq('driver_id', body.driver_id).execute()
    if not driver_result.data:
        raise HTTPException(status_code=404, detail="Driver not found")
    driver = driver_result.data[0]
    if not driver.get('is_online') or driver.get('status') != 'idle':
        raise HTTPException(status_code=409, detail="You must be online and idle to accept a delivery")

    score = deadhead_scorer.calculate_score(
        (driver['current_latitude'], driver['current_longitude']),
        (task['pickup_latitude'], task['pickup_longitude']),
        (task['dropoff_latitude'], task['dropoff_longitude'])
    )

    now = datetime.now(timezone.utc).isoformat()
    supabase.table('delivery_tasks').update({
        'driver_id': body.driver_id,
        'status': 'assigned',
        'deadhead_score': round(score, 3),
        'assigned_at': now
    }).eq('task_id', task_id).execute()

    supabase.table('drivers').update({'status': 'delivering'}).eq('driver_id', body.driver_id).execute()

    return {"message": "Delivery task assigned", "task_id": task_id, "score": round(score, 3)}


@router.put("/{task_id}/status")
async def update_delivery_status(task_id: str, body: DeliveryStatusUpdate, current_user: dict = Depends(get_current_user)):
    """
    Driver progresses a delivery through pending -> assigned -> picked_up ->
    delivered. On 'delivered', the driver is paid a flat delivery fee and
    freed back to idle (if still online).
    """
    require_self(current_user, body.driver_id, expected_role='driver')

    valid_statuses = ["picked_up", "delivered", "cancelled"]
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    task_result = supabase.table('delivery_tasks').select('*').eq('task_id', task_id).execute()
    if not task_result.data:
        raise HTTPException(status_code=404, detail="Delivery task not found")
    task = task_result.data[0]
    if task.get('driver_id') != body.driver_id:
        raise HTTPException(status_code=403, detail="This delivery is not assigned to this driver")

    now = datetime.now(timezone.utc).isoformat()
    update = {'status': body.status}
    if body.status == 'picked_up':
        update['picked_up_at'] = now
    elif body.status == 'delivered':
        update['delivered_at'] = now

    supabase.table('delivery_tasks').update(update).eq('task_id', task_id).execute()

    if body.status in ('delivered', 'cancelled'):
        driver_result = supabase.table('drivers').select('total_earnings, is_online').eq('driver_id', body.driver_id).execute()
        if driver_result.data:
            d = driver_result.data[0]
            new_status = 'idle' if d.get('is_online') else 'offline'
            driver_update = {'status': new_status}
            if body.status == 'delivered':
                driver_update['total_earnings'] = (d.get('total_earnings') or 0) + DELIVERY_BASE_FEE
            supabase.table('drivers').update(driver_update).eq('driver_id', body.driver_id).execute()

    return {"message": f"Delivery {body.status}", "task_id": task_id, "earned": DELIVERY_BASE_FEE if body.status == 'delivered' else 0}
