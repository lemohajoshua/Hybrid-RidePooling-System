# app/models.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ================================================================
# AUTH MODELS
# ================================================================

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

class LoginResponse(BaseModel):
    user_id: str
    name: str
    role: str
    message: str

# ================================================================
# RIDE MODELS
# ================================================================

class RideRequestCreate(BaseModel):
    passenger_id: str
    origin_latitude: float
    origin_longitude: float
    destination_latitude: float
    destination_longitude: float
    pickup_time_window_start: Optional[str] = None
    pickup_time_window_end: Optional[str] = None

class RideRequestResponse(BaseModel):
    request_id: str
    passenger_id: str
    origin_latitude: float
    origin_longitude: float
    destination_latitude: float
    destination_longitude: float
    status: str
    request_time: Optional[str] = None

# ================================================================
# DRIVER MODELS
# ================================================================

class DriverResponse(BaseModel):
    driver_id: str
    name: str
    phone_number: str
    vehicle_type: Optional[str] = None
    vehicle_capacity: int
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    status: str
    registration_date: Optional[str] = None

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

# ================================================================
# DELIVERY MODELS
# ================================================================

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

class DeliveryTaskResponse(BaseModel):
    task_id: str
    sender_name: str
    sender_phone: str
    pickup_latitude: float
    pickup_longitude: float
    dropoff_latitude: float
    dropoff_longitude: float
    status: str
    package_description: Optional[str] = None
    assigned_driver_id: Optional[str] = None

# ================================================================
# TRIP MODELS
# ================================================================

class TripCreate(BaseModel):
    driver_id: str
    request_ids: Optional[List[str]] = []
    task_ids: Optional[List[str]] = []
    total_distance: float
    total_duration: Optional[float] = None

class TripResponse(BaseModel):
    trip_id: str
    driver_id: str
    request_ids: List[str]
    task_ids: List[str]
    total_distance: float
    total_duration: Optional[float] = None
    status: str
    start_time: Optional[str] = None

# ================================================================
# SIMULATION MODELS
# ================================================================

class SimulationStatus(BaseModel):
    is_initialized: bool
    step: int
    drivers: int
    passengers: int
    deliveries: int

class MetricsResponse(BaseModel):
    deadhead_reduction: float
    driver_income: float
    passenger_cost: float
    delivery_completion: float
    total_trips: int
    active_drivers: int
    pending_rides: int
    pending_deliveries: int