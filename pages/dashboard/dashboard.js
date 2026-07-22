/**
 * dashboard.js - Simulation Dashboard Engine
 * Hybrid Ride-Pooling & Delivery Optimisation System
 * Based on Figma Make (shadcn/ui) design system
 */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    // ================================================================
    //  1.  CONFIGURATION
    // ================================================================

    const CONFIG = {
        bounds: [
            [5.38, 6.94],
            [5.52, 7.08]
        ],
        urbanZones: [
            { name: 'Owerri Municipal', center: [5.483, 7.035], radius: 0.035 },
            { name: 'World Bank', center: [5.478, 7.025], radius: 0.025 },
            { name: 'FUTO', center: [5.414, 7.016], radius: 0.025 },
            { name: 'Concorde', center: [5.460, 7.040], radius: 0.020 }
        ],
        ruralZones: [
            { name: 'Obinze', center: [5.362, 6.956], radius: 0.030 },
            { name: 'Ihiagwa', center: [5.400, 6.989], radius: 0.025 },
            { name: 'Nekede', center: [5.442, 6.970], radius: 0.025 },
            { name: 'Umuguma', center: [5.505, 6.965], radius: 0.030 }
        ],
        numDrivers: 6,
        numPassengers: 18,
        numDeliveries: 8,
        maxDetourFactor: 1.20,
        baseFare: 800,
        deliveryRevenue: 1200,
    };

    // ================================================================
    //  2.  STATE
    // ================================================================

    const state = {
        drivers: [],
        passengers: [],
        deliveries: [],
        trips: [],
        stepCount: 0,
        totalDeadhead: 0,
        totalRevenue: 0,
        totalPassengerCost: 0,
        deliveriesCompleted: 0,
        totalDeliveries: 0,
        isInitialized: false,
        running: false,
        log: [],
    };

    let map = null;
    let mapLayers = {
        drivers: L.layerGroup(),
        passengers: L.layerGroup(),
        deliveries: L.layerGroup(),
        routes: L.layerGroup(),
    };

    // ================================================================
    //  3.  HELPER FUNCTIONS
    // ================================================================

    function randomBetween(min, max) {
        return Math.random() * (max - min) + min;
    }

    function randomInt(min, max) {
        return Math.floor(randomBetween(min, max + 1));
    }

    function haversine(lat1, lon1, lat2, lon2) {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) ** 2;
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    function randomPointInZone(zone) {
        const angle = randomBetween(0, 2 * Math.PI);
        const r = randomBetween(0, zone.radius);
        return [zone.center[0] + r * Math.cos(angle), zone.center[1] + r * Math.sin(angle)];
    }

    function randomPointInBounds() {
        const [minLat, minLng] = CONFIG.bounds[0];
        const [maxLat, maxLng] = CONFIG.bounds[1];
        return [randomBetween(minLat, maxLat), randomBetween(minLng, maxLng)];
    }

    function isUrban(lat, lng) {
        for (const z of CONFIG.urbanZones) {
            if (haversine(lat, lng, z.center[0], z.center[1]) < z.radius * 2) return true;
        }
        return false;
    }

    function formatCurrency(amount) {
        return '₦' + Math.round(amount).toLocaleString();
    }

    // ================================================================
    //  4.  LOGGING
    // ================================================================

    function addLog(message) {
        const ts = state.stepCount;
        state.log.push({ step: ts, message });
        renderLog();
    }

    function renderLog() {
        const box = document.getElementById('logBox');
        if (!box) return;
        const entries = state.log.slice(-20);
        box.innerHTML = entries.map(e =>
            `<div class="log-entry">[${e.step}] ${e.message}</div>`
        ).join('');
        box.scrollTop = box.scrollHeight;
    }

    // ================================================================
    //  5.  INITIALIZATION
    // ================================================================

    function initSimulation() {
        state.drivers = [];
        state.passengers = [];
        state.deliveries = [];
        state.trips = [];
        state.stepCount = 0;
        state.totalDeadhead = 0;
        state.totalRevenue = 0;
        state.totalPassengerCost = 0;
        state.deliveriesCompleted = 0;
        state.totalDeliveries = 0;
        state.log = [];
        state.isInitialized = true;
        state.running = false;

        mapLayers.drivers.clearLayers();
        mapLayers.passengers.clearLayers();
        mapLayers.deliveries.clearLayers();
        mapLayers.routes.clearLayers();

        // Create Drivers
        for (let i = 0; i < CONFIG.numDrivers; i++) {
            let pos = randomPointInBounds();
            let tries = 0;
            while (!isUrban(pos[0], pos[1]) && tries < 20) {
                pos = randomPointInBounds();
                tries++;
            }
            state.drivers.push({
                id: i,
                lat: pos[0],
                lng: pos[1],
                status: 'idle',
                route: [],
                earnings: 0,
                tripsCompleted: 0,
                deadheadKm: 0,
                capacity: 2,
                currentPassengers: [],
                currentDelivery: null,
            });
        }

        // Create Passengers
        state.passengers = [];
        for (let i = 0; i < CONFIG.numPassengers; i++) {
            const origin = randomPointInBounds();
            const dest = randomPointInBounds();
            state.passengers.push({
                id: i,
                origin: origin,
                destination: dest,
                status: 'waiting',
                matchedDriver: null,
                fare: CONFIG.baseFare,
                waitTime: 0,
            });
        }

        // Create Deliveries
        state.deliveries = [];
        state.totalDeliveries = CONFIG.numDeliveries;
        for (let i = 0; i < CONFIG.numDeliveries; i++) {
            const rz = CONFIG.ruralZones[randomInt(0, CONFIG.ruralZones.length - 1)];
            const pickup = randomPointInZone(rz);
            const uz = CONFIG.urbanZones[randomInt(0, CONFIG.urbanZones.length - 1)];
            const dropoff = randomPointInZone(uz);
            state.deliveries.push({
                id: i,
                pickup: pickup,
                dropoff: dropoff,
                status: 'pending',
                assignedDriver: null,
                revenue: CONFIG.deliveryRevenue,
                completionTime: 0,
            });
        }

        addLog('✅ System initialised with ' + state.drivers.length + ' drivers, ' +
            state.passengers.length + ' passengers, ' +
            state.deliveries.length + ' deliveries.');

        renderMap();
        updateStats();
        updateStepCounter();
        updateSystemStatus('Initialized', 'initialized');
        enableControls(true);
    }

    // ================================================================
    //  6.  MAP RENDERING
    // ================================================================

    function initMap() {
        if (map) return;
        map = L.map('map', {
            center: [5.46, 7.02],
            zoom: 12,
            zoomControl: true,
        });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 18,
        }).addTo(map);

        mapLayers.drivers.addTo(map);
        mapLayers.passengers.addTo(map);
        mapLayers.deliveries.addTo(map);
        mapLayers.routes.addTo(map);

        // Zone boundaries
        for (const z of CONFIG.urbanZones) {
            L.circle(z.center, { radius: z.radius * 2000, color: '#2b8a3e', fill: false, weight: 1, dashArray: '4,4' })
                .addTo(map);
        }
        for (const z of CONFIG.ruralZones) {
            L.circle(z.center, { radius: z.radius * 2000, color: '#e85d04', fill: false, weight: 1, dashArray: '4,4' })
                .addTo(map);
        }

        // Zone labels
        for (const z of CONFIG.urbanZones) {
            L.marker(z.center, { icon: L.divIcon({ className: '', html: '🏙️', iconSize: [20, 20] }) })
                .bindTooltip(z.name, { permanent: false, direction: 'top' })
                .addTo(map);
        }
        for (const z of CONFIG.ruralZones) {
            L.marker(z.center, { icon: L.divIcon({ className: '', html: '🌾', iconSize: [20, 20] }) })
                .bindTooltip(z.name, { permanent: false, direction: 'top' })
                .addTo(map);
        }
    }

    function renderMap() {
        if (!map) return;

        mapLayers.drivers.clearLayers();
        mapLayers.passengers.clearLayers();
        mapLayers.deliveries.clearLayers();
        mapLayers.routes.clearLayers();

        // Drivers
        for (const d of state.drivers) {
            const icon = L.divIcon({
                className: '',
                html: d.status === 'idle' ? '🚗' : '🚕',
                iconSize: [28, 28],
            });
            const m = L.marker([d.lat, d.lng], { icon })
                .bindTooltip('Driver ' + d.id + ' (' + d.status + ')', { permanent: false });
            mapLayers.drivers.addLayer(m);

            if (d.route && d.route.length > 1) {
                const latlngs = d.route.map(p => [p[0], p[1]]);
                const polyline = L.polyline(latlngs, {
                    color: '#7b2fbe',
                    weight: 3,
                    opacity: 0.7,
                    dashArray: '6,6',
                });
                mapLayers.routes.addLayer(polyline);
            }
        }

        // Passengers
        for (const p of state.passengers) {
            if (p.status === 'completed') continue;
            const isUrb = isUrban(p.origin[0], p.origin[1]);
            const emoji = isUrb ? '🧑' : '👨‍🌾';
            const icon = L.divIcon({
                className: '',
                html: emoji,
                iconSize: [24, 24],
            });
            const m = L.marker([p.origin[0], p.origin[1]], { icon })
                .bindTooltip('Pax ' + p.id + (p.status === 'matched' ? ' (matched)' : ' (waiting)'), {
                    permanent: false
                });
            mapLayers.passengers.addLayer(m);

            const destIcon = L.divIcon({
                className: '',
                html: '📍',
                iconSize: [16, 16],
            });
            const dm = L.marker([p.destination[0], p.destination[1]], { icon: destIcon })
                .bindTooltip('Dest ' + p.id, { permanent: false });
            mapLayers.passengers.addLayer(dm);
        }

        // Deliveries
        for (const dl of state.deliveries) {
            if (dl.status === 'delivered') continue;
            const icon = L.divIcon({
                className: '',
                html: '📦',
                iconSize: [24, 24],
            });
            const m = L.marker([dl.pickup[0], dl.pickup[1]], { icon })
                .bindTooltip('Delivery ' + dl.id + ' (' + dl.status + ')', { permanent: false });
            mapLayers.deliveries.addLayer(m);

            const dropIcon = L.divIcon({
                className: '',
                html: '🏠',
                iconSize: [16, 16],
            });
            const dm = L.marker([dl.dropoff[0], dl.dropoff[1]], { icon: dropIcon })
                .bindTooltip('Dropoff ' + dl.id, { permanent: false });
            mapLayers.deliveries.addLayer(dm);
        }
    }

    // ================================================================
    //  7.  ALGORITHMS (from Chapter 3 of your project)
    // ================================================================

    // Algorithm 1: Insertion Heuristic for Ride-Pooling
    function findRidePoolingMatch(driver, passenger) {
        if (driver.currentPassengers.length >= driver.capacity) return null;

        const currentPos = [driver.lat, driver.lng];
        const existingStops = driver.route.length > 0 ? driver.route : [currentPos];
        const P_p = passenger.origin;
        const D_p = passenger.destination;

        let bestDelta = Infinity;
        let bestRoute = null;

        for (let i = 0; i <= existingStops.length; i++) {
            for (let j = i + 1; j <= existingStops.length + 1; j++) {
                const route = [];
                for (let k = 0; k < existingStops.length; k++) {
                    if (k === i) route.push(P_p);
                    route.push(existingStops[k]);
                    if (k === j - 1) route.push(D_p);
                }
                if (i === existingStops.length) route.push(P_p);
                if (j === existingStops.length + 1) route.push(D_p);

                let totalDist = 0;
                let prev = currentPos;
                for (const stop of route) {
                    totalDist += haversine(prev[0], prev[1], stop[0], stop[1]);
                    prev = stop;
                }

                let origDist = 0;
                prev = currentPos;
                for (const stop of existingStops) {
                    origDist += haversine(prev[0], prev[1], stop[0], stop[1]);
                    prev = stop;
                }

                const delta = totalDist - origDist;
                const detourFactor = (totalDist / (origDist + 0.001));

                if (detourFactor <= CONFIG.maxDetourFactor && delta < bestDelta) {
                    bestDelta = delta;
                    bestRoute = route;
                }
            }
        }

        if (bestRoute && bestDelta < 5) {
            return { route: bestRoute, delta: bestDelta };
        }
        return null;
    }

    // Algorithm 2: Deadhead Reduction Scoring
    function calculateDeadheadScore(driver, delivery) {
        const L_d = [driver.lat, driver.lng];
        const P_t = delivery.pickup;
        const D_t = delivery.dropoff;

        let nearestUrban = null;
        let minDist = Infinity;
        for (const z of CONFIG.urbanZones) {
            const d = haversine(D_t[0], D_t[1], z.center[0], z.center[1]);
            if (d < minDist) {
                minDist = d;
                nearestUrban = z.center;
            }
        }
        if (!nearestUrban) return 0;

        const H = nearestUrban;
        const d1 = haversine(L_d[0], L_d[1], P_t[0], P_t[1]);
        const d2 = haversine(P_t[0], P_t[1], D_t[0], D_t[1]);
        const d3 = haversine(D_t[0], D_t[1], H[0], H[1]);
        const baseline = haversine(L_d[0], L_d[1], H[0], H[1]);
        const deadheadWithDelivery = d1 + d3;
        const reduction = baseline - deadheadWithDelivery;
        return Math.max(0, reduction / (d1 + d2 + 0.001));
    }

    // Algorithm 3: Hybrid Mode Switching
    function switchMode(driver) {
        const lat = driver.lat;
        const lng = driver.lng;

        const nearbyPassengers = state.passengers.filter(p =>
            p.status === 'waiting' &&
            haversine(lat, lng, p.origin[0], p.origin[1]) < 5
        );

        const demandDensity = nearbyPassengers.length;

        if (demandDensity >= 1) {
            const availablePax = state.passengers.filter(p =>
                p.status === 'waiting' && p.matchedDriver === null
            );

            availablePax.sort((a, b) => {
                const da = haversine(lat, lng, a.origin[0], a.origin[1]);
                const db = haversine(lat, lng, b.origin[0], b.origin[1]);
                return da - db;
            });

            for (const pax of availablePax) {
                const match = findRidePoolingMatch(driver, pax);
                if (match) {
                    pax.status = 'matched';
                    pax.matchedDriver = driver.id;
                    driver.currentPassengers.push(pax.id);
                    driver.route = match.route;
                    driver.status = 'en-route';
                    state.trips.push({
                        type: 'ride-pooling',
                        driverId: driver.id,
                        passengerIds: [pax.id],
                        route: match.route,
                        revenue: pax.fare * 0.8,
                        distance: calculateRouteDistance(match.route),
                    });
                    addLog(`🚗 Driver ${driver.id} matched with Passenger ${pax.id} (pooling)`);
                    return 'ride-pooling';
                }
            }

            // Single passenger
            for (const pax of availablePax) {
                const dist = haversine(lat, lng, pax.origin[0], pax.origin[1]);
                if (dist < 3) {
                    pax.status = 'matched';
                    pax.matchedDriver = driver.id;
                    driver.currentPassengers.push(pax.id);
                    driver.route = [pax.origin, pax.destination];
                    driver.status = 'en-route';
                    state.trips.push({
                        type: 'single',
                        driverId: driver.id,
                        passengerIds: [pax.id],
                        route: [pax.origin, pax.destination],
                        revenue: pax.fare,
                        distance: haversine(pax.origin[0], pax.origin[1], pax.destination[0], pax.destination[1]),
                    });
                    addLog(`🚗 Driver ${driver.id} assigned to Passenger ${pax.id} (single)`);
                    return 'single';
                }
            }
        } else {
            // Low demand -> try delivery
            const availableDeliveries = state.deliveries.filter(d =>
                d.status === 'pending' || d.status === 'assigned'
            );

            let bestScore = 0;
            let bestDelivery = null;
            for (const dl of availableDeliveries) {
                const score = calculateDeadheadScore(driver, dl);
                if (score > bestScore) {
                    bestScore = score;
                    bestDelivery = dl;
                }
            }

            if (bestDelivery && bestScore > 0.5) {
                bestDelivery.status = 'assigned';
                bestDelivery.assignedDriver = driver.id;
                driver.currentDelivery = bestDelivery.id;
                driver.route = [bestDelivery.pickup, bestDelivery.dropoff];
                driver.status = 'en-route';
                state.trips.push({
                    type: 'delivery',
                    driverId: driver.id,
                    deliveryId: bestDelivery.id,
                    route: [bestDelivery.pickup, bestDelivery.dropoff],
                    revenue: CONFIG.deliveryRevenue,
                    distance: haversine(bestDelivery.pickup[0], bestDelivery.pickup[1],
                        bestDelivery.dropoff[0], bestDelivery.dropoff[1]),
                });
                addLog(`📦 Driver ${driver.id} assigned to Delivery ${bestDelivery.id} (score: ${bestScore.toFixed(2)})`);
                return 'delivery';
            }
        }

        return 'idle';
    }

    function calculateRouteDistance(route) {
        let total = 0;
        for (let i = 1; i < route.length; i++) {
            total += haversine(route[i - 1][0], route[i - 1][1], route[i][0], route[i][1]);
        }
        return total;
    }

    // ================================================================
    //  8.  STEP FUNCTION
    // ================================================================

    function stepSimulation() {
        if (!state.isInitialized) {
            addLog('⚠️ Please initialize the system first.');
            return;
        }

        state.stepCount++;

        for (const driver of state.drivers) {
            if (driver.status === 'idle') {
                const mode = switchMode(driver);
                if (mode === 'idle') {
                    driver.lat += randomBetween(-0.005, 0.005);
                    driver.lng += randomBetween(-0.005, 0.005);
                    driver.lat = Math.max(CONFIG.bounds[0][0], Math.min(CONFIG.bounds[1][0], driver.lat));
                    driver.lng = Math.max(CONFIG.bounds[0][1], Math.min(CONFIG.bounds[1][1], driver.lng));
                }
            }

            if (driver.status === 'en-route' && driver.route && driver.route.length > 1) {
                const target = driver.route[0];
                const dx = target[0] - driver.lat;
                const dy = target[1] - driver.lng;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 0.003) {
                    const stop = driver.route.shift();

                    for (const p of state.passengers) {
                        if (p.status === 'matched' && p.matchedDriver === driver.id) {
                            if (haversine(driver.lat, driver.lng, p.origin[0], p.origin[1]) < 0.003) {
                                addLog(`📍 Driver ${driver.id} picked up Passenger ${p.id}`);
                            }
                            if (haversine(driver.lat, driver.lng, p.destination[0], p.destination[1]) < 0.003) {
                                p.status = 'completed';
                                p.matchedDriver = null;
                                driver.currentPassengers = driver.currentPassengers.filter(id => id !== p.id);
                                driver.earnings += p.fare;
                                driver.tripsCompleted++;
                                state.totalRevenue += p.fare;
                                state.totalPassengerCost += p.fare;
                                addLog(`✅ Driver ${driver.id} dropped off Passenger ${p.id} (earned ${formatCurrency(p.fare)})`);
                            }
                        }
                    }

                    for (const dl of state.deliveries) {
                        if (dl.assignedDriver === driver.id) {
                            if (dl.status === 'assigned' &&
                                haversine(driver.lat, driver.lng, dl.pickup[0], dl.pickup[1]) < 0.003) {
                                dl.status = 'picked_up';
                                addLog(`📦 Driver ${driver.id} picked up Delivery ${dl.id}`);
                            }
                            if (dl.status === 'picked_up' &&
                                haversine(driver.lat, driver.lng, dl.dropoff[0], dl.dropoff[1]) < 0.003) {
                                dl.status = 'delivered';
                                dl.completionTime = state.stepCount;
                                driver.earnings += CONFIG.deliveryRevenue;
                                state.deliveriesCompleted++;
                                state.totalRevenue += CONFIG.deliveryRevenue;
                                addLog(`✅ Driver ${driver.id} delivered Delivery ${dl.id} (earned ${formatCurrency(CONFIG.deliveryRevenue)})`);
                            }
                        }
                    }

                    const deadhead = 0.5 + Math.random() * 0.5;
                    driver.deadheadKm += deadhead;
                    state.totalDeadhead += deadhead;

                    if (driver.route.length === 0) {
                        driver.status = 'idle';
                        driver.currentDelivery = null;
                        driver.lat = stop[0];
                        driver.lng = stop[1];
                        addLog(`🔄 Driver ${driver.id} is now idle`);
                    }
                } else {
                    const stepSize = 0.008;
                    const ratio = Math.min(1, stepSize / (dist + 0.001));
                    driver.lat += dx * ratio;
                    driver.lng += dy * ratio;
                }
            }
        }

        for (const p of state.passengers) {
            if (p.status === 'waiting') {
                p.waitTime++;
            }
        }

        if (state.stepCount % 5 === 0) {
            const completedPax = state.passengers.filter(p => p.status === 'completed').length;
            const deliveredCount = state.deliveries.filter(d => d.status === 'delivered').length;
            addLog(`📊 Step ${state.stepCount}: ${completedPax}/${state.passengers.length} passengers completed, ${deliveredCount}/${state.deliveries.length} deliveries delivered`);
        }

        renderMap();
        updateStats();
        updateStepCounter();
        updateSystemStatus('Running', 'running');
    }

    // ================================================================
    //  9.  UI UPDATES
    // ================================================================

    function updateStats() {
        const totalPax = state.passengers.length;
        const completedPax = state.passengers.filter(p => p.status === 'completed').length;
        const deliveredCount = state.deliveries.filter(d => d.status === 'delivered').length;

        const baselineDeadhead = state.stepCount * 0.5 * state.drivers.length;
        const currentDeadhead = state.totalDeadhead;
        const reduction = baselineDeadhead > 0 ?
            Math.round((1 - currentDeadhead / baselineDeadhead) * 100) :
            0;

        const avgIncome = state.drivers.reduce((sum, d) => sum + d.earnings, 0) / state.drivers.length || 0;
        const avgCost = completedPax > 0 ? state.totalPassengerCost / completedPax : 0;
        const completionRate = state.totalDeliveries > 0 ?
            Math.round((deliveredCount / state.totalDeliveries) * 100) :
            0;

        document.getElementById('statDeadhead').textContent = Math.max(0, reduction) + '%';
        document.getElementById('statIncome').textContent = formatCurrency(avgIncome);
        document.getElementById('statCost').textContent = formatCurrency(avgCost);
        document.getElementById('statDelivery').textContent = completionRate + '%';
    }

    function updateStepCounter() {
        const el = document.getElementById('stepCounter');
        if (el) el.textContent = state.stepCount;
    }

    function updateSystemStatus(text, statusClass) {
        const el = document.getElementById('systemStatus');
        const dot = document.getElementById('statusDot');
        if (el) el.textContent = text;
        if (dot) {
            dot.className = 'status-dot';
            if (statusClass) dot.classList.add(statusClass);
        }
    }

    function enableControls(enabled) {
        document.getElementById('btnStep').disabled = !enabled;
        document.getElementById('btnRun').disabled = !enabled;
        document.getElementById('btnReset').disabled = !enabled;
        document.getElementById('btnInit').disabled = enabled;
    }

    // ================================================================
    //  10.  UI EVENT BINDING
    // ================================================================

    if (document.getElementById('map')) {
        initMap();
    }

    const btnInit = document.getElementById('btnInit');
    const btnStep = document.getElementById('btnStep');
    const btnRun = document.getElementById('btnRun');
    const btnReset = document.getElementById('btnReset');

    if (btnInit) {
        btnInit.addEventListener('click', function() {
            initSimulation();
            addLog('▶️ Simulation ready. Click Step or Run to simulate.');
            updateSystemStatus('Initialized', 'initialized');
        });
    }

    if (btnStep) {
        btnStep.addEventListener('click', function() {
            if (!state.isInitialized) {
                addLog('⚠️ Please initialize first.');
                return;
            }
            stepSimulation();
        });
    }

    if (btnRun) {
        btnRun.addEventListener('click', function() {
            if (!state.isInitialized) {
                addLog('⚠️ Please initialize first.');
                return;
            }
            if (state.running) return;
            state.running = true;
            this.disabled = true;
            let steps = 0;
            const interval = setInterval(() => {
                stepSimulation();
                steps++;
                if (steps >= 10) {
                    clearInterval(interval);
                    state.running = false;
                    btnRun.disabled = false;
                    addLog('⏹️ Run completed.');
                    updateSystemStatus('Ready', 'ready');
                }
            }, 500);
        });
    }

    if (btnReset) {
        btnReset.addEventListener('click', function() {
            state.isInitialized = false;
            state.running = false;
            state.stepCount = 0;
            state.totalDeadhead = 0;
            state.totalRevenue = 0;
            state.totalPassengerCost = 0;
            state.deliveriesCompleted = 0;
            state.log = [];
            state.drivers = [];
            state.passengers = [];
            state.deliveries = [];
            state.trips = [];

            if (map) {
                mapLayers.drivers.clearLayers();
                mapLayers.passengers.clearLayers();
                mapLayers.deliveries.clearLayers();
                mapLayers.routes.clearLayers();
            }

            document.getElementById('btnInit').disabled = false;
            document.getElementById('btnStep').disabled = true;
            document.getElementById('btnRun').disabled = true;
            document.getElementById('btnReset').disabled = true;

            document.getElementById('statDeadhead').textContent = '0%';
            document.getElementById('statIncome').textContent = '₦0';
            document.getElementById('statCost').textContent = '₦0';
            document.getElementById('statDelivery').textContent = '0%';
            updateStepCounter();
            updateSystemStatus('Ready', 'ready');

            addLog('🔄 System reset. Click Initialize to start again.');
            renderLog();
        });
    }

    // Welcome log
    addLog('🚀 Welcome to the RidePool+ Simulation Dashboard.');
    addLog('📌 Click "Initialize" to set up the simulation.');

});