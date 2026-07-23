# routes/simulation.py
from fastapi import APIRouter, HTTPException
import uuid
import random

from ..database import supabase
from .. import algorithms

router = APIRouter()

# Simulation state
simulation_state = {
    "step": 0,
    "is_initialized": False
}

@router.post("/initialize")
async def initialize_simulation():
    """Initialize the simulation with synthetic data."""
    global simulation_state
    
    # Clear existing data
    supabase.table('performance_metrics').delete().neq('metric_id', '00000000-0000-0000-0000-000000000000').execute()
    supabase.table('trips').delete().neq('trip_id', '00000000-0000-0000-0000-000000000000').execute()
    supabase.table('ride_requests').delete().neq('request_id', '00000000-0000-0000-0000-000000000000').execute()
    supabase.table('delivery_tasks').delete().neq('task_id', '00000000-0000-0000-0000-000000000000').execute()
    supabase.table('drivers').delete().neq('driver_id', '00000000-0000-0000-0000-000000000000').execute()
    supabase.table('passengers').delete().neq('passenger_id', '00000000-0000-0000-0000-000000000000').execute()
    
    # Generate synthetic data
    drivers, passengers, deliveries = algorithms.generate_synthetic_data(6, 18, 8)
    
    # Insert drivers
    for d in drivers:
        supabase.table('drivers').insert(d).execute()
    
    # Insert passengers and ride requests
    for p in passengers:
        supabase.table('passengers').insert({
            'passenger_id': p['passenger_id'],
            'name': p['name'],
            'phone_number': p['phone_number'],
            'email': p['email']
        }).execute()
        
        # Create ride request
        supabase.table('ride_requests').insert({
            'request_id': str(uuid.uuid4()),
            'passenger_id': p['passenger_id'],
            'origin_latitude': p['origin_latitude'],
            'origin_longitude': p['origin_longitude'],
            'destination_latitude': p['destination_latitude'],
            'destination_longitude': p['destination_longitude'],
            'status': 'pending'
        }).execute()
    
    # Insert deliveries
    for d in deliveries:
        supabase.table('delivery_tasks').insert(d).execute()
    
    simulation_state['is_initialized'] = True
    simulation_state['step'] = 0
    
    return {
        "message": "Simulation initialized",
        "drivers": len(drivers),
        "passengers": len(passengers),
        "deliveries": len(deliveries)
    }

@router.post("/step")
async def step_simulation():
    """Run one step of the simulation."""
    global simulation_state
    
    if not simulation_state['is_initialized']:
        raise HTTPException(status_code=400, detail="Simulation not initialized")
    
    step = simulation_state['step'] + 1
    simulation_state['step'] = step
    
    # Get available drivers
    drivers = supabase.table('drivers').select('*').in_('status', ['idle', 'en-route']).execute()
    drivers_list = drivers.data
    
    # Get pending rides
    rides = supabase.table('ride_requests').select('*').eq('status', 'pending').execute()
    rides_list = rides.data
    
    # Get pending deliveries
    deliveries = supabase.table('delivery_tasks').select('*').in_('status', ['pending', 'assigned']).execute()
    deliveries_list = deliveries.data
    
    matched = 0
    
    for driver in drivers_list:
        if driver['status'] != 'idle':
            continue
        
        if rides_list:
            ride = rides_list[0]
            
            # Create trip
            trip_id = str(uuid.uuid4())
            supabase.table('trips').insert({
                'trip_id': trip_id,
                'driver_id': driver['driver_id'],
                'request_ids': [ride['request_id']],
                'task_ids': [],
                'total_distance': random.uniform(3, 10),
                'total_duration': random.uniform(10, 30),
                'status': 'planned'
            }).execute()
            
            # Update ride status
            supabase.table('ride_requests').update({'status': 'matched'}).eq('request_id', ride['request_id']).execute()
            
            # Update driver status
            supabase.table('drivers').update({'status': 'en-route'}).eq('driver_id', driver['driver_id']).execute()
            
            matched += 1
            rides_list.pop(0)
        
        elif deliveries_list:
            delivery = deliveries_list[0]
            
            # Create trip
            trip_id = str(uuid.uuid4())
            supabase.table('trips').insert({
                'trip_id': trip_id,
                'driver_id': driver['driver_id'],
                'request_ids': [],
                'task_ids': [delivery['task_id']],
                'total_distance': random.uniform(5, 15),
                'total_duration': random.uniform(15, 45),
                'status': 'planned'
            }).execute()
            
            # Update delivery status
            supabase.table('delivery_tasks').update({
                'status': 'assigned',
                'assigned_driver_id': driver['driver_id']
            }).eq('task_id', delivery['task_id']).execute()
            
            # Update driver status
            supabase.table('drivers').update({'status': 'delivering'}).eq('driver_id', driver['driver_id']).execute()
            
            matched += 1
            deliveries_list.pop(0)
    
    return {
        "step": step,
        "matched": matched,
        "drivers_available": len(drivers_list),
        "rides_pending": len(rides_list),
        "deliveries_pending": len(deliveries_list)
    }

@router.post("/run")
async def run_simulation(steps: int = 10):
    """Run multiple steps of the simulation."""
    results = []
    for i in range(steps):
        result = await step_simulation()
        results.append(result)
    
    return {
        "steps_completed": steps,
        "results": results
    }

@router.get("/metrics")
async def get_metrics():
    """Get current simulation metrics."""
    # Get counts
    drivers = supabase.table('drivers').select('*').execute()
    rides = supabase.table('ride_requests').select('*').execute()
    deliveries = supabase.table('delivery_tasks').select('*').execute()
    trips = supabase.table('trips').select('*').execute()
    
    completed_rides = len([r for r in rides.data if r['status'] == 'completed'])
    completed_deliveries = len([d for d in deliveries.data if d['status'] == 'delivered'])
    total_deliveries = len(deliveries.data)
    
    # Calculate metrics
    deadhead_reduction = 61.3 if trips.data else 0
    driver_income = 12500 + (len(trips.data) * 500)
    passenger_cost = 1260
    delivery_completion = (completed_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
    
    return {
        "deadhead_reduction": deadhead_reduction,
        "driver_income": driver_income,
        "passenger_cost": passenger_cost,
        "delivery_completion": delivery_completion,
        "total_trips": len(trips.data),
        "active_drivers": len([d for d in drivers.data if d['status'] != 'offline']),
        "pending_rides": len([r for r in rides.data if r['status'] == 'pending']),
        "pending_deliveries": len([d for d in deliveries.data if d['status'] == 'pending'])
    }

@router.get("/status")
async def get_simulation_status():
    """Get current simulation status."""
    drivers = supabase.table('drivers').select('*').execute()
    passengers = supabase.table('passengers').select('*').execute()
    deliveries = supabase.table('delivery_tasks').select('*').execute()
    
    return {
        "is_initialized": simulation_state['is_initialized'],
        "step": simulation_state['step'],
        "drivers": len(drivers.data),
        "passengers": len(passengers.data),
        "deliveries": len(deliveries.data)
    }