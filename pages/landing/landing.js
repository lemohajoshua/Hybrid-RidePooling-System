/**
 * landing.js - Landing Page Specific JavaScript
 * Hybrid Ride-Pooling & Delivery System
 */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    console.log('🏠 RidePool+ Landing Page loaded');

    // ================================================================
    //  1.  SMOOTH SCROLL FOR "LEARN MORE" BUTTON
    // ================================================================

    const learnMoreBtn = document.querySelector('.hero-buttons .btn-outline-light');
    if (learnMoreBtn) {
        learnMoreBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector('#features');
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    }

    // ================================================================
    //  2.  STATISTICS COUNTER ANIMATION
    // ================================================================

    const statNumbers = document.querySelectorAll('.stat-number, .hero-stat-number');

    if ('IntersectionObserver' in window && statNumbers.length > 0) {
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const originalText = el.textContent;
                    const isPercentage = originalText.includes('%');
                    const isCurrency = originalText.includes('₦');
                    const numValue = parseFloat(originalText.replace(/[₦,%.]/g, ''));

                    if (!isNaN(numValue)) {
                        el.style.opacity = '1';
                        el.style.transform = 'translateY(0)';
                    }
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.3 });

        statNumbers.forEach(function(el) {
            el.style.opacity = '0';
            el.style.transform = 'translateY(12px)';
            el.style.transition = 'all 0.7s ease';
            observer.observe(el);
        });
    }

    // ================================================================
    //  3.  FEATURE CARD INTERACTIONS
    // ================================================================

    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            const icon = this.querySelector('.feature-icon');
            if (icon) {
                icon.style.transform = 'scale(1.1)';
                icon.style.transition = 'transform 0.3s ease';
            }
        });
        card.addEventListener('mouseleave', function() {
            const icon = this.querySelector('.feature-icon');
            if (icon) {
                icon.style.transform = 'scale(1)';
            }
        });
    });

});