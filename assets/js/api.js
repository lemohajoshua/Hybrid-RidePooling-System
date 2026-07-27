// assets/js/api.js
// Frontend API client for connecting to the backend

const API_BASE_URL = 'http://localhost:8000/api';

// ================================================================
// API CALL HELPER
// ================================================================

export async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('token');

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...(options.headers || {})
        }
    });

    if (!response.ok) {
        let error;
        try {
            error = await response.json();
        } catch {
            error = {};
        }
        throw new Error(error.detail || error.message || `API Error (${response.status})`);
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
    // data can include a `driver_id` to send the request straight to one
    // driver, or set `is_pooled: true` with no driver_id to be auto-matched
    // with another passenger via the insertion heuristic.
    return apiCall('/rides/request', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function cancelRide(requestId) {
    return apiCall(`/rides/${requestId}/cancel`, { method: 'PUT' });
}

export async function getOpenPools(excludePassengerId) {
    return apiCall(`/rides/open-pools?exclude_passenger_id=${excludePassengerId}`);
}

export async function joinPool(requestId, data) {
    return apiCall(`/rides/${requestId}/join`, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

export async function getPendingRides() {
    return apiCall('/rides/pending');
}

export async function getRide(requestId) {
    return apiCall(`/rides/${requestId}`);
}

export async function respondToRide(requestId, driverId, decision) {
    // decision: 'accept' | 'reject'
    return apiCall(`/rides/${requestId}/respond`, {
        method: 'PUT',
        body: JSON.stringify({ driver_id: driverId, decision })
    });
}

export async function getIncomingRequestsForDriver(driverId) {
    return apiCall(`/rides/driver/${driverId}/incoming`);
}

export async function getDriverActiveRide(driverId) {
    return apiCall(`/rides/driver/${driverId}/active`);
}

export async function completeRide(requestId) {
    return apiCall(`/rides/${requestId}/complete`, {
        method: 'PUT'
    });
}

// ================================================================
// PASSENGER API
// ================================================================

export async function getPassenger(passengerId) {
    return apiCall(`/passengers/${passengerId}`);
}

export async function getPassengerWallet(passengerId) {
    return apiCall(`/passengers/${passengerId}/wallet`);
}

export async function getPassengerActiveRide(passengerId) {
    return apiCall(`/passengers/${passengerId}/active-ride`);
}

export async function getPassengerRides(passengerId) {
    return apiCall(`/passengers/${passengerId}/rides`);
}

// ================================================================
// DRIVER API
// ================================================================

export async function getAvailableDrivers() {
    return apiCall('/drivers/available');
}

export async function getDriverInfo(driverId) {
    return apiCall(`/drivers/${driverId}`);
}

export async function getDriverEarnings(driverId) {
    return apiCall(`/drivers/${driverId}/earnings`);
}

export async function getSuggestedMode(driverId) {
    return apiCall(`/drivers/${driverId}/suggested-mode`);
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

export async function setDriverOnline(driverId, isOnline) {
    return apiCall(`/drivers/${driverId}/online`, {
        method: 'PUT',
        body: JSON.stringify({ is_online: isOnline })
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

export async function getAvailableDeliveries(driverLat, driverLng) {
    return apiCall(`/deliveries/available?driver_lat=${driverLat}&driver_lng=${driverLng}`);
}

export async function getDriverTasks(driverId) {
    return apiCall(`/deliveries/driver/${driverId}/tasks`);
}

export async function assignDelivery(taskId) {
    return apiCall(`/deliveries/${taskId}/assign`, {
        method: 'PUT'
    });
}

export async function updateDeliveryStatus(taskId, driverId, status) {
    return apiCall(`/deliveries/${taskId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ driver_id: driverId, status })
    });
}

// ================================================================
// RATINGS API
// ================================================================

export async function submitRating(data) {
    // { request_id, rater_role, rater_id, target_role, target_id, stars, comment }
    return apiCall('/ratings/', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function getRatingsFor(targetRole, targetId) {
    return apiCall(`/ratings/for/${targetRole}/${targetId}`);
}

export async function getPendingRatingStatus(requestId) {
    return apiCall(`/ratings/pending/${requestId}`);
}

// ================================================================
// ANALYTICS API
// ================================================================

export async function getDemandAnalytics() {
    return apiCall('/analytics/demand');
}

// ================================================================
// TRACKING / ROUTING API
// ================================================================

export async function getRouteBetween(originLat, originLng, destLat, destLng) {
    return apiCall(`/tracking/route?origin_lat=${originLat}&origin_lng=${originLng}&dest_lat=${destLat}&dest_lng=${destLng}`);
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
