// pages/passenger/passenger.js
import {
    requestRide,
    cancelRide,
    getAvailableDrivers,
    getDriverInfo,
    getPassengerActiveRide,
    getPassengerRides,
    getPassengerWallet,
    getRouteBetween,
    submitRating
} from '../../assets/js/api.js'

// ================================================================
//  1. AUTH CHECK
// ================================================================

const user = JSON.parse(localStorage.getItem('user') || 'null')

if (!user) {
    alert('Please login first')
    window.location.href = '../auth/login.html'
}

if (user.role !== 'passenger') {
    alert('This page is for passengers only')
    window.location.href = '../auth/login.html'
}

const passengerId = user.id
document.getElementById('passengerName').textContent = user.name || 'Passenger'

// ================================================================
//  2. OWERRI ZONES (must match backend/app/algorithms.py exactly)
// ================================================================

const LOCATIONS = [
    { name: 'Owerri Municipal', lat: 5.483, lng: 7.035 },
    { name: 'World Bank', lat: 5.478, lng: 7.025 },
    { name: 'FUTO', lat: 5.414, lng: 7.016 },
    { name: 'Concorde', lat: 5.460, lng: 7.040 },
    { name: 'Obinze', lat: 5.362, lng: 6.956 },
    { name: 'Ihiagwa', lat: 5.400, lng: 6.989 },
    { name: 'Nekede', lat: 5.442, lng: 6.970 },
    { name: 'Umuguma', lat: 5.505, lng: 6.965 }
]

const pickupSelect = document.getElementById('pickupSelect')
const destinationSelect = document.getElementById('destinationSelect')

function populateLocationSelects() {
    LOCATIONS.forEach((loc, idx) => {
        const opt1 = document.createElement('option')
        opt1.value = idx
        opt1.textContent = loc.name
        pickupSelect.appendChild(opt1)

        const opt2 = document.createElement('option')
        opt2.value = idx
        opt2.textContent = loc.name
        destinationSelect.appendChild(opt2)
    })
    pickupSelect.selectedIndex = 0
    destinationSelect.selectedIndex = 1
}
populateLocationSelects()

function haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371
    const dLat = (lat2 - lat1) * Math.PI / 180
    const dLon = (lon2 - lon1) * Math.PI / 180
    const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) ** 2
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

// ================================================================
//  3. NOTIFICATION TOAST
// ================================================================

function showNotification(message, type) {
    const existing = document.querySelector('.passenger-notification')
    if (existing) existing.remove()

    const notification = document.createElement('div')
    notification.className = 'passenger-notification'
    notification.style.cssText = `
        position: fixed; bottom: 24px; right: 24px; padding: 14px 20px;
        border-radius: 12px; background: ${type === 'success' ? '#2B8A3E' : type === 'error' ? '#C92A2A' : '#3B2A60'};
        color: #FFFFFF; font-size: 14px; font-weight: 500;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 9999;
        display: flex; align-items: center; gap: 12px; max-width: 400px;
        opacity: 0; transition: opacity 0.3s ease;
    `
    const icon = type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'
    notification.innerHTML = `<i class="fas ${icon}"></i> ${message}`
    document.body.appendChild(notification)
    requestAnimationFrame(() => notification.style.opacity = '1')

    setTimeout(() => {
        notification.style.opacity = '0'
        setTimeout(() => notification.remove(), 300)
    }, 4000)
}

// ================================================================
//  4. WALLET
// ================================================================

async function loadWallet() {
    try {
        const wallet = await getPassengerWallet(passengerId)
        document.getElementById('walletBalance').textContent = '₦' + Math.round(wallet.wallet_balance).toLocaleString()
    } catch (error) {
        console.error('Error loading wallet:', error)
    }
}

// ================================================================
//  5. RIDE TYPE TOGGLE + FARE ESTIMATE
// ================================================================

const soloToggle = document.getElementById('soloToggle')
const poolToggle = document.getElementById('poolToggle')
const rideInfoText = document.getElementById('rideInfoText')
const estimatedFareEl = document.getElementById('estimatedFare')
const findDriverBtn = document.getElementById('findDriverBtn')

let isPooled = false

function updateFareEstimate() {
    const origin = LOCATIONS[pickupSelect.value]
    const dest = LOCATIONS[destinationSelect.value]
    const distanceKm = haversineKm(origin.lat, origin.lng, dest.lat, dest.lng)

    const baseFare = 800
    let fare = baseFare + distanceKm * 80
    if (isPooled) fare *= 0.70

    estimatedFareEl.textContent = `₦${Math.round(fare).toLocaleString()}`
}

soloToggle.addEventListener('click', () => {
    isPooled = false
    soloToggle.classList.add('active')
    poolToggle.classList.remove('active')
    rideInfoText.textContent = 'Solo ride - just you, no stops for other passengers.'
    findDriverBtn.innerHTML = '<i class="fas fa-search"></i> Find Driver'
    updateFareEstimate()
})

poolToggle.addEventListener('click', () => {
    isPooled = true
    poolToggle.classList.add('active')
    soloToggle.classList.remove('active')
    rideInfoText.textContent = 'Pooled ride - we\'ll try to match you with another passenger heading the same way, for a lower fare.'
    findDriverBtn.innerHTML = '<i class="fas fa-users"></i> Find Pool Match'
    updateFareEstimate()
})

pickupSelect.addEventListener('change', updateFareEstimate)
destinationSelect.addEventListener('change', updateFareEstimate)
updateFareEstimate()

// ================================================================
//  6. UI STATE HELPERS
// ================================================================

const rideRequestCard = document.getElementById('rideRequestCard')
const driverListCard = document.getElementById('driverListCard')
const driverListEl = document.getElementById('driverList')
const poolWaitingCard = document.getElementById('poolWaitingCard')
const waitingCard = document.getElementById('waitingCard')
const waitingDriverName = document.getElementById('waitingDriverName')
const waitingPoolNote = document.getElementById('waitingPoolNote')
const onTripCard = document.getElementById('onTripCard')
const outcomeCard = document.getElementById('outcomeCard')
const outcomeBadge = document.getElementById('outcomeBadge')
const outcomeBody = document.getElementById('outcomeBody')
const outcomeActionBtn = document.getElementById('outcomeActionBtn')
const outcomeDoneBtn = document.getElementById('outcomeDoneBtn')

function showOnly(section) {
    rideRequestCard.style.display = section === 'form' ? 'block' : 'none'
    driverListCard.style.display = section === 'drivers' ? 'block' : 'none'
    poolWaitingCard.style.display = section === 'pool_waiting' ? 'block' : 'none'
    waitingCard.style.display = section === 'waiting' ? 'block' : 'none'
    onTripCard.style.display = section === 'ontrip' ? 'block' : 'none'
    outcomeCard.style.display = section === 'outcome' ? 'block' : 'none'
}

// ================================================================
//  7. FIND DRIVER (solo) -> LIST -> SELECT
// ================================================================

async function loadAvailableDrivers() {
    driverListEl.innerHTML = '<div style="text-align:center; padding:16px; color:#6C757D;"><i class="fas fa-spinner fa-spin"></i> Looking for drivers...</div>'
    try {
        const drivers = await getAvailableDrivers()
        if (!drivers || drivers.length === 0) {
            driverListEl.innerHTML = `
                <div style="text-align:center; padding:24px 12px; color:#6C757D;">
                    <i class="fas fa-car-side" style="font-size:32px; color:#D3C5F6; display:block; margin-bottom:10px;"></i>
                    No drivers are online right now. Try refreshing in a moment.
                </div>`
            return
        }

        driverListEl.innerHTML = drivers.map(d => `
            <div class="passenger-card" style="margin-bottom:10px; cursor:pointer;" data-driver-id="${d.driver_id}">
                <div class="passenger-avatar">🚗</div>
                <div class="passenger-details" style="flex:1;">
                    <h4>${d.name} ${d.rating_count > 0 ? `<span class="badge badge-primary">★ ${d.avg_rating.toFixed(1)}</span>` : ''}</h4>
                    <p><i class="fas fa-car"></i> ${d.vehicle_type || 'Sedan'} &middot; ${d.vehicle_capacity || 4} seats</p>
                </div>
                <button class="btn btn-primary btn-sm select-driver-btn">Select</button>
            </div>
        `).join('')

        driverListEl.querySelectorAll('[data-driver-id]').forEach(card => {
            const driverId = card.dataset.driverId
            const driver = drivers.find(d => d.driver_id === driverId)
            card.querySelector('.select-driver-btn').addEventListener('click', () => selectDriver(driver))
        })
    } catch (error) {
        driverListEl.innerHTML = `<div style="text-align:center; padding:16px; color:#C92A2A;">Error loading drivers: ${error.message}</div>`
    }
}

findDriverBtn.addEventListener('click', () => {
    const originIdx = pickupSelect.value
    const destIdx = destinationSelect.value
    if (originIdx === destIdx) {
        showNotification('⚠️ Pickup and destination cannot be the same.', 'error')
        return
    }

    if (isPooled) {
        startPoolMatch()
    } else {
        showOnly('drivers')
        loadAvailableDrivers()
    }
})

document.getElementById('refreshDriversBtn').addEventListener('click', loadAvailableDrivers)
document.getElementById('cancelFindBtn').addEventListener('click', () => showOnly('form'))

// ================================================================
//  8. POOLED RIDE - AUTO MATCH (Algorithm 1, live)
// ================================================================

let currentRequestId = null

async function startPoolMatch() {
    const origin = LOCATIONS[pickupSelect.value]
    const dest = LOCATIONS[destinationSelect.value]

    try {
        const result = await requestRide({
            passenger_id: passengerId,
            passenger_name: user.name,
            origin_latitude: origin.lat,
            origin_longitude: origin.lng,
            destination_latitude: dest.lat,
            destination_longitude: dest.lng,
            is_pooled: true
            // no driver_id -> backend tries to auto-match with another
            // waiting passenger via the insertion heuristic
        })

        currentRequestId = result.request_id

        if (result.status === 'requested') {
            // Matched immediately with a driver
            const driver = await getDriverInfo(result.driver_id)
            waitingDriverName.textContent = driver.name
            waitingPoolNote.textContent = ' (pooled with another passenger)'
            showOnly('waiting')
        } else {
            // Parked, waiting for another passenger
            showOnly('pool_waiting')
        }

        stopPolling()
        pollTimer = setInterval(pollActiveRide, 3000)
        pollActiveRide()
    } catch (error) {
        showNotification('❌ ' + error.message, 'error')
    }
}

document.getElementById('cancelPoolWaitBtn').addEventListener('click', async () => {
    stopPolling()
    if (currentRequestId) {
        try { await cancelRide(currentRequestId) } catch { /* best effort */ }
    }
    showOnly('form')
})

document.getElementById('bookSoloInsteadBtn').addEventListener('click', async () => {
    stopPolling()
    if (currentRequestId) {
        try { await cancelRide(currentRequestId) } catch { /* best effort */ }
    }
    soloToggle.click()
    showOnly('drivers')
    loadAvailableDrivers()
})

// ================================================================
//  9. SELECT A DRIVER (solo) -> SEND REQUEST -> POLL FOR RESPONSE
// ================================================================

let pollTimer = null
let pollAttempts = 0
const MAX_POLL_ATTEMPTS = 40 // ~2 minutes at 3s interval

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
    }
    pollAttempts = 0
}

async function selectDriver(driver) {
    const origin = LOCATIONS[pickupSelect.value]
    const dest = LOCATIONS[destinationSelect.value]

    try {
        const result = await requestRide({
            passenger_id: passengerId,
            passenger_name: user.name,
            origin_latitude: origin.lat,
            origin_longitude: origin.lng,
            destination_latitude: dest.lat,
            destination_longitude: dest.lng,
            is_pooled: false,
            driver_id: driver.driver_id
        })

        currentRequestId = result.request_id
        waitingDriverName.textContent = driver.name
        waitingPoolNote.textContent = ''
        showOnly('waiting')

        stopPolling()
        pollTimer = setInterval(pollActiveRide, 3000)
        pollActiveRide()
    } catch (error) {
        showNotification('❌ ' + error.message, 'error')
        loadAvailableDrivers()
    }
}

// ================================================================
//  10. UNIFIED POLLING (pool_waiting -> requested -> accepted -> completed)
// ================================================================

let onTripRide = null
let onTripDriver = null

async function pollActiveRide() {
    pollAttempts++
    try {
        const active = await getPassengerActiveRide(passengerId)

        if (!active.has_active_ride) {
            // The ride left the active states - either it was just completed
            // (handled by pollTripCompletion below) or cancelled elsewhere.
            if (pollAttempts >= MAX_POLL_ATTEMPTS) {
                stopPolling()
                showOutcomeGeneric('timeout')
            }
            return
        }

        const ride = active.ride

        if (ride.status === 'pending_pool') {
            showOnly('pool_waiting')
        } else if (ride.status === 'requested') {
            if (waitingDriverName.textContent === 'the driver' || !waitingDriverName.textContent) {
                const driver = await getDriverInfo(ride.driver_id)
                waitingDriverName.textContent = driver.name
            }
            waitingPoolNote.textContent = ride.pool_group_id ? ' (pooled with another passenger)' : ''
            showOnly('waiting')
        } else if (ride.status === 'accepted') {
            stopPolling()
            await enterOnTrip(ride)
        } else if (ride.status === 'rejected') {
            stopPolling()
            showOutcomeGeneric('rejected')
        } else if (pollAttempts >= MAX_POLL_ATTEMPTS) {
            stopPolling()
            showOutcomeGeneric('timeout')
        }
    } catch (error) {
        console.error('Error polling ride status:', error)
    }
}

function showOutcomeGeneric(kind) {
    if (kind === 'rejected') {
        outcomeBadge.innerHTML = '<i class="fas fa-times-circle"></i> Driver Declined'
        outcomeBadge.style.color = '#C92A2A'
        outcomeBody.innerHTML = `<p style="font-size:14px; color:#6C757D;">That driver isn't able to take this ride right now. Please choose another one.</p>`
    } else {
        outcomeBadge.innerHTML = '<i class="fas fa-clock"></i> No Response Yet'
        outcomeBadge.style.color = '#6C757D'
        outcomeBody.innerHTML = `<p style="font-size:14px; color:#6C757D;">No driver has responded yet. Try again.</p>`
    }
    outcomeActionBtn.style.display = 'inline-flex'
    outcomeActionBtn.textContent = 'Choose Another Driver'
    showOnly('outcome')
}

outcomeActionBtn.addEventListener('click', () => {
    showOnly('drivers')
    loadAvailableDrivers()
})

outcomeDoneBtn.addEventListener('click', () => {
    showOnly('form')
    loadRideHistory()
})

document.getElementById('cancelWaitBtn').addEventListener('click', async () => {
    stopPolling()
    if (currentRequestId) {
        try { await cancelRide(currentRequestId) } catch { /* best effort */ }
    }
    showOnly('form')
})

// ================================================================
//  11. ON TRIP - LIVE MAP + WAIT FOR COMPLETION
// ================================================================

let trackingMap = null
let driverMarker = null
let tripCompletionTimer = null

async function enterOnTrip(ride) {
    onTripRide = ride
    const driver = await getDriverInfo(ride.driver_id)
    onTripDriver = driver

    document.getElementById('tripDriverName').textContent = driver.name
    document.getElementById('tripFare').textContent = '₦' + Math.round(ride.fare || 0).toLocaleString()

    const poolNote = document.getElementById('tripPoolNote')
    if (ride.pool_group_id && ride.pool_partner_name) {
        poolNote.style.display = 'block'
        document.getElementById('tripPartnerName').textContent = ride.pool_partner_name
    } else {
        poolNote.style.display = 'none'
    }

    showOnly('ontrip')
    initTrackingMap(ride, driver)

    tripCompletionTimer = setInterval(() => pollTripCompletion(ride.request_id), 4000)
    pollTripCompletion(ride.request_id)
}

function initTrackingMap(ride, driver) {
    const pickup = [ride.origin_latitude, ride.origin_longitude]
    const dest = [ride.destination_latitude, ride.destination_longitude]

    if (trackingMap) {
        trackingMap.remove()
        trackingMap = null
    }

    setTimeout(() => {
        trackingMap = L.map('trackingMap', { zoomControl: true, attributionControl: false })
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(trackingMap)

        L.marker(pickup, { title: 'Pickup' }).addTo(trackingMap).bindPopup('Pickup')
        L.marker(dest, { title: 'Destination' }).addTo(trackingMap).bindPopup('Destination')

        driverMarker = L.circleMarker([driver.current_latitude, driver.current_longitude], {
            radius: 9, color: '#2B8A3E', fillColor: '#2B8A3E', fillOpacity: 1
        }).addTo(trackingMap).bindPopup('Your driver')

        trackingMap.fitBounds([pickup, dest, [driver.current_latitude, driver.current_longitude]], { padding: [30, 30] })

        getRouteBetween(pickup[0], pickup[1], dest[0], dest[1]).then(route => {
            if (route.geometry && route.geometry.length > 1) {
                L.polyline(route.geometry, { color: '#3B2A60', weight: 4, opacity: 0.7 }).addTo(trackingMap)
            }
        }).catch(() => { /* OSRM may not be configured - markers alone are fine */ })

        driverPositionPoll = setInterval(() => updateDriverMarker(driver.driver_id), 5000)
    }, 50)
}

let driverPositionPoll = null

async function updateDriverMarker(driverId) {
    try {
        const driver = await getDriverInfo(driverId)
        if (driverMarker) {
            driverMarker.setLatLng([driver.current_latitude, driver.current_longitude])
        }
    } catch (error) {
        console.error('Error updating driver position:', error)
    }
}

async function pollTripCompletion(requestId) {
    try {
        const active = await getPassengerActiveRide(passengerId)
        if (!active.has_active_ride) {
            // No longer active -> assume completed (driver marked it done)
            clearInterval(tripCompletionTimer)
            if (driverPositionPoll) clearInterval(driverPositionPoll)
            showNotification('✅ Trip completed!', 'success')
            await loadWallet()
            await loadRideHistory()
            showRatingModal(requestId, onTripDriver.driver_id, onTripDriver.name)
            showOnly('form')
        }
    } catch (error) {
        console.error('Error polling trip completion:', error)
    }
}

// ================================================================
//  12. RATE THE DRIVER
// ================================================================

function showRatingModal(requestId, driverId, driverName) {
    const overlay = document.createElement('div')
    overlay.className = 'modal-overlay'
    overlay.innerHTML = `
        <div class="modal-box">
            <h3>Rate ${driverName}</h3>
            <p>How was your trip?</p>
            <div class="star-rating">
                ${[1,2,3,4,5].map(n => `<i class="fas fa-star" data-star="${n}"></i>`).join('')}
            </div>
            <textarea placeholder="Optional comment..." id="ratingComment"></textarea>
            <div class="modal-actions">
                <button class="btn btn-outline" id="skipRatingBtn">Skip</button>
                <button class="btn btn-primary" id="submitRatingBtn" disabled>Submit</button>
            </div>
        </div>
    `
    document.body.appendChild(overlay)
    requestAnimationFrame(() => overlay.classList.add('visible'))

    let selectedStars = 0
    const stars = overlay.querySelectorAll('.star-rating i')
    const submitBtn = overlay.querySelector('#submitRatingBtn')

    stars.forEach(star => {
        star.addEventListener('click', () => {
            selectedStars = parseInt(star.dataset.star)
            stars.forEach(s => s.classList.toggle('selected', parseInt(s.dataset.star) <= selectedStars))
            submitBtn.disabled = false
        })
    })

    function close() {
        overlay.classList.remove('visible')
        setTimeout(() => overlay.remove(), 200)
    }

    overlay.querySelector('#skipRatingBtn').addEventListener('click', close)

    submitBtn.addEventListener('click', async () => {
        submitBtn.disabled = true
        submitBtn.textContent = 'Submitting...'
        try {
            await submitRating({
                request_id: requestId,
                rater_role: 'passenger',
                rater_id: passengerId,
                target_role: 'driver',
                target_id: driverId,
                stars: selectedStars,
                comment: overlay.querySelector('#ratingComment').value || null
            })
            showNotification('⭐ Thanks for your feedback!', 'success')
        } catch (error) {
            showNotification('❌ ' + error.message, 'error')
        }
        close()
    })
}

// ================================================================
//  13. RIDE HISTORY
// ================================================================

async function loadRideHistory() {
    const historyEl = document.getElementById('rideHistory')
    try {
        const rides = await getPassengerRides(passengerId)
        if (!rides || rides.length === 0) {
            historyEl.innerHTML = '<div style="text-align:center; padding:20px; color:#6C757D; font-size:14px;">No rides yet. Book your first ride above!</div>'
            return
        }

        const statusBadge = {
            pending_pool: '<span class="badge badge-secondary">Finding match</span>',
            requested: '<span class="badge badge-warning">Pending</span>',
            accepted: '<span class="badge badge-success">In progress</span>',
            rejected: '<span class="badge badge-danger">Declined</span>',
            completed: '<span class="badge badge-success">Completed</span>',
            pending: '<span class="badge badge-secondary">Unassigned</span>',
            matched: '<span class="badge badge-primary">Matched</span>',
            cancelled: '<span class="badge badge-secondary">Cancelled</span>'
        }

        historyEl.innerHTML = rides.slice(0, 8).map(r => `
            <div class="history-item">
                <div class="history-icon"><i class="fas fa-route"></i></div>
                <div class="history-details">
                    <div class="history-route">${r.origin_latitude.toFixed(3)}, ${r.origin_longitude.toFixed(3)} → ${r.destination_latitude.toFixed(3)}, ${r.destination_longitude.toFixed(3)}</div>
                    <div class="history-meta">
                        ${statusBadge[r.status] || r.status}
                        ${r.is_pooled ? '<span class="badge badge-primary">Pooled</span>' : ''}
                        ${r.fare ? `<span class="history-cost">₦${Math.round(r.fare).toLocaleString()}</span>` : ''}
                    </div>
                </div>
            </div>
        `).join('')
    } catch (error) {
        historyEl.innerHTML = `<div style="text-align:center; padding:16px; color:#C92A2A; font-size:13px;">Error loading ride history: ${error.message}</div>`
    }
}

// ================================================================
//  14. INITIAL LOAD (resume an in-flight ride if the page was refreshed)
// ================================================================

async function init() {
    await loadWallet()
    await loadRideHistory()

    try {
        const active = await getPassengerActiveRide(passengerId)
        if (active.has_active_ride) {
            currentRequestId = active.ride.request_id
            if (active.ride.status === 'accepted') {
                await enterOnTrip(active.ride)
            } else {
                stopPolling()
                pollTimer = setInterval(pollActiveRide, 3000)
                pollActiveRide()
            }
            return
        }
    } catch (error) {
        console.error('Error checking for an active ride:', error)
    }

    showOnly('form')
}

init()
