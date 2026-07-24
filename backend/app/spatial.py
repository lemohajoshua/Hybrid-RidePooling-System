# app/spatial.py
"""
H3 Spatial Indexing for Demand Density Analysis
"""

import h3
from typing import List, Tuple, Dict, Any
from .algorithms import haversine

# Define zones for Owerri
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

# H3 resolution (8 = ~0.6km² cells)
H3_RESOLUTION = 8


def get_h3_cell(lat: float, lng: float, resolution: int = H3_RESOLUTION) -> str:
    """Get H3 cell index for a location."""
    return h3.geo_to_h3(lat, lng, resolution)


def get_h3_cells_for_zone(center: Tuple[float, float], radius_km: float, resolution: int = H3_RESOLUTION) -> List[str]:
    """Get all H3 cells within a radius of a center point."""
    # Simplified: use a grid of points around the center
    cells = []
    step = 0.01  # ~1km
    lat, lng = center
    
    for dlat in range(-int(radius_km), int(radius_km) + 1):
        for dlng in range(-int(radius_km), int(radius_km) + 1):
            test_lat = lat + dlat * step
            test_lng = lng + dlng * step
            dist = haversine(lat, lng, test_lat, test_lng)
            if dist <= radius_km:
                cell = get_h3_cell(test_lat, test_lng, resolution)
                if cell not in cells:
                    cells.append(cell)
    
    return cells


def is_urban(lat: float, lng: float) -> bool:
    """Check if a location is in an urban zone."""
    for zone in URBAN_ZONES:
        if haversine(lat, lng, zone[0], zone[1]) < 3.0:  # Within 3km
            return True
    return False


def is_rural(lat: float, lng: float) -> bool:
    """Check if a location is in a rural zone."""
    if is_urban(lat, lng):
        return False
    for zone in RURAL_ZONES:
        if haversine(lat, lng, zone[0], zone[1]) < 5.0:  # Within 5km
            return True
    return False


def calculate_demand_density(
    drivers: List[Dict], 
    rides: List[Dict], 
    radius_km: float = 5.0,
    resolution: int = H3_RESOLUTION
) -> Dict[str, Dict]:
    """
    Calculate demand density for each driver's location using H3 cells.
    
    Returns a dict mapping cell IDs to density data.
    """
    densities = {}
    
    # Group rides by H3 cell
    ride_cells = {}
    for ride in rides:
        if ride.get('status') != 'pending':
            continue
        lat = ride.get('origin_latitude', 0)
        lng = ride.get('origin_longitude', 0)
        cell = get_h3_cell(lat, lng, resolution)
        if cell not in ride_cells:
            ride_cells[cell] = []
        ride_cells[cell].append(ride)
    
    # For each driver, find their H3 cell and nearby rides
    for driver in drivers:
        lat = driver.get('current_latitude', 0)
        lng = driver.get('current_longitude', 0)
        driver_cell = get_h3_cell(lat, lng, resolution)
        
        # Count rides in same cell and adjacent cells
        nearby_rides = ride_cells.get(driver_cell, [])
        
        # Also check adjacent cells (simplified: check radius)
        for cell, rides_in_cell in ride_cells.items():
            if cell != driver_cell:
                # Get cell center (approximate)
                try:
                    cell_center = h3.h3_to_geo(cell)
                    dist = haversine(lat, lng, cell_center[0], cell_center[1])
                    if dist < radius_km:
                        nearby_rides.extend(rides_in_cell)
                except:
                    pass
        
        densities[driver['driver_id']] = {
            'cell': driver_cell,
            'ride_count': len(nearby_rides),
            'is_urban': is_urban(lat, lng),
            'is_rural': is_rural(lat, lng)
        }
    
    return densities


def get_zone_type(lat: float, lng: float) -> str:
    """Get the zone type for a location."""
    if is_urban(lat, lng):
        return 'urban'
    elif is_rural(lat, lng):
        return 'rural'
    else:
        return 'peri-urban'