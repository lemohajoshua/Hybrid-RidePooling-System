// assets/js/supabase-client.js

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm'

const supabaseUrl = 'https://agupysxqsmzommswknse.supabase.co'
const supabaseAnonKey = 'sb_publishable_4kmqLiYrLO2sruv2JYwkdQ_3vSElgX3'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// ================================================================
// AUTH FUNCTIONS
// ================================================================

export async function signUp(email, password, userData, role) {
    const { data: authData, error: authError } = await supabase.auth.signUp({
        email,
        password,
        options: {
            data: {
                name: userData.name,
                phone: userData.phone,
                role: role
            }
        }
    })
    
    if (authError) throw authError
    
    const userId = authData.user.id
    
    if (role === 'passenger') {
        const { error: profileError } = await supabase
            .from('passengers')
            .insert({
                passenger_id: userId,
                name: userData.name,
                phone_number: userData.phone,
                email: email
            })
        if (profileError) throw profileError
    } else if (role === 'driver') {
        const { error: profileError } = await supabase
            .from('drivers')
            .insert({
                driver_id: userId,
                name: userData.name,
                phone_number: userData.phone,
                vehicle_type: userData.vehicleType || 'Sedan',
                vehicle_capacity: userData.vehicleCapacity || 4,
                status: 'idle'
            })
        if (profileError) throw profileError
    }
    
    return authData
}

export async function signIn(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
    })
    if (error) throw error
    return data
}

export async function signOut() {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
}

export async function getCurrentUser() {
    const { data: { user } } = await supabase.auth.getUser()
    return user
}

// ================================================================
// RIDE FUNCTIONS
// ================================================================

export async function createRideRequest(passengerId, rideData) {
    const { data, error } = await supabase
        .from('ride_requests')
        .insert({
            passenger_id: passengerId,
            origin_latitude: rideData.originLat,
            origin_longitude: rideData.originLng,
            destination_latitude: rideData.destLat,
            destination_longitude: rideData.destLng,
            pickup_time_window_start: rideData.pickupWindowStart,
            pickup_time_window_end: rideData.pickupWindowEnd,
            status: 'pending'
        })
        .select()
    if (error) throw error
    return data[0]
}

export async function getPendingRides() {
    const { data, error } = await supabase
        .from('ride_requests')
        .select('*, passengers(name, phone_number)')
        .eq('status', 'pending')
    if (error) throw error
    return data
}

// ================================================================
// DRIVER FUNCTIONS
// ================================================================

export async function getAvailableDrivers() {
    const { data, error } = await supabase
        .from('drivers')
        .select('*')
        .in('status', ['idle', 'en-route'])
    if (error) throw error
    return data
}

export async function updateDriverLocation(driverId, lat, lng) {
    const { error } = await supabase
        .from('drivers')
        .update({
            current_latitude: lat,
            current_longitude: lng
        })
        .eq('driver_id', driverId)
    if (error) throw error
}

export async function updateDriverStatus(driverId, status) {
    const { error } = await supabase
        .from('drivers')
        .update({ status: status })
        .eq('driver_id', driverId)
    if (error) throw error
}

// ================================================================
// DELIVERY FUNCTIONS
// ================================================================

export async function createDeliveryTask(taskData) {
    const { data, error } = await supabase
        .from('delivery_tasks')
        .insert({
            sender_name: taskData.senderName,
            sender_phone: taskData.senderPhone,
            pickup_latitude: taskData.pickupLat,
            pickup_longitude: taskData.pickupLng,
            dropoff_latitude: taskData.dropoffLat,
            dropoff_longitude: taskData.dropoffLng,
            pickup_time_window_start: taskData.pickupWindowStart,
            pickup_time_window_end: taskData.pickupWindowEnd,
            dropoff_time_window_start: taskData.dropoffWindowStart,
            dropoff_time_window_end: taskData.dropoffWindowEnd,
            package_description: taskData.description,
            status: 'pending'
        })
        .select()
    if (error) throw error
    return data[0]
}

export async function getPendingDeliveries() {
    const { data, error } = await supabase
        .from('delivery_tasks')
        .select('*')
        .in('status', ['pending', 'assigned'])
    if (error) throw error
    return data
}

// ================================================================
// TRIP FUNCTIONS
// ================================================================

export async function createTrip(tripData) {
    const { data, error } = await supabase
        .from('trips')
        .insert({
            driver_id: tripData.driverId,
            request_ids: tripData.requestIds || [],
            task_ids: tripData.taskIds || [],
            route_sequence: tripData.routeSequence || [],
            total_distance: tripData.totalDistance,
            total_duration: tripData.totalDuration,
            start_time: tripData.startTime || new Date().toISOString(),
            status: 'planned'
        })
        .select()
    if (error) throw error
    return data[0]
}

// ================================================================
// METRICS FUNCTIONS
// ================================================================

export async function getSummaryMetrics() {
    const { data: trips, error } = await supabase
        .from('trips')
        .select('*')
    if (error) throw error
    
    const totalTrips = trips?.length || 0
    const totalRevenue = trips?.reduce((sum, t) => sum + (t.total_fare || 0), 0) || 0
    const totalDistance = trips?.reduce((sum, t) => sum + (t.total_distance || 0), 0) || 0
    
    return {
        totalTrips,
        totalRevenue,
        totalDistance,
        averageFare: totalTrips > 0 ? totalRevenue / totalTrips : 0
    }
}

export async function getRecentTrips(limit = 5) {
    const { data, error } = await supabase
        .from('trips')
        .select('*, drivers(name)')
        .order('start_time', { ascending: false })
        .limit(limit)
    if (error) throw error
    return data
}