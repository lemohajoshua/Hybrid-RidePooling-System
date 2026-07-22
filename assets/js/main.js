/**
 * main.js - Global Shared JavaScript
 * Hybrid Ride-Pooling & Delivery System
 */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    // ================================================================
    //  1.  HAMBURGER MENU TOGGLE
    // ================================================================

    const hamburger = document.getElementById('hamburger');
    if (hamburger) {
        hamburger.addEventListener('click', function() {
            const navLinks = document.querySelector('.nav-links');
            if (navLinks) {
                navLinks.classList.toggle('open');
            }
        });
    }

    // ================================================================
    //  2.  CLOSE MOBILE MENU ON LINK CLICK
    // ================================================================

    document.querySelectorAll('.nav-links a').forEach(function(link) {
        link.addEventListener('click', function() {
            const mobileMenu = document.querySelector('.nav-links');
            if (mobileMenu && window.innerWidth <= 768) {
                mobileMenu.classList.remove('open');
            }
        });
    });

    // ================================================================
    //  3.  ACTIVE NAV LINK HIGHLIGHT
    // ================================================================

    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(function(link) {
        const href = link.getAttribute('href');
        if (href && href.includes(currentPage)) {
            link.classList.add('active');
        }
    });

});