# routes/simulation.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
import random
from typing import List, Optional

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
            'status': 'pending',
            'is_pooled': False
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
    
    # Get available drivers (ONLY idle drivers)
    drivers = supabase.table('drivers').select('*').eq('status', 'idle').execute()
    drivers_list = drivers.data
    
    # Get pending rides
    rides = supabase.table('ride_requests').select('*').eq('status', 'pending').execute()
    rides_list = rides.data
    
    # Get pending deliveries
    deliveries = supabase.table('delivery_tasks').select('*').eq('status', 'pending').execute()
    deliveries_list = deliveries.data
    
    matched = 0
    
    for driver in drivers_list:
        if driver['status'] != 'idle':
            continue
        
        if rides_list:
            ride = rides_list[0]
            trip_id = str(uuid.uuid4())
            
            # Check if pooling is possible (another ride to same destination)
            dest_lat = ride['destination_latitude']
            dest_lng = ride['destination_longitude']
            matching_ride = None
            
            for r in rides_list[1:]:
                if (abs(r['destination_latitude'] - dest_lat) < 0.01 and 
                    abs(r['destination_longitude'] - dest_lng) < 0.01):
                    matching_ride = r
                    break
            
            is_pooled = False
            if matching_ride:
                is_pooled = True
                request_ids = [ride['request_id'], matching_ride['request_id']]
                # Mark both rides as matched
                supabase.table('ride_requests').update({'status': 'matched'}).eq('request_id', matching_ride['request_id']).execute()
                supabase.table('ride_requests').update({'is_pooled': True}).eq('request_id', ride['request_id']).execute()
                supabase.table('ride_requests').update({'is_pooled': True}).eq('request_id', matching_ride['request_id']).execute()
                # Remove matching ride from list
                rides_list.remove(matching_ride)
            else:
                request_ids = [ride['request_id']]
            
            # Create trip
            supabase.table('trips').insert({
                'trip_id': trip_id,
                'driver_id': driver['driver_id'],
                'request_ids': request_ids,
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
            
            # Record performance metrics
            deadhead_dist = random.uniform(0.5, 2.0)
            passenger_dist = random.uniform(3, 10)
            
            # Calculate fare
            base_fare = 800
            distance_fare = passenger_dist * 80
            total_fare = base_fare + distance_fare
            
            if is_pooled:
                passenger_savings = total_fare * 0.30
                total_fare = total_fare * 0.70
            else:
                passenger_savings = 0
            
            driver_earnings = total_fare * 0.80
            
            supabase.table('performance_metrics').insert({
                'metric_id': str(uuid.uuid4()),
                'trip_id': trip_id,
                'deadhead_distance': deadhead_dist,
                'passenger_distance': passenger_dist,
                'delivery_distance': 0,
                'driver_earnings': driver_earnings,
                'passenger_savings': passenger_savings,
                'delivery_revenue': 0,
                'fuel_consumption': (deadhead_dist + passenger_dist) * 0.08,
                'emissions': (deadhead_dist + passenger_dist) * 0.18
            }).execute()
        
        elif deliveries_list:
            # Try delivery
            delivery = deliveries_list[0]
            trip_id = str(uuid.uuid4())
            
            # Create trip
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
            
            # Record performance metrics
            deadhead_dist = random.uniform(0.5, 2.0)
            delivery_dist = random.uniform(3, 8)
            
            supabase.table('performance_metrics').insert({
                'metric_id': str(uuid.uuid4()),
                'trip_id': trip_id,
                'deadhead_distance': deadhead_dist,
                'passenger_distance': 0,
                'delivery_distance': delivery_dist,
                'driver_earnings': random.uniform(500, 1500),
                'passenger_savings': 0,
                'delivery_revenue': 1200,
                'fuel_consumption': (deadhead_dist + delivery_dist) * 0.08,
                'emissions': (deadhead_dist + delivery_dist) * 0.18
            }).execute()
    
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
    """Get current simulation metrics - calculated dynamically."""
    # Get data from tables
    drivers = supabase.table('drivers').select('*').execute()
    rides = supabase.table('ride_requests').select('*').execute()
    deliveries = supabase.table('delivery_tasks').select('*').execute()
    trips = supabase.table('trips').select('*').execute()
    metrics = supabase.table('performance_metrics').select('*').execute()
    
    # Calculate from actual data
    total_trips = len(trips.data)
    completed_rides = len([r for r in rides.data if r['status'] == 'completed'])
    total_rides = len(rides.data) if rides.data else 1
    completed_deliveries = len([d for d in deliveries.data if d['status'] == 'delivered'])
    total_deliveries = len(deliveries.data) if deliveries.data else 1
    
    # Calculate deadhead reduction from performance metrics
    total_deadhead = sum([m.get('deadhead_distance', 0) for m in metrics.data]) if metrics.data else 0
    total_passenger_dist = sum([m.get('passenger_distance', 0) for m in metrics.data]) if metrics.data else 1
    
    # Calculate metrics dynamically
    deadhead_ratio = (total_deadhead / (total_deadhead + total_passenger_dist)) * 100 if (total_deadhead + total_passenger_dist) > 0 else 0
    deadhead_reduction = max(0, 100 - deadhead_ratio)
    
    # Driver income (average per trip)
    total_earnings = sum([m.get('driver_earnings', 0) for m in metrics.data]) if metrics.data else 0
    avg_income = total_earnings / len(drivers.data) if drivers.data and len(drivers.data) > 0 else 0
    
    # Passenger cost savings from pooled rides
    pooled_rides = len([r for r in rides.data if r.get('is_pooled', False)])
    avg_passenger_cost = 1800
    if pooled_rides > 0 and total_rides > 0:
        passenger_cost = avg_passenger_cost * (1 - (pooled_rides / total_rides) * 0.30)
    else:
        passenger_cost = avg_passenger_cost
    
    # Delivery completion rate
    delivery_completion = (completed_deliveries / total_deliveries) * 100 if total_deliveries > 0 else 0
    
    return {
        "deadhead_reduction": round(deadhead_reduction, 1),
        "driver_income": round(avg_income, 2),
        "passenger_cost": round(passenger_cost, 2),
        "delivery_completion": round(delivery_completion, 1),
        "total_trips": total_trips,
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


@router.post("/simulate")
async def run_agent_simulation(duration_hours: int = 24):
    """Run agent-based simulation using SimPy."""
    # Try to import simulation engine
    try:
        from ..simulation_engine import SimulationEngine
        from ..algorithms import generate_synthetic_data
    except ImportError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Simulation engine not available: {str(e)}. Please ensure simpy is installed and simulation_engine.py exists."
        )
    
    # Generate data
    drivers, passengers, deliveries = generate_synthetic_data(6, 18, 8)
    
    # Convert to format expected by SimulationEngine
    driver_data = [{
        'driver_id': d['driver_id'],
        'current_latitude': d['current_latitude'],
        'current_longitude': d['current_longitude'],
        'vehicle_capacity': d.get('vehicle_capacity', 4)
    } for d in drivers]
    
    passenger_data = passengers
    delivery_data = deliveries
    
    # Create simulation engine
    engine = SimulationEngine(driver_data, passenger_data, delivery_data)
    
    # Run simulation
    results = engine.run(duration_minutes=duration_hours * 60)
    
    return {
        "message": f"Simulation completed for {duration_hours} hours",
        "results": results
    }