/**
 * passenger.js - Passenger Page Specific JavaScript
 * Hybrid Ride-Pooling & Delivery System
 * Based on Figma Make (shadcn/ui) design system
 */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    console.log('🧑 Passenger Page loaded');

    // ================================================================
    //  1.  RIDE TOGGLE (Solo / Pooled)
    // ================================================================

    const soloToggle = document.getElementById('soloToggle');
    const poolToggle = document.getElementById('poolToggle');
    const rideInfo = document.getElementById('rideInfo');

    if (soloToggle && poolToggle) {
        soloToggle.addEventListener('click', function() {
            soloToggle.classList.add('active');
            poolToggle.classList.remove('active');
            rideInfo.innerHTML = `
                <i class="fas fa-info-circle"></i>
                Solo rides are private and direct. No sharing with other passengers.
            `;
            rideInfo.style.color = '#6C757D';
        });

        poolToggle.addEventListener('click', function() {
            poolToggle.classList.add('active');
            soloToggle.classList.remove('active');
            rideInfo.innerHTML = `
                <i class="fas fa-info-circle"></i>
                Pooled rides save up to 30% on fare and help reduce traffic congestion.
            `;
            rideInfo.style.color = '#2B8A3E';
        });
    }

    // ================================================================
    //  2.  FIND RIDE BUTTON
    // ================================================================

    const findRideBtn = document.getElementById('findRideBtn');
    const matchResults = document.getElementById('matchResults');
    const closeMatchBtn = document.getElementById('closeMatch');

    if (findRideBtn && matchResults) {
        findRideBtn.addEventListener('click', function() {
            const pickup = document.getElementById('pickup').value || 'FUTO Gate';
            const destination = document.getElementById('destination').value || 'World Bank';
            const isPooled = poolToggle.classList.contains('active');

            // Show loading state
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Searching...';
            this.disabled = true;

            // Simulate API call / search delay
            setTimeout(() => {
                // Restore button
                this.innerHTML = '<i class="fas fa-search"></i> Find My Ride';
                this.disabled = false;

                // Show match results
                matchResults.style.display = 'block';

                // Update match content based on selection
                if (isPooled) {
                    document.querySelector('.match-badge').innerHTML =
                        '<i class="fas fa-check-circle"></i> We found a match!';
                    document.querySelector('.savings-value').textContent = '₦540';
                    document.querySelector('.savings-percent').textContent = '(30%)';
                    document.querySelector('.savings-detail').innerHTML = `
                        <span>Solo fare: ₦1,800</span>
                        <span>Pooled fare: ₦1,260</span>
                    `;
                    document.querySelector('.match-arrow span').textContent = 'Pooling';
                } else {
                    document.querySelector('.match-badge').innerHTML =
                        '<i class="fas fa-info-circle"></i> Solo ride confirmed';
                    document.querySelector('.savings-value').textContent = '₦0';
                    document.querySelector('.savings-percent').textContent = '(0%)';
                    document.querySelector('.savings-detail').innerHTML = `
                        <span>Solo fare: ₦1,800</span>
                        <span>No savings</span>
                    `;
                    document.querySelector('.match-arrow span').textContent = 'Solo';
                }

                // Scroll to match results
                matchResults.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });

            }, 1500);
        });
    }

    // ================================================================
    //  3.  CLOSE MATCH RESULTS
    // ================================================================

    if (closeMatchBtn && matchResults) {
        closeMatchBtn.addEventListener('click', function() {
            matchResults.style.display = 'none';
        });
    }

    // ================================================================
    //  4.  CONFIRM RIDE BUTTON
    // ================================================================

    const confirmBtn = document.querySelector('.match-actions .btn-success');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            // Show confirmation
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check-circle"></i> Confirmed!';
            this.style.background = '#2B8A3E';
            this.disabled = true;

            // Add to recent rides
            addRecentRide();

            // Close match after 2 seconds
            setTimeout(() => {
                matchResults.style.display = 'none';
                this.innerHTML = originalText;
                this.disabled = false;
                this.style.background = '';
            }, 2000);
        });
    }

    // ================================================================
    //  5.  ADD RECENT RIDE (Simulated)
    // ================================================================

    function addRecentRide() {
        const historyContainer = document.querySelector('.ride-history');

        // Get current pickup and destination
        const pickup = document.getElementById('pickup').value || 'FUTO Gate';
        const destination = document.getElementById('destination').value || 'World Bank';
        const isPooled = poolToggle.classList.contains('active');

        // Create new history item
        const newItem = document.createElement('div');
        newItem.className = 'history-item';
        newItem.style.animation = 'slideDown 0.4s ease';

        const icon = isPooled ? 'fa-users' : 'fa-car';
        const badge = isPooled ? '<span class="badge badge-primary">Pooled</span>' : '';

        const now = new Date();
        const dateStr = now.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
        const timeStr = now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

        const cost = isPooled ? '₦1,260' : '₦1,800';

        newItem.innerHTML = `
            <div class="history-icon">
                <i class="fas ${icon}"></i>
            </div>
            <div class="history-details">
                <div class="history-route">${pickup} → ${destination}</div>
                <div class="history-meta">
                    <span><i class="far fa-calendar"></i> ${dateStr}</span>
                    <span><i class="far fa-clock"></i> ${timeStr}</span>
                    <span class="badge badge-success">Completed</span>
                    ${badge}
                </div>
            </div>
            <div class="history-cost">${cost}</div>
        `;

        // Insert at the top
        historyContainer.insertBefore(newItem, historyContainer.firstChild);

        // Update badge count
        const badgeCount = document.querySelector('.recent-rides .badge');
        if (badgeCount) {
            const count = parseInt(badgeCount.textContent) + 1;
            badgeCount.textContent = count + ' trips';
        }
    }

    // ================================================================
    //  6.  KEYBOARD SHORTCUT: ENTER TO FIND RIDE
    // ================================================================

    const inputs = document.querySelectorAll('.ride-request-card input');
    inputs.forEach(function(input) {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (findRideBtn) {
                    findRideBtn.click();
                }
            }
        });
    });

});