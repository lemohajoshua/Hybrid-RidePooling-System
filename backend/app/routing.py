# app/routing.py
"""
OSRM Routing Engine Integration for Real-World Road Network Routing
"""

import requests
import os
from typing import Tuple, List, Optional, Dict, Any
from .algorithms import haversine

# OSRM server URL (default: localhost:5000)
OSRM_URL = os.getenv("OSRM_URL", "http://localhost:5000")


def get_route_distance(
    origin: Tuple[float, float], 
    destination: Tuple[float, float]
) -> float:
    """
    Get real road distance using OSRM.
    Returns distance in kilometers.
    """
    try:
        url = f"{OSRM_URL}/route/v1/driving/{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('routes') and len(data['routes']) > 0:
                return data['routes'][0]['distance'] / 1000  # Convert meters to km
    except Exception as e:
        print(f"OSRM error: {e}")
    
    # Fallback to haversine
    return haversine(origin[0], origin[1], destination[0], destination[1])


def get_route_duration(
    origin: Tuple[float, float], 
    destination: Tuple[float, float]
) -> float:
    """
    Get estimated travel time using OSRM.
    Returns duration in minutes.
    """
    try:
        url = f"{OSRM_URL}/route/v1/driving/{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('routes') and len(data['routes']) > 0:
                return data['routes'][0]['duration'] / 60  # Convert seconds to minutes
    except Exception as e:
        print(f"OSRM error: {e}")
    
    # Fallback: assume 30 km/h average speed
    distance = get_route_distance(origin, destination)
    return distance * 2  # 30 km/h = 2 min per km


def get_route_geometry(
    origin: Tuple[float, float], 
    destination: Tuple[float, float]
) -> Optional[List[Tuple[float, float]]]:
    """
    Get the route geometry (list of waypoints) from OSRM.
    """
    try:
        url = f"{OSRM_URL}/route/v1/driving/{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('routes') and len(data['routes']) > 0:
                route = data['routes'][0]
                if route.get('geometry'):
                    # Decode polyline (simplified)
                    # In production, use polyline decoder library
                    return []
    except Exception as e:
        print(f"OSRM error: {e}")
    
    return None


def get_distance_matrix(
    origins: List[Tuple[float, float]], 
    destinations: List[Tuple[float, float]]
) -> List[List[float]]:
    """
    Get a distance matrix between multiple origins and destinations.
    """
    # For now, use haversine (OSRM matrix API would be better)
    matrix = []
    for origin in origins:
        row = []
        for destination in destinations:
            row.append(haversine(origin[0], origin[1], destination[0], destination[1]))
        matrix.append(row)
    return matrix


def get_nearest_road(lat: float, lng: float) -> Optional[Tuple[float, float]]:
    """
    Get the nearest road point using OSRM's nearest service.
    """
    try:
        url = f"{OSRM_URL}/nearest/v1/driving/{lng},{lat}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('waypoints') and len(data['waypoints']) > 0:
                wp = data['waypoints'][0]
                return (wp['location'][1], wp['location'][0])
    except Exception as e:
        print(f"OSRM error: {e}")
    
    return None


def is_osrm_available() -> bool:
    """Check if OSRM server is available."""
    try:
        response = requests.get(f"{OSRM_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False