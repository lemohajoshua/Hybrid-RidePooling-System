# app/simulation_engine.py
"""
Agent-Based Simulation Engine using SimPy
Implements discrete-event simulation for the hybrid ride-pooling system
"""

import simpy
import random
import uuid
from typing import Dict, List, Any, Tuple
from .algorithms import haversine


class DriverAgent:
    """Agent-based simulation driver."""
    
    def __init__(self, env: simpy.Environment, driver_id: str, location: Tuple[float, float], vehicle_capacity: int = 4):
        self.env = env
        self.id = driver_id
        self.location = location
        self.vehicle_capacity = vehicle_capacity
        self.status = 'idle'  # idle, en-route, occupied, delivering
        self.earnings = 0
        self.trips = []
        self.deadhead_km = 0
        self.active = True
        self.action = env.process(self.run())
    
    def run(self):
        """Main driver agent loop."""
        while self.active:
            if self.status == 'idle':
                # Wait for assignment
                yield self.env.timeout(random.uniform(1, 5))
            elif self.status == 'en-route':
                # Move to pickup
                travel_time = random.uniform(5, 15)
                self.deadhead_km += random.uniform(1, 3)
                yield self.env.timeout(travel_time)
                self.status = 'occupied'
            elif self.status == 'occupied':
                # Transport passenger
                travel_time = random.uniform(10, 30)
                yield self.env.timeout(travel_time)
                self.status = 'idle'
                self.earnings += random.uniform(800, 2000)
            elif self.status == 'delivering':
                # Deliver package
                travel_time = random.uniform(15, 45)
                self.deadhead_km += random.uniform(0.5, 2)
                yield self.env.timeout(travel_time)
                self.status = 'idle'
                self.earnings += random.uniform(500, 1500)
            else:
                yield self.env.timeout(1)
    
    def assign_trip(self, trip: Dict[str, Any]):
        """Assign a trip to the driver."""
        self.status = trip.get('status', 'en-route')
        self.trips.append(trip)
    
    def assign_delivery(self, delivery: Dict[str, Any]):
        """Assign a delivery to the driver."""
        self.status = 'delivering'
        self.trips.append({'type': 'delivery', 'data': delivery})


class PassengerAgent:
    """Agent-based simulation passenger."""
    
    def __init__(self, env: simpy.Environment, passenger_id: str, origin: Tuple[float, float], 
                 destination: Tuple[float, float], request_time: float):
        self.env = env
        self.id = passenger_id
        self.origin = origin
        self.destination = destination
        self.request_time = request_time
        self.status = 'pending'  # pending, matched, completed
        self.wait_time = 0
        self.action = env.process(self.run())
    
    def run(self):
        """Passenger agent loop."""
        yield self.env.timeout(0)
        self.status = 'pending'
        
        # Wait to be matched
        start_wait = self.env.now
        while self.status == 'pending':
            yield self.env.timeout(1)
            self.wait_time = self.env.now - start_wait
        
        if self.status == 'matched':
            # Wait for ride
            yield self.env.timeout(random.uniform(10, 30))
            self.status = 'completed'


class DeliveryTask:
    """Agent-based simulation delivery task."""
    
    def __init__(self, task_id: str, pickup: Tuple[float, float], dropoff: Tuple[float, float]):
        self.id = task_id
        self.pickup = pickup
        self.dropoff = dropoff
        self.status = 'pending'  # pending, assigned, picked_up, delivered
        self.assigned_driver = None
        self.completion_time = None


class SimulationEngine:
    """Agent-based simulation engine."""
    
    def __init__(self, drivers: List[Dict], passengers: List[Dict], deliveries: List[Dict]):
        self.env = simpy.Environment()
        self.drivers = []
        self.passengers = []
        self.deliveries = []
        self.trips_completed = 0
        self.deliveries_completed = 0
        self.total_deadhead = 0
        self.total_earnings = 0
        
        # Create driver agents
        for driver_data in drivers:
            location = (
                driver_data.get('current_latitude', 0),
                driver_data.get('current_longitude', 0)
            )
            driver = DriverAgent(
                self.env,
                driver_data['driver_id'],
                location,
                driver_data.get('vehicle_capacity', 4)
            )
            self.drivers.append(driver)
        
        # Create passenger agents
        for passenger_data in passengers:
            passenger = PassengerAgent(
                self.env,
                passenger_data['passenger_id'],
                (passenger_data['origin_latitude'], passenger_data['origin_longitude']),
                (passenger_data['destination_latitude'], passenger_data['destination_longitude']),
                self.env.now
            )
            self.passengers.append(passenger)
        
        # Create delivery tasks
        for delivery_data in deliveries:
            delivery = DeliveryTask(
                delivery_data['task_id'],
                (delivery_data['pickup_latitude'], delivery_data['pickup_longitude']),
                (delivery_data['dropoff_latitude'], delivery_data['dropoff_longitude'])
            )
            self.deliveries.append(delivery)
        
        # Start simulation processes
        self.env.process(self.matchmaking_process())
        self.env.process(self.delivery_assignment_process())
    
    def matchmaking_process(self):
        """Process for matching passengers with drivers."""
        while True:
            # Find pending passengers
            pending_passengers = [p for p in self.passengers if p.status == 'pending']
            
            if pending_passengers:
                # Find available drivers
                available_drivers = [d for d in self.drivers if d.status == 'idle']
                
                if available_drivers:
                    passenger = pending_passengers[0]
                    driver = random.choice(available_drivers)
                    
                    # Calculate distance
                    dist = haversine(
                        driver.location[0], driver.location[1],
                        passenger.origin[0], passenger.origin[1]
                    )
                    
                    # Assign trip
                    trip = {
                        'type': 'passenger',
                        'passenger_id': passenger.id,
                        'origin': passenger.origin,
                        'destination': passenger.destination,
                        'distance': dist,
                        'status': 'en-route'
                    }
                    driver.assign_trip(trip)
                    passenger.status = 'matched'
                    self.trips_completed += 1
                    self.total_deadhead += dist
                    self.total_earnings += random.uniform(800, 2000)
            
            yield self.env.timeout(5)
    
    def delivery_assignment_process(self):
        """Process for assigning deliveries to drivers."""
        while True:
            # Find pending deliveries
            pending_deliveries = [d for d in self.deliveries if d.status == 'pending']
            
            if pending_deliveries:
                # Find available drivers (prefer those in rural areas)
                available_drivers = [d for d in self.drivers if d.status == 'idle']
                
                if available_drivers:
                    delivery = pending_deliveries[0]
                    driver = random.choice(available_drivers)
                    
                    # Assign delivery
                    driver.assign_delivery({
                        'type': 'delivery',
                        'delivery_id': delivery.id,
                        'pickup': delivery.pickup,
                        'dropoff': delivery.dropoff,
                        'status': 'delivering'
                    })
                    delivery.status = 'assigned'
                    delivery.assigned_driver = driver.id
                    self.deliveries_completed += 1
                    self.total_earnings += random.uniform(500, 1500)
            
            yield self.env.timeout(10)
    
    def run(self, duration_minutes: int = 1440) -> Dict[str, Any]:
        """
        Run the simulation for a specified duration.
        Default: 1440 minutes = 24 hours.
        """
        self.env.run(until=duration_minutes)
        return self.get_metrics()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get simulation results and metrics."""
        total_drivers = len(self.drivers)
        total_passengers = len(self.passengers)
        total_deliveries = len(self.deliveries)
        
        completed_passengers = len([p for p in self.passengers if p.status == 'completed'])
        completed_deliveries = self.deliveries_completed
        
        avg_wait_time = sum([p.wait_time for p in self.passengers]) / total_passengers if total_passengers > 0 else 0
        
        return {
            "total_time_minutes": self.env.now,
            "trips_completed": self.trips_completed,
            "deliveries_completed": completed_deliveries,
            "passengers_completed": completed_passengers,
            "total_earnings": round(self.total_earnings, 2),
            "total_deadhead_km": round(self.total_deadhead, 2),
            "avg_wait_time_minutes": round(avg_wait_time, 2),
            "avg_driver_income": round(self.total_earnings / total_drivers, 2) if total_drivers > 0 else 0,
            "drivers_used": len([d for d in self.drivers if d.trips]),
            "utilization_rate": round((len([d for d in self.drivers if d.trips]) / total_drivers) * 100, 1) if total_drivers > 0 else 0
        }


def run_simulation_with_data(drivers: List[Dict], passengers: List[Dict], deliveries: List[Dict], duration_hours: int = 24):
    """
    Convenience function to run the simulation with given data.
    """
    engine = SimulationEngine(drivers, passengers, deliveries)
    return engine.run(duration_minutes=duration_hours * 60)