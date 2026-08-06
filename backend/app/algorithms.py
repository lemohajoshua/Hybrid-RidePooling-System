# app/algorithms.py
"""
Core algorithms from Chapter 3 of the project
"""

import math
import random
import uuid
from typing import List, Tuple, Optional, Dict, Any

# ================================================================
# UTILITY FUNCTIONS
# ================================================================

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ================================================================
# ALGORITHM 1: INSERTION HEURISTIC FOR RIDE-POOLING
# ================================================================

class InsertionHeuristic:
    """
    Algorithm 1: Insertion Heuristic for Ride-Pooling Matching
    """
    
    def __init__(self, max_detour_factor: float = 1.20):
        self.max_detour_factor = max_detour_factor
    
    def find_match(
        self,
        driver_route: List[Tuple[float, float]],
        driver_position: Tuple[float, float],
        passenger_pickup: Tuple[float, float],
        passenger_dropoff: Tuple[float, float]
    ) -> Optional[Tuple[List[Tuple[float, float]], float]]:
        """
        Find the optimal insertion position for a new passenger.
        
        Returns:
            Tuple of (updated_route, additional_distance) or None if infeasible
        """
        existing_stops = driver_route if driver_route else [driver_position]
        current_pos = driver_position
        P_p = passenger_pickup
        D_p = passenger_dropoff
        
        best_delta = float('inf')
        best_route = None
        
        for i in range(len(existing_stops) + 1):
            for j in range(i + 1, len(existing_stops) + 2):
                route = []
                for k in range(len(existing_stops)):
                    if k == i:
                        route.append(P_p)
                    route.append(existing_stops[k])
                    if k == j - 1:
                        route.append(D_p)
                if i == len(existing_stops):
                    route.append(P_p)
                if j == len(existing_stops) + 1:
                    route.append(D_p)
                
                # Calculate total distance
                total_dist = 0
                prev = current_pos
                for stop in route:
                    total_dist += haversine(prev[0], prev[1], stop[0], stop[1])
                    prev = stop
                
                # Calculate original distance
                orig_dist = 0
                prev = current_pos
                for stop in existing_stops:
                    orig_dist += haversine(prev[0], prev[1], stop[0], stop[1])
                    prev = stop
                
                delta = total_dist - orig_dist
                detour_factor = total_dist / (orig_dist + 0.001)
                
                if detour_factor <= self.max_detour_factor and delta < best_delta:
                    best_delta = delta
                    best_route = route
        
        if best_route and best_delta < 5:
            return best_route, best_delta
        return None


# ================================================================
# ALGORITHM 2: DEADHEAD REDUCTION SCORING
# ================================================================

class DeadheadReductionScorer:
    """
    Algorithm 2: Deadhead Reduction Scoring for Delivery Allocation
    """
    
    def __init__(self, high_demand_zones: List[Tuple[float, float]]):
        self.high_demand_zones = high_demand_zones
    
    def calculate_score(
        self,
        driver_location: Tuple[float, float],
        pickup: Tuple[float, float],
        dropoff: Tuple[float, float]
    ) -> float:
        """
        Calculate the deadhead reduction score for a delivery task.
        Higher score = better delivery task.
        """
        L_d = driver_location
        P_t = pickup
        D_t = dropoff
        
        # Find nearest high-demand zone
        nearest_urban = None
        min_dist = float('inf')
        for zone in self.high_demand_zones:
            d = haversine(D_t[0], D_t[1], zone[0], zone[1])
            if d < min_dist:
                min_dist = d
                nearest_urban = zone
        
        if not nearest_urban:
            return 0
        
        H = nearest_urban
        
        d1 = haversine(L_d[0], L_d[1], P_t[0], P_t[1])
        d2 = haversine(P_t[0], P_t[1], D_t[0], D_t[1])
        d3 = haversine(D_t[0], D_t[1], H[0], H[1])
        baseline = haversine(L_d[0], L_d[1], H[0], H[1])
        
        deadhead_with_delivery = d1 + d3
        reduction = baseline - deadhead_with_delivery
        score = reduction / (d1 + d2 + 0.001)
        
        return max(0, score)


# ================================================================
# ALGORITHM 3: HYBRID MODE SWITCHING
# ================================================================

class ModeSwitcher:
    """
    Algorithm 3: Hybrid Mode Switching Decision
    """
    
    def __init__(self, demand_threshold: float = 2.0):
        self.demand_threshold = demand_threshold
    
    def decide_mode(
        self,
        driver_location: Tuple[float, float],
        nearby_passengers: List[Dict[str, Any]],
        available_deliveries: List[Dict[str, Any]],
        scorer: DeadheadReductionScorer
    ) -> Dict[str, Any]:
        """
        Decide whether a driver should be in ride-pooling or delivery mode.
        """
        demand_density = len(nearby_passengers)
        
        if demand_density >= self.demand_threshold:
            # High demand -> ride-pooling
            if demand_density >= 2:
                return {
                    'mode': 'ride-pooling',
                    'assignment': nearby_passengers[:2]
                }
            elif demand_density == 1:
                return {
                    'mode': 'single',
                    'assignment': nearby_passengers[0]
                }
            else:
                return {'mode': 'idle', 'assignment': None}
        else:
            # Low demand -> try delivery
            best_score = 0
            best_delivery = None
            
            for delivery in available_deliveries:
                pickup = (delivery.get('pickup_latitude', 0), delivery.get('pickup_longitude', 0))
                dropoff = (delivery.get('dropoff_latitude', 0), delivery.get('dropoff_longitude', 0))
                score = scorer.calculate_score(driver_location, pickup, dropoff)
                if score > best_score:
                    best_score = score
                    best_delivery = delivery
            
            if best_delivery and best_score > 0.5:
                return {
                    'mode': 'delivery',
                    'assignment': best_delivery,
                    'score': best_score
                }
            
            return {'mode': 'idle', 'assignment': None}


# ================================================================
# SYNTHETIC DATA GENERATOR
# ================================================================

URBAN_ZONES = [
    (5.483, 7.035),  # Owerri Municipal
    (5.478, 7.025),  # World Bank
    (5.414, 7.016),  # FUTO
    (5.460, 7.040),  # Concorde
]

RURAL_ZONES = [
    (5.362, 6.956),  # Obinze
    (5.400, 6.989),  # Ihiagwa
    (5.442, 6.970),  # Nekede
    (5.505, 6.965),  # Umuguma
]

def random_point_in_zone(zones):
    zone = random.choice(zones)
    lat = zone[0] + random.uniform(-0.02, 0.02)
    lng = zone[1] + random.uniform(-0.02, 0.02)
    return (lat, lng)

def generate_synthetic_data(num_drivers=6, num_passengers=18, num_deliveries=8):
    """Generate synthetic data for simulation."""
    
    # Generate drivers
    drivers = []
    for i in range(num_drivers):
        pos = random_point_in_zone(URBAN_ZONES)
        drivers.append({
            'driver_id': str(uuid.uuid4()),
            'name': f'Driver {i+1}',
            'phone_number': f'+234800000{i:04d}',
            'vehicle_type': random.choice(['Sedan', 'SUV', 'Mini']),
            'vehicle_capacity': 4,
            'current_latitude': pos[0],
            'current_longitude': pos[1],
            'status': 'idle',
            'is_simulated': True
        })
    
    # Generate passengers and ride requests
    passengers = []
    for i in range(num_passengers):
        origin = random_point_in_zone(URBAN_ZONES if i < num_passengers // 2 else RURAL_ZONES)
        dest = random_point_in_zone(URBAN_ZONES if i >= num_passengers // 2 else RURAL_ZONES)
        passengers.append({
            'passenger_id': str(uuid.uuid4()),
            'name': f'Passenger {i+1}',
            'phone_number': f'+234800000{i+100:04d}',
            'email': f'passenger{i+1}@email.com',
            'origin_latitude': origin[0],
            'origin_longitude': origin[1],
            'destination_latitude': dest[0],
            'destination_longitude': dest[1],
            'status': 'pending',
            'is_simulated': True
        })
    
    # Generate deliveries
    deliveries = []
    for i in range(num_deliveries):
        pickup = random_point_in_zone(RURAL_ZONES)
        dropoff = random_point_in_zone(URBAN_ZONES)
        deliveries.append({
            'task_id': str(uuid.uuid4()),
            'sender_name': f'Sender {i+1}',
            'sender_phone': f'+234800000{i+200:04d}',
            'pickup_latitude': pickup[0],
            'pickup_longitude': pickup[1],
            'dropoff_latitude': dropoff[0],
            'dropoff_longitude': dropoff[1],
            'package_description': random.choice(['Small Parcel', 'Medium Box', 'Large Package', 'Electronics']),
            'status': 'pending',
            'is_simulated': True
        })
    
    return drivers, passengers, deliveries