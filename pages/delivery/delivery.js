/**
 * delivery.js - Delivery Page (Sender View) JavaScript
 * Hybrid Ride-Pooling & Delivery System
 */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    console.log('📦 Delivery Sender Page loaded');

    // ================================================================
    //  1.  STATE
    // ================================================================

    let deliveries = [];
    let deliveryIdCounter = 1;
    let pickupMarker = null;
    let dropoffMarker = null;
    let routeLine = null;
    let map = null;
    let pickupCoords = null;
    let dropoffCoords = null;

    // ================================================================
    //  2.  INITIALIZE MAP
    // ================================================================

    const mapContainer = document.getElementById('deliveryMap');

    if (mapContainer && typeof L !== 'undefined') {
        map = L.map('deliveryMap', {
            center: [5.46, 7.02],
            zoom: 12,
            zoomControl: false,
            attributionControl: false,
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '',
        }).addTo(map);

        // Click on map to set pickup or dropoff
        map.on('click', function(e) {
            const lat = e.latlng.lat.toFixed(6);
            const lng = e.latlng.lng.toFixed(6);

            // Determine which location to set based on what's focused or what's missing
            const activeElement = document.activeElement;
            const pickupAddress = document.getElementById('pickupAddress');
            const dropoffAddress = document.getElementById('dropoffAddress');

            // If pickup address is focused or pickup not set, set pickup
            if (activeElement === pickupAddress || !pickupCoords) {
                pickupCoords = { lat: parseFloat(lat), lng: parseFloat(lng) };
                updateMapMarker('pickup', lat, lng);
                showNotification('📍 Pickup location set on map', 'info');
            } else {
                dropoffCoords = { lat: parseFloat(lat), lng: parseFloat(lng) };
                updateMapMarker('dropoff', lat, lng);
                showNotification('📍 Dropoff location set on map', 'info');
            }

            updateFeeEstimate();
        });
    }

    // ================================================================
    //  3.  MAP MARKER FUNCTIONS
    // ================================================================

    function updateMapMarker(type, lat, lng) {
        if (!map) return;

        const icon = L.divIcon({
            className: '',
            html: `<div style="
                background: ${type === 'pickup' ? '#2B8A3E' : '#E85D04'};
                width: 16px;
                height: 16px;
                border-radius: 50%;
                border: 2px solid #fff;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            "></div>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8],
        });

        const marker = L.marker([lat, lng], { icon })
            .bindTooltip(type === 'pickup' ? '📦 Pickup' : '🏠 Dropoff', { permanent: false })
            .addTo(map);

        if (type === 'pickup') {
            if (pickupMarker) {
                map.removeLayer(pickupMarker);
            }
            pickupMarker = marker;
        } else {
            if (dropoffMarker) {
                map.removeLayer(dropoffMarker);
            }
            dropoffMarker = marker;
        }

        // Draw route if both markers exist
        if (pickupMarker && dropoffMarker) {
            drawRoute();
        }

        // Fit bounds to show both markers
        const markers = [];
        if (pickupMarker) markers.push(pickupMarker.getLatLng());
        if (dropoffMarker) markers.push(dropoffMarker.getLatLng());

        if (markers.length > 0) {
            const bounds = L.latLngBounds(markers);
            map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
        }
    }

    function drawRoute() {
        if (!map || !pickupMarker || !dropoffMarker) return;

        if (routeLine) {
            map.removeLayer(routeLine);
        }

        const points = [
            pickupMarker.getLatLng(),
            dropoffMarker.getLatLng()
        ];

        routeLine = L.polyline(points, {
            color: '#7B2FBE',
            weight: 3,
            opacity: 0.7,
            dashArray: '8,6',
        }).addTo(map);
    }

    // ================================================================
    //  4.  FEE ESTIMATE
    // ================================================================

    function updateFeeEstimate() {
        const packageType = document.getElementById('packageType').value;
        const weight = parseFloat(document.getElementById('packageWeight').value) || 0;

        // Calculate distance from coordinates
        let distance = 0;
        if (pickupCoords && dropoffCoords) {
            distance = haversine(
                pickupCoords.lat, pickupCoords.lng,
                dropoffCoords.lat, dropoffCoords.lng
            );
        }

        // Size multiplier based on package type
        const sizeMultipliers = {
            'small': 1,
            'medium': 1.5,
            'large': 2,
            'extra': 2.5
        };
        const sizeMultiplier = sizeMultipliers[packageType] || 1;

        // Weight multiplier
        const weightMultiplier = Math.max(1, weight / 2);

        // Base fee calculation
        const baseFee = 500;
        const distanceFee = distance * 80;
        const sizeFee = (sizeMultiplier - 1) * 200;
        const weightFee = (weightMultiplier - 1) * 100;

        const totalFee = baseFee + distanceFee + sizeFee + weightFee;

        // Update UI
        document.getElementById('feeDistance').textContent = distance.toFixed(1) + ' km';
        document.getElementById('feeSize').textContent = packageType.charAt(0).toUpperCase() + packageType.slice(1) || 'Small';
        document.getElementById('feeTotal').textContent = '₦' + Math.round(totalFee);
        document.getElementById('estimatedFee').textContent = '₦' + Math.round(totalFee);
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

    // ================================================================
    //  5.  FORM EVENT LISTENERS
    // ================================================================

    // Calculate fee on input change
    const feeInputs = ['packageType', 'packageWeight'];
    feeInputs.forEach(function(id) {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateFeeEstimate);
            el.addEventListener('change', updateFeeEstimate);
        }
    });

    // Auto-geocode addresses (simplified)
    document.getElementById('pickupAddress').addEventListener('change', function() {
        const address = this.value.toLowerCase();
        const coords = getCoordinatesFromAddress(address);
        if (coords) {
            pickupCoords = coords;
            updateMapMarker('pickup', coords.lat, coords.lng);
            updateFeeEstimate();
            showNotification('📍 Pickup location updated on map', 'info');
        }
    });

    document.getElementById('dropoffAddress').addEventListener('change', function() {
        const address = this.value.toLowerCase();
        const coords = getCoordinatesFromAddress(address);
        if (coords) {
            dropoffCoords = coords;
            updateMapMarker('dropoff', coords.lat, coords.lng);
            updateFeeEstimate();
            showNotification('📍 Dropoff location updated on map', 'info');
        }
    });

    // Simple address to coordinate mapping (simulated)
    function getCoordinatesFromAddress(address) {
        const locations = {
            'obinze': { lat: 5.362, lng: 6.956 },
            'ihiagwa': { lat: 5.400, lng: 6.989 },
            'nekede': { lat: 5.442, lng: 6.970 },
            'umuguma': { lat: 5.505, lng: 6.965 },
            'futo': { lat: 5.414, lng: 7.016 },
            'world bank': { lat: 5.478, lng: 7.025 },
            'concorde': { lat: 5.460, lng: 7.040 },
            'owerri': { lat: 5.483, lng: 7.035 },
            'federal poly': { lat: 5.442, lng: 6.970 },
            'nekede': { lat: 5.442, lng: 6.970 },
            'imo state': { lat: 5.483, lng: 7.035 },
        };

        for (const [key, coords] of Object.entries(locations)) {
            if (address.includes(key)) {
                return coords;
            }
        }
        return null;
    }

    // ================================================================
    //  6.  SUBMIT DELIVERY FORM
    // ================================================================

    const deliveryForm = document.getElementById('deliveryForm');

    if (deliveryForm) {
        deliveryForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Get form values
            const pickupAddress = document.getElementById('pickupAddress').value;
            const pickupInstructions = document.getElementById('pickupInstructions').value;
            const dropoffAddress = document.getElementById('dropoffAddress').value;
            const packageType = document.getElementById('packageType').value;
            const packageWeight = document.getElementById('packageWeight').value;
            const packageDescription = document.getElementById('packageDescription').value;
            const pickupWindowStart = document.getElementById('pickupWindowStart').value;
            const pickupWindowEnd = document.getElementById('pickupWindowEnd').value;
            const dropoffDeadline = document.getElementById('dropoffDeadline').value;
            const senderName = document.getElementById('senderName').value;
            const senderPhone = document.getElementById('senderPhone').value;

            // Validation
            if (!pickupAddress || !dropoffAddress || !packageType || !packageWeight || !senderName || !senderPhone) {
                showNotification('Please fill in all required fields.', 'error');
                return;
            }

            if (!pickupCoords || !dropoffCoords) {
                showNotification('Please set pickup and dropoff locations on the map.', 'error');
                return;
            }

            // Create delivery object
            const delivery = {
                id: 'D-' + String(deliveryIdCounter).padStart(3, '0'),
                pickupAddress: pickupAddress,
                pickupLat: pickupCoords.lat,
                pickupLng: pickupCoords.lng,
                pickupInstructions: pickupInstructions,
                dropoffAddress: dropoffAddress,
                dropoffLat: dropoffCoords.lat,
                dropoffLng: dropoffCoords.lng,
                packageType: packageType,
                packageWeight: parseFloat(packageWeight),
                packageDescription: packageDescription,
                pickupWindowStart: pickupWindowStart,
                pickupWindowEnd: pickupWindowEnd,
                dropoffDeadline: dropoffDeadline,
                senderName: senderName,
                senderPhone: senderPhone,
                status: 'pending',
                createdAt: new Date().toISOString(),
                fee: document.getElementById('feeTotal').textContent,
            };

            // Add to deliveries list
            deliveries.push(delivery);
            deliveryIdCounter++;

            // Render delivery in list
            renderDelivery(delivery);

            // Update stats
            updateStats();

            // Reset form
            deliveryForm.reset();

            // Reset map markers
            if (pickupMarker) {
                map.removeLayer(pickupMarker);
                pickupMarker = null;
            }
            if (dropoffMarker) {
                map.removeLayer(dropoffMarker);
                dropoffMarker = null;
            }
            if (routeLine) {
                map.removeLayer(routeLine);
                routeLine = null;
            }
            pickupCoords = null;
            dropoffCoords = null;

            // Reset fee
            document.getElementById('feeDistance').textContent = '0 km';
            document.getElementById('feeSize').textContent = 'Small';
            document.getElementById('feeTotal').textContent = '₦500';
            document.getElementById('estimatedFee').textContent = '₦0';

            // Show success message
            showNotification('✅ Delivery task #' + delivery.id + ' created successfully!', 'success');
            console.log('📦 Delivery created:', delivery);

            // Hide empty state
            document.getElementById('emptyState').style.display = 'none';
        });
    }

    // ================================================================
    //  7.  RENDER DELIVERY
    // ================================================================

    function renderDelivery(delivery) {
        const list = document.getElementById('myDeliveriesList');
        const emptyState = document.getElementById('emptyState');

        if (emptyState) {
            emptyState.style.display = 'none';
        }

        const statusLabels = {
            'pending': 'Pending',
            'assigned': 'Assigned',
            'picked_up': 'Picked Up',
            'delivered': 'Delivered'
        };

        const statusClasses = {
            'pending': 'pending',
            'assigned': 'assigned',
            'picked_up': 'picked_up',
            'delivered': 'delivered'
        };

        const fee = delivery.fee || '₦' + Math.round(500 + (delivery.packageWeight || 0) * 100);

        const item = document.createElement('div');
        item.className = 'delivery-item';
        item.dataset.status = delivery.status;
        item.dataset.id = delivery.id;

        const created = new Date(delivery.createdAt);
        const timeStr = created.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        const dateStr = created.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        item.innerHTML = `
            <div class="delivery-status">
                <span class="status-badge ${statusClasses[delivery.status]}">${statusLabels[delivery.status]}</span>
            </div>
            <div class="delivery-info">
                <div class="delivery-header">
                    <h4>📦 ${delivery.packageType.charAt(0).toUpperCase() + delivery.packageType.slice(1)} Parcel <span class="delivery-id">#${delivery.id}</span></h4>
                    <span style="font-size:12px;color:#6C757D;">${dateStr} at ${timeStr}</span>
                </div>
                <div class="delivery-route">
                    <span class="route-point pickup"><i class="fas fa-store"></i> ${delivery.pickupAddress}</span>
                    <span class="route-arrow">→</span>
                    <span class="route-point dropoff"><i class="fas fa-home"></i> ${delivery.dropoffAddress}</span>
                </div>
                <div class="delivery-meta">
                    <span><i class="fas fa-weight-hanging"></i> ${delivery.packageWeight} kg</span>
                    <span><i class="fas fa-tag"></i> ${fee}</span>
                    <span><i class="fas fa-user"></i> ${delivery.senderName}</span>
                    ${delivery.status === 'assigned' || delivery.status === 'picked_up' ? `<span class="driver-name"><i class="fas fa-car"></i> Driver: ${getRandomDriver()}</span>` : ''}
                    ${delivery.status === 'delivered' ? `<span style="color:#2B8A3E;"><i class="fas fa-check-circle"></i> Delivered</span>` : ''}
                </div>
            </div>
            <div class="delivery-actions">
                ${delivery.status === 'pending' ? `
                    <button class="btn btn-outline btn-sm btn-cancel" data-id="${delivery.id}">Cancel</button>
                    <button class="btn btn-outline btn-sm view-details" data-id="${delivery.id}">Details</button>
                ` : `
                    <button class="btn btn-outline btn-sm view-details" data-id="${delivery.id}">Details</button>
                `}
            </div>
        `;

        list.prepend(item);

        // Bind event listeners
        const cancelBtn = item.querySelector('.btn-cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const id = this.dataset.id;
                cancelDelivery(id);
            });
        }

        const viewBtn = item.querySelector('.view-details');
        if (viewBtn) {
            viewBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const id = this.dataset.id;
                viewDeliveryDetails(id);
            });
        }
    }

    // ================================================================
    //  8.  DELIVERY ACTIONS
    // ================================================================

    function cancelDelivery(id) {
        if (confirm('Are you sure you want to cancel this delivery task?')) {
            const index = deliveries.findIndex(d => d.id === id);
            if (index !== -1) {
                deliveries[index].status = 'cancelled';
                const item = document.querySelector(`.delivery-item[data-id="${id}"]`);
                if (item) {
                    item.remove();
                }
                updateStats();
                showNotification('❌ Delivery #' + id + ' cancelled.', 'error');
            }
        }
    }

    function viewDeliveryDetails(id) {
        const delivery = deliveries.find(d => d.id === id);
        if (delivery) {
            const details = `
                📦 Delivery #${delivery.id}
                ─────────────────────
                Pickup: ${delivery.pickupAddress}
                Dropoff: ${delivery.dropoffAddress}
                Package: ${delivery.packageType} (${delivery.packageWeight} kg)
                Status: ${delivery.status}
                Sender: ${delivery.senderName}
                Phone: ${delivery.senderPhone}
                Fee: ${delivery.fee}
            `;
            showNotification('📋 Delivery details shown in console', 'info');
            console.log('📋 Delivery Details:\n' + details);
            alert('📋 Delivery #' + id + '\n\nPickup: ' + delivery.pickupAddress +
                '\nDropoff: ' + delivery.dropoffAddress +
                '\nPackage: ' + delivery.packageType + ' (' + delivery.packageWeight + ' kg)' +
                '\nStatus: ' + delivery.status +
                '\nSender: ' + delivery.senderName +
                '\nFee: ' + delivery.fee);
        }
    }

    function getRandomDriver() {
        const drivers = ['Chidi O.', 'Amara E.', 'Kelechi N.', 'Ngozi B.', 'Emeka I.'];
        return drivers[Math.floor(Math.random() * drivers.length)];
    }

    // ================================================================
    //  9.  FILTER DELIVERIES
    // ================================================================

    const filterBtns = document.querySelectorAll('.delivery-filters .filter-btn');

    filterBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            filterBtns.forEach(function(b) {
                b.classList.remove('active');
            });
            this.classList.add('active');

            const filter = this.dataset.filter;
            const items = document.querySelectorAll('.delivery-item');

            items.forEach(function(item) {
                if (filter === 'all' || item.dataset.status === filter) {
                    item.classList.remove('hidden');
                } else {
                    item.classList.add('hidden');
                }
            });
        });
    });

    // ================================================================
    //  10.  UPDATE STATS
    // ================================================================

    function updateStats() {
        const total = deliveries.length;
        const pending = deliveries.filter(d => d.status === 'pending').length;
        const inProgress = deliveries.filter(d => d.status === 'assigned' || d.status === 'picked_up').length;
        const completed = deliveries.filter(d => d.status === 'delivered').length;

        document.getElementById('totalDeliveries').textContent = total;
        document.getElementById('pendingDeliveries').textContent = pending;
        document.getElementById('inProgressDeliveries').textContent = inProgress;
        document.getElementById('completedDeliveries').textContent = completed;
    }

    // ================================================================
    //  11.  NOTIFICATION SYSTEM
    // ================================================================

    function showNotification(message, type) {
        const existing = document.querySelector('.delivery-notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = 'delivery-notification';
        notification.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 14px 20px;
            border-radius: 12px;
            background: ${type === 'success' ? '#2B8A3E' : type === 'error' ? '#C92A2A' : '#3B2A60'};
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 12px;
            max-width: 400px;
            animation: slideUp 0.3s ease;
            border: none;
        `;

        const icon = type === 'success' ? 'fa-check-circle' :
                     type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';

        notification.innerHTML = `<i class="fas ${icon}"></i> ${message}`;

        document.body.appendChild(notification);

        if (!document.getElementById('notificationStyles')) {
            const style = document.createElement('style');
            style.id = 'notificationStyles';
            style.textContent = `
                @keyframes slideUp {
                    0% { opacity: 0; transform: translateY(20px); }
                    100% { opacity: 1; transform: translateY(0); }
                }
            `;
            document.head.appendChild(style);
        }

        setTimeout(function() {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.3s ease';
            setTimeout(function() {
                notification.remove();
            }, 300);
        }, 4000);
    }

    // ================================================================
    //  12.  KEYBOARD SHORTCUTS
    // ================================================================

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            const submitBtn = document.querySelector('.delivery-form .btn');
            if (submitBtn) submitBtn.click();
        }
    });

    console.log('⌨️ Delivery Page Shortcuts:');
    console.log('  [Ctrl+Enter] Submit delivery form');
    console.log('  Click on map to set pickup/dropoff locations');

    // ================================================================
    //  13.  DEMO: ADD SAMPLE DELIVERY
    // ================================================================

    setTimeout(function() {
        const sampleDelivery = {
            id: 'D-001',
            pickupAddress: 'Obinze Market',
            pickupLat: 5.362,
            pickupLng: 6.956,
            pickupInstructions: 'Call upon arrival',
            dropoffAddress: 'World Bank Estate',
            dropoffLat: 5.478,
            dropoffLng: 7.025,
            packageType: 'small',
            packageWeight: 2.5,
            packageDescription: 'Electronics - Fragile',
            pickupWindowStart: '2026-07-20T09:00',
            pickupWindowEnd: '2026-07-20T10:00',
            dropoffDeadline: '2026-07-20T12:00',
            senderName: 'Chioma O.',
            senderPhone: '+234 800 000 0000',
            status: 'pending',
            createdAt: new Date(Date.now() - 600000).toISOString(),
            fee: '₦1,200',
        };

        deliveries.push(sampleDelivery);
        renderDelivery(sampleDelivery);
        updateStats();
        document.getElementById('emptyState').style.display = 'none';
        console.log('📦 Sample delivery added for demo');
    }, 500);

});