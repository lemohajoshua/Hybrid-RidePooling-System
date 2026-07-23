# routes/deliveries.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

from ..database import supabase

router = APIRouter()

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

@router.post("/create")
async def create_delivery(req: DeliveryTaskCreate):
    """Create a new delivery task."""
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
    """Get all pending delivery tasks."""
    result = supabase.table('delivery_tasks').select('*').in_('status', ['pending', 'assigned']).execute()
    return result.data

@router.get("/{task_id}")
async def get_delivery(task_id: str):
    """Get delivery task by ID."""
    result = supabase.table('delivery_tasks').select('*').eq('task_id', task_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Delivery task not found")
    return result.data[0]

@router.put("/{task_id}/status")
async def update_delivery_status(task_id: str, status: str):
    """Update delivery task status."""
    valid_statuses = ["pending", "assigned", "picked_up", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = supabase.table('delivery_tasks').update({'status': status}).eq('task_id', task_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Delivery task not found")
    return {"message": "Status updated"}