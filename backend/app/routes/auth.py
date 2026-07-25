# routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from ..database import supabase
from ..security import hash_password, verify_password
from ..token_auth import create_token

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
    existing = supabase.table('passengers').select('passenger_id').eq('email', req.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    passenger_id = str(uuid.uuid4())

    data = {
        'passenger_id': passenger_id,
        'name': req.name,
        'phone_number': req.phone,
        'email': req.email,
        'password_hash': hash_password(req.password)
    }

    supabase.table('passengers').insert(data).execute()

    return {"message": "Passenger registered successfully", "passenger_id": passenger_id}


@router.post("/register/driver")
async def register_driver(req: RegisterDriverRequest):
    """Register a new driver."""
    existing_phone = supabase.table('drivers').select('driver_id').eq('phone_number', req.phone).execute()
    if existing_phone.data:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    existing_email = supabase.table('drivers').select('driver_id').eq('email', req.email).execute()
    if existing_email.data:
        raise HTTPException(status_code=400, detail="Email already registered as a driver")

    driver_id = str(uuid.uuid4())

    data = {
        'driver_id': driver_id,
        'name': req.name,
        'phone_number': req.phone,
        'email': req.email,
        'vehicle_type': req.vehicle_type,
        'vehicle_capacity': req.vehicle_capacity,
        'status': 'offline',
        'is_online': False,
        'password_hash': hash_password(req.password)
    }

    supabase.table('drivers').insert(data).execute()

    return {"message": "Driver registered successfully", "driver_id": driver_id}


@router.post("/login")
async def login(req: LoginRequest):
    """Login user. Checks passengers first, then drivers, and verifies the
    hashed password against whichever record matches the email."""

    passenger = supabase.table('passengers').select('*').eq('email', req.email).execute()
    if passenger.data:
        p = passenger.data[0]
        if not verify_password(req.password, p.get('password_hash')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {
            "token": create_token(p['passenger_id'], 'passenger'),
            "user": {
                "id": p['passenger_id'],
                "name": p['name'],
                "role": "passenger",
                "email": p['email']
            }
        }

    driver = supabase.table('drivers').select('*').eq('email', req.email).execute()
    if driver.data:
        d = driver.data[0]
        if not verify_password(req.password, d.get('password_hash')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {
            "token": create_token(d['driver_id'], 'driver'),
            "user": {
                "id": d['driver_id'],
                "name": d['name'],
                "role": "driver",
                "email": d.get('email', '')
            }
        }

    raise HTTPException(status_code=401, detail="Invalid credentials")
