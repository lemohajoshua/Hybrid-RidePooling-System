/**
 * driver.js - Driver Page Specific JavaScript
 * Hybrid Ride-Pooling & Delivery System
 * Based on Figma Make (shadcn/ui) design system
 */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    console.log('🚗 Driver Page loaded');

    // ================================================================
    //  1.  STATUS TOGGLE (Online/Offline)
    // ================================================================

    const statusToggle = document.getElementById('statusToggle');
    const statusBadge = document.getElementById('statusBadge');
    const statusText = document.getElementById('statusText');

    if (statusToggle && statusBadge) {
        statusToggle.addEventListener('change', function() {
            if (this.checked) {
                statusBadge.className = 'status-badge online';
                statusText.textContent = 'Online';
            } else {
                statusBadge.className = 'status-badge offline';
                statusText.textContent = 'Offline';
            }
        });
    }

    // ================================================================
    //  2.  NOTIFICATION BANNER
    // ================================================================

    const notificationBanner = document.getElementById('notificationBanner');
    const closeNotification = document.getElementById('closeNotification');
    const acceptDelivery = document.getElementById('acceptDelivery');
    const declineDelivery = document.getElementById('declineDelivery');

    if (closeNotification && notificationBanner) {
        closeNotification.addEventListener('click', function() {
            notificationBanner.classList.add('hidden');
        });
    }

    if (acceptDelivery && notificationBanner) {
        acceptDelivery.addEventListener('click', function() {
            // Show acceptance feedback
            this.innerHTML = '<i class="fas fa-check"></i> Accepted!';
            this.style.background = '#2B8A3E';

            // Add to assignment
            const deliveryAssignment = document.getElementById('deliveryAssignment');
            const rideAssignment = document.getElementById('ridePoolingAssignment');

            if (deliveryAssignment && rideAssignment) {
                // Switch to delivery assignment
                rideAssignment.style.display = 'none';
                deliveryAssignment.style.display = 'block';
                document.getElementById('assignmentType').textContent = 'Delivery';
                document.getElementById('assignmentType').className = 'badge badge-warning';
            }

            // Hide notification
            setTimeout(() => {
                notificationBanner.classList.add('hidden');
                this.innerHTML = '<i class="fas fa-check"></i> Accept';
                this.style.background = '';
            }, 1500);
        });
    }

    if (declineDelivery && notificationBanner) {
        declineDelivery.addEventListener('click', function() {
            notificationBanner.classList.add('hidden');
        });
    }

    // ================================================================
    //  3.  START TRIP / DELIVERY BUTTONS
    // ================================================================

    const startTripBtn = document.getElementById('startTripBtn');
    const startDeliveryBtn = document.getElementById('startDeliveryBtn');

    if (startTripBtn) {
        startTripBtn.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';
            this.disabled = true;

            setTimeout(() => {
                this.innerHTML = '<i class="fas fa-check"></i> Trip Started!';
                this.style.background = '#2B8A3E';

                // Update status badge
                document.querySelector('.passenger-ride-header .badge-success').textContent = 'In Progress';

                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                    this.style.background = '';
                }, 2000);
            }, 1500);
        });
    }

    if (startDeliveryBtn) {
        startDeliveryBtn.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';
            this.disabled = true;

            setTimeout(() => {
                this.innerHTML = '<i class="fas fa-check"></i> Delivery Started!';
                this.style.background = '#2B8A3E';

                // Update delivery status
                const statusBadge = document.querySelector('.delivery-package .badge');
                if (statusBadge) {
                    statusBadge.textContent = 'In Progress';
                    statusBadge.className = 'badge badge-success';
                }

                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                    this.style.background = '';
                }, 2000);
            }, 1500);
        });
    }

    // ================================================================
    //  4.  ROUTE MAP (Leaflet.js)
    // ================================================================

    const routeMapContainer = document.getElementById('routeMap');
    if (routeMapContainer) {
        // Check if Leaflet is loaded
        if (typeof L !== 'undefined') {
            const map = L.map('routeMap', {
                center: [5.46, 7.02],
                zoom: 13,
                zoomControl: false,
                attributionControl: false,
            });

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: '',
            }).addTo(map);

            // Define route points
            const routePoints = [
                [5.414, 7.016], // FUTO Gate
                [5.460, 7.040], // Concorde Hotel
                [5.478, 7.025], // World Bank
                [5.478, 7.025], // World Bank (same for second dropoff)
            ];

            // Draw route line
            const polyline = L.polyline(routePoints, {
                color: '#7b2fbe',
                weight: 4,
                opacity: 0.7,
                dashArray: '8,6',
            }).addTo(map);

            // Add markers for each stop
            const stopIcons = [
                { icon: '📍', label: 'Pickup A' },
                { icon: '📍', label: 'Pickup B' },
                { icon: '🏁', label: 'Dropoff A' },
                { icon: '🏁', label: 'Dropoff B' },
            ];

            routePoints.forEach(function(point, index) {
                const markerIcon = L.divIcon({
                    className: 'route-marker',
                    html: `
                        <div style="
                            background: #3B2A60;
                            color: #FFFFFF;
                            width: 28px;
                            height: 28px;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 12px;
                            font-weight: 700;
                            border: 2px solid #D3C5F6;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                        ">
                            ${index + 1}
                        </div>
                    `,
                    iconSize: [28, 28],
                    iconAnchor: [14, 14],
                });

                L.marker([point[0], point[1]], { icon: markerIcon })
                    .bindTooltip(stopIcons[index].label + ' - ' + stopIcons[index].label, {
                        permanent: false,
                        direction: 'top',
                    })
                    .addTo(map);
            });

            // Fit bounds
            map.fitBounds(polyline.getBounds(), {
                padding: [40, 40],
                maxZoom: 14,
            });
        } else {
            // Fallback if Leaflet not loaded
            routeMapContainer.innerHTML = `
                <div style="
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #F0EDF5;
                    border-radius: 12px;
                    color: #6C757D;
                    font-size: 14px;
                    flex-direction: column;
                    gap: 8px;
                ">
                    <i class="fas fa-map" style="font-size: 32px; color: #D3C5F6;"></i>
                    <span>Route Map Loading...</span>
                    <span style="font-size: 12px;">4 Stops: FUTO → Concorde → World Bank</span>
                </div>
            `;
        }
    }

    // ================================================================
    //  5.  ROUTE STOP INTERACTIONS
    // ================================================================

    const routeStopItems = document.querySelectorAll('.route-stop-item');
    routeStopItems.forEach(function(item) {
        item.addEventListener('click', function() {
            // Remove active from all
            routeStopItems.forEach(function(el) {
                el.classList.remove('active');
            });
            // Add active to clicked
            this.classList.add('active');

            // Scroll to map
            const mapContainer = document.getElementById('routeMap');
            if (mapContainer) {
                mapContainer.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        });
    });

    // ================================================================
    //  6.  KEYBOARD SHORTCUTS
    // ================================================================

    document.addEventListener('keydown', function(e) {
        // 'S' key - Toggle status
        if (e.key === 's' || e.key === 'S') {
            if (statusToggle) {
                statusToggle.checked = !statusToggle.checked;
                statusToggle.dispatchEvent(new Event('change'));
            }
        }

        // 'A' key - Accept delivery
        if (e.key === 'a' || e.key === 'A') {
            if (acceptDelivery && !notificationBanner.classList.contains('hidden')) {
                acceptDelivery.click();
            }
        }

        // 'D' key - Decline delivery
        if (e.key === 'd' || e.key === 'D') {
            if (declineDelivery && !notificationBanner.classList.contains('hidden')) {
                declineDelivery.click();
            }
        }

        // 'T' key - Start trip
        if (e.key === 't' || e.key === 'T') {
            const assignmentType = document.getElementById('assignmentType');
            if (assignmentType) {
                if (assignmentType.textContent === 'Ride-Pooling' && startTripBtn) {
                    startTripBtn.click();
                } else if (assignmentType.textContent === 'Delivery' && startDeliveryBtn) {
                    startDeliveryBtn.click();
                }
            }
        }
    });

    // ================================================================
    //  7.  TOOLTIP FOR SHORTCUTS (Console)
    // ================================================================

    console.log('⌨️ Keyboard Shortcuts:');
    console.log('  [S] Toggle Online/Offline');
    console.log('  [A] Accept Delivery');
    console.log('  [D] Decline Delivery');
    console.log('  [T] Start Trip/Delivery');

});