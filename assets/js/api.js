// assets/js/api.js
// Frontend API client for connecting to the backend

const API_BASE_URL = 'http://localhost:8000/api';

// ================================================================
// API CALL HELPER
// ================================================================

export async function apiCall(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        }
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || error.message || 'API Error');
    }
    
    return response.json();
}

// ================================================================
// AUTH API
// ================================================================

export async function registerPassenger(data) {
    return apiCall('/auth/register/passenger', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function registerDriver(data) {
    return apiCall('/auth/register/driver', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function login(data) {
    return apiCall('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

// ================================================================
// RIDE API
// ================================================================

export async function requestRide(data) {
    return apiCall('/rides/request', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function getPendingRides() {
    return apiCall('/rides/pending');
}

// ================================================================
// DRIVER API
// ================================================================

export async function getAvailableDrivers() {
    return apiCall('/drivers/available');
}

export async function updateDriverLocation(driverId, latitude, longitude) {
    return apiCall(`/drivers/${driverId}/location`, {
        method: 'PUT',
        body: JSON.stringify({ latitude, longitude })
    });
}

export async function updateDriverStatus(driverId, status) {
    return apiCall(`/drivers/${driverId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status })
    });
}

// ================================================================
// DELIVERY API
// ================================================================

export async function createDelivery(data) {
    return apiCall('/deliveries/create', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function getPendingDeliveries() {
    return apiCall('/deliveries/pending');
}

// ================================================================
// SIMULATION API
// ================================================================

export async function initializeSimulation() {
    return apiCall('/simulation/initialize', { method: 'POST' });
}

export async function stepSimulation() {
    return apiCall('/simulation/step', { method: 'POST' });
}

export async function runSimulation(steps = 10) {
    return apiCall(`/simulation/run?steps=${steps}`, { method: 'POST' });
}

export async function getMetrics() {
    return apiCall('/simulation/metrics');
}

export async function getSimulationStatus() {
    return apiCall('/simulation/status');
}