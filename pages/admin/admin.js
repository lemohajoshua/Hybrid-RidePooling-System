/**
 * admin.js - Admin Dashboard Specific JavaScript
 * Hybrid Ride-Pooling & Delivery System
 * Based on Figma Make (shadcn/ui) design system
 */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    console.log('👤 Admin Dashboard loaded');

    // ================================================================
    //  1.  SIDEBAR TOGGLE (Mobile)
    // ================================================================

    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        }
    });

    // ================================================================
    //  2.  SIDEBAR NAVIGATION
    // ================================================================

    const navLinks = document.querySelectorAll('.sidebar-nav a');
    const sections = document.querySelectorAll('.metrics-grid, .charts-grid, .activity-section, .alerts-section');

    navLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            // Remove active from all links
            navLinks.forEach(function(l) {
                l.classList.remove('active');
            });

            // Add active to clicked link
            this.classList.add('active');

            // Close sidebar on mobile
            if (window.innerWidth <= 768 && sidebar) {
                sidebar.classList.remove('open');
            }

            // Scroll to section (simulated)
            const section = this.dataset.section;
            if (section) {
                // Simple scroll to top for overview
                if (section === 'overview') {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
                // Other sections just show a log for now
                console.log('📊 Navigating to:', section);
            }
        });
    });

    // ================================================================
    //  3.  DATE FILTER BUTTONS
    // ================================================================

    const filterBtns = document.querySelectorAll('.date-filter .filter-btn, .activity-filters .filter-btn');

    filterBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            // Remove active from siblings
            const parent = this.closest('.date-filter, .activity-filters');
            if (parent) {
                parent.querySelectorAll('.filter-btn').forEach(function(b) {
                    b.classList.remove('active');
                });
            }
            this.classList.add('active');

            // Simulate data update
            const filterText = this.textContent.trim();
            console.log('🔍 Filter applied:', filterText);
        });
    });

    // ================================================================
    //  4.  CHART BAR ANIMATIONS (On scroll)
    // ================================================================

    function animateBars() {
        const bars = document.querySelectorAll('.bar, .bar-fill, .area-bar');

        bars.forEach(function(bar) {
            const rect = bar.getBoundingClientRect();
            const isVisible = rect.top < window.innerHeight && rect.bottom > 0;

            if (isVisible) {
                const targetHeight = bar.style.height || bar.style.width;
                if (targetHeight) {
                    // Store original height
                    const originalHeight = targetHeight;
                    bar.style.height = '0%';
                    bar.style.width = '0%';

                    setTimeout(function() {
                        bar.style.height = originalHeight;
                        bar.style.width = originalHeight;
                        bar.style.transition = 'all 0.8s ease';
                    }, 100);
                }
            }
        });
    }

    // Run animation on load and scroll
    setTimeout(animateBars, 500);
    window.addEventListener('scroll', function() {
        // Throttle scroll events
        if (!window._scrollTimeout) {
            window._scrollTimeout = setTimeout(function() {
                animateBars();
                window._scrollTimeout = null;
            }, 200);
        }
    });

    // ================================================================
    //  5.  METRIC CARDS HOVER EFFECT
    // ================================================================

    const metricCards = document.querySelectorAll('.metric-card');
    metricCards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            const icon = this.querySelector('.metric-icon');
            if (icon) {
                icon.style.transform = 'scale(1.05)';
                icon.style.transition = 'transform 0.3s ease';
            }
        });
        card.addEventListener('mouseleave', function() {
            const icon = this.querySelector('.metric-icon');
            if (icon) {
                icon.style.transform = 'scale(1)';
            }
        });
    });

    // ================================================================
    //  6.  ACTIVITY TABLE ROW HOVER
    // ================================================================

    const tableRows = document.querySelectorAll('.activity-table tbody tr');
    tableRows.forEach(function(row) {
        row.addEventListener('click', function() {
            // Highlight clicked row
            tableRows.forEach(function(r) {
                r.style.background = '';
            });
            this.style.background = '#F0EDF5';

            // Log the row data
            const cells = this.querySelectorAll('td');
            if (cells.length >= 4) {
                console.log('📋 Activity clicked:', {
                    time: cells[0].textContent.trim(),
                    type: cells[1].textContent.trim(),
                    driver: cells[2].textContent.trim(),
                    route: cells[3].textContent.trim(),
                    status: cells[4].textContent.trim()
                });
            }
        });
    });

    // ================================================================
    //  7.  ALERT ITEM INTERACTIONS
    // ================================================================

    const alertItems = document.querySelectorAll('.alert-item');
    alertItems.forEach(function(item) {
        item.addEventListener('click', function() {
            // Toggle highlight
            this.style.background = this.style.background === '#F0EDF5' ? '#F8F9FA' : '#F0EDF5';
            console.log('🔔 Alert clicked:', this.querySelector('.alert-content p')?.textContent);
        });

        item.addEventListener('mouseenter', function() {
            this.style.cursor = 'pointer';
        });
    });

    // ================================================================
    //  8.  EXPORT BUTTON
    // ================================================================

    const exportBtn = document.querySelector('.header-right .btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
            this.disabled = true;

            setTimeout(function() {
                // Simulate export completion
                alert('📊 Report exported successfully!');
                exportBtn.innerHTML = '<i class="fas fa-download"></i> Export';
                exportBtn.disabled = false;
            }, 1500);
        });
    }

    // ================================================================
    //  9.  KEYBOARD SHORTCUTS (Admin)
    // ================================================================

    document.addEventListener('keydown', function(e) {
        // '1' - Overview
        if (e.key === '1') {
            const overviewLink = document.querySelector('.sidebar-nav a[data-section="overview"]');
            if (overviewLink) overviewLink.click();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        // '2' - Drivers
        if (e.key === '2') {
            const driversLink = document.querySelector('.sidebar-nav a[data-section="drivers"]');
            if (driversLink) driversLink.click();
            // Scroll to activity section
            const activitySection = document.querySelector('.activity-section');
            if (activitySection) activitySection.scrollIntoView({ behavior: 'smooth' });
        }

        // '3' - Analytics
        if (e.key === '3') {
            const analyticsLink = document.querySelector('.sidebar-nav a[data-section="analytics"]');
            if (analyticsLink) analyticsLink.click();
            const chartsSection = document.querySelector('.charts-grid');
            if (chartsSection) chartsSection.scrollIntoView({ behavior: 'smooth' });
        }

        // 'E' - Export
        if (e.key === 'e' || e.key === 'E') {
            if (exportBtn && !exportBtn.disabled) {
                exportBtn.click();
            }
        }
    });

    // Show keyboard shortcuts in console
    console.log('⌨️ Admin Keyboard Shortcuts:');
    console.log('  [1] Go to Overview');
    console.log('  [2] Go to Drivers/Activity');
    console.log('  [3] Go to Analytics/Charts');
    console.log('  [E] Export Report');

    // ================================================================
    //  10.  SIMULATED REAL-TIME UPDATES
    // ================================================================

    // Simulate a new alert appearing after 30 seconds
    setTimeout(function() {
        const alertsList = document.querySelector('.alerts-list');
        if (alertsList) {
            const newAlert = document.createElement('div');
            newAlert.className = 'alert-item';
            newAlert.style.animation = 'slideDown 0.4s ease';
            newAlert.innerHTML = `
                <div class="alert-icon info">
                    <i class="fas fa-info-circle"></i>
                </div>
                <div class="alert-content">
                    <p><strong>New passenger request</strong> in Ihiagwa rural zone</p>
                    <span class="alert-time">Just now</span>
                </div>
            `;
            alertsList.prepend(newAlert);

            // Update badge count
            const alertBadge = document.querySelector('.alerts-header .badge');
            if (alertBadge) {
                const currentCount = parseInt(alertBadge.textContent) || 0;
                alertBadge.textContent = (currentCount + 1) + ' New';
            }

            console.log('🔔 New alert added: Passenger request in Ihiagwa');
        }
    }, 30000);

    console.log('📊 Admin Dashboard fully loaded. Monitoring system performance...');

});