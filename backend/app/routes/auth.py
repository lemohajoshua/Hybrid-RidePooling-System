# routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from ..database import supabase

router = APIRouter()


class RegisterPassengerRequest(BaseModel):
    name: str
    phone: str
    email: str
    password: str


class RegisterDriverRequest(BaseModel):
    name: str
    phone: str
    email: str
    vehicle_type: str = "Sedan"
    vehicle_capacity: int = 4
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register/passenger")
async def register_passenger(req: RegisterPassengerRequest):
    """Register a new passenger."""
    # Check if email exists
    existing = supabase.table('passengers').select('*').eq('email', req.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    passenger_id = str(uuid.uuid4())
    
    data = {
        'passenger_id': passenger_id,
        'name': req.name,
        'phone_number': req.phone,
        'email': req.email
    }
    
    result = supabase.table('passengers').insert(data).execute()
    
    return {"message": "Passenger registered successfully", "passenger_id": passenger_id}


@router.post("/register/driver")
async def register_driver(req: RegisterDriverRequest):
    """Register a new driver."""
    # Check if phone already exists
    existing_phone = supabase.table('drivers').select('*').eq('phone_number', req.phone).execute()
    if existing_phone.data:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Check if email already exists for drivers
    existing_email = supabase.table('drivers').select('*').eq('email', req.email).execute()
    if existing_email.data:
        raise HTTPException(status_code=400, detail="Email already registered as a driver")
    
    driver_id = str(uuid.uuid4())
    
    data = {
        'driver_id': driver_id,
        'name': req.name,
        'phone_number': req.phone,
        'email': req.email,  # ← Store email for drivers!
        'vehicle_type': req.vehicle_type,
        'vehicle_capacity': req.vehicle_capacity,
        'status': 'idle'
    }
    
    result = supabase.table('drivers').insert(data).execute()
    
    return {"message": "Driver registered successfully", "driver_id": driver_id}


@router.post("/login")
async def login(req: LoginRequest):
    """Login user."""
    # Check passenger by email
    passenger = supabase.table('passengers').select('*').eq('email', req.email).execute()
    if passenger.data:
        p = passenger.data[0]
        return {
            "user": {
                "id": p['passenger_id'],
                "name": p['name'],
                "role": "passenger",
                "email": p['email']
            }
        }
    
    # Check driver by email (NOW FIXED!)
    driver = supabase.table('drivers').select('*').eq('email', req.email).execute()
    if driver.data:
        d = driver.data[0]
        return {
            "user": {
                "id": d['driver_id'],
                "name": d['name'],
                "role": "driver",
                "email": d.get('email', '')
            }
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")