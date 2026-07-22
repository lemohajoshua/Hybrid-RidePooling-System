/**
 * auth.js - Authentication Pages JavaScript
 * Hybrid Ride-Pooling & Delivery System
 */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    // ================================================================
    //  1.  PASSWORD VISIBILITY TOGGLE
    // ================================================================

    const passwordToggles = document.querySelectorAll('.password-toggle');

    passwordToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            const wrapper = this.closest('.password-wrapper');
            const input = wrapper.querySelector('input');
            const icon = this.querySelector('i');

            if (input.type === 'password') {
                input.type = 'text';
                icon.className = 'fas fa-eye-slash';
            } else {
                input.type = 'password';
                icon.className = 'fas fa-eye';
            }
        });
    });

    // ================================================================
    //  2.  ROLE SELECTION (Login Page)
    // ================================================================

    const roleBtns = document.querySelectorAll('.role-btn');

    roleBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            roleBtns.forEach(function(b) {
                b.classList.remove('active');
            });
            this.classList.add('active');

            const role = this.dataset.role;
            const heading = document.querySelector('.auth-card h2');
            const subtitle = document.querySelector('.auth-subtitle');

            if (heading && subtitle) {
                const roleNames = {
                    'passenger': 'Passenger Login',
                    'driver': 'Driver Login',
                    'admin': 'Admin Login'
                };
                const roleSubs = {
                    'passenger': 'Book rides and save with pooling',
                    'driver': 'Accept rides and deliveries',
                    'admin': 'Monitor system performance'
                };
                heading.textContent = roleNames[role] || 'Welcome Back';
                subtitle.textContent = roleSubs[role] || 'Sign in to continue';

                // Update button text
                const submitBtn = document.querySelector('.auth-form .btn');
                if (submitBtn) {
                    const icons = {
                        'passenger': 'fa-user',
                        'driver': 'fa-car',
                        'admin': 'fa-user-tie'
                    };
                    submitBtn.innerHTML = `<i class="fas ${icons[role]}"></i> Sign In as ${role.charAt(0).toUpperCase() + role.slice(1)}`;
                }
            }
        });
    });

    // ================================================================
    //  3.  LOGIN FORM HANDLING
    // ================================================================

    const loginForm = document.getElementById('loginForm');

    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const rememberMe = document.getElementById('rememberMe')?.checked || false;

            // Basic validation
            if (!email || !password) {
                showNotification('Please fill in all fields.', 'error');
                return;
            }

            if (!isValidEmail(email)) {
                showNotification('Please enter a valid email address.', 'error');
                return;
            }

            // Simulate login
            const submitBtn = this.querySelector('.btn');
            const originalText = submitBtn.innerHTML;

            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing in...';
            submitBtn.disabled = true;

            setTimeout(function() {
                // Determine role from active button
                const activeRole = document.querySelector('.role-btn.active');
                const role = activeRole ? activeRole.dataset.role : 'passenger';

                // Redirect based on role
                const redirects = {
                    'passenger': '../passenger/index.html',
                    'driver': '../driver/index.html',
                    'admin': '../admin/index.html'
                };

                showNotification(`Welcome back, ${email}! Redirecting...`, 'success');

                setTimeout(function() {
                    window.location.href = redirects[role] || '../landing/index.html';
                }, 1000);

                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 1500);
        });
    }

    // ================================================================
    //  4.  PASSENGER REGISTRATION FORM HANDLING
    // ================================================================

    const registerForm = document.getElementById('registerForm');

    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const firstName = document.getElementById('firstName').value;
            const lastName = document.getElementById('lastName').value;
            const email = document.getElementById('email').value;
            const phone = document.getElementById('phone').value;
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const termsAccepted = document.getElementById('termsAccepted').checked;

            // Validation
            if (!firstName || !lastName || !email || !phone || !password) {
                showNotification('Please fill in all required fields.', 'error');
                return;
            }

            if (!isValidEmail(email)) {
                showNotification('Please enter a valid email address.', 'error');
                return;
            }

            if (password.length < 6) {
                showNotification('Password must be at least 6 characters.', 'error');
                return;
            }

            if (password !== confirmPassword) {
                showNotification('Passwords do not match.', 'error');
                return;
            }

            if (!termsAccepted) {
                showNotification('Please accept the Terms of Service.', 'error');
                return;
            }

            const submitBtn = this.querySelector('.btn');
            const originalText = submitBtn.innerHTML;

            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating account...';
            submitBtn.disabled = true;

            setTimeout(function() {
                showNotification('🎉 Account created successfully! Redirecting to login...', 'success');

                setTimeout(function() {
                    window.location.href = 'login.html';
                }, 1500);

                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 1500);
        });
    }

    // ================================================================
    //  5.  DRIVER REGISTRATION FORM HANDLING
    // ================================================================

    const driverRegisterForm = document.getElementById('driverRegisterForm');

    if (driverRegisterForm) {
        driverRegisterForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const firstName = document.getElementById('firstName').value;
            const lastName = document.getElementById('lastName').value;
            const email = document.getElementById('email').value;
            const phone = document.getElementById('phone').value;
            const vehicleType = document.getElementById('vehicleType').value;
            const plateNumber = document.getElementById('plateNumber').value;
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const termsAccepted = document.getElementById('termsAccepted').checked;

            // Validation
            if (!firstName || !lastName || !email || !phone || !vehicleType || !plateNumber || !password) {
                showNotification('Please fill in all required fields.', 'error');
                return;
            }

            if (!isValidEmail(email)) {
                showNotification('Please enter a valid email address.', 'error');
                return;
            }

            if (password.length < 6) {
                showNotification('Password must be at least 6 characters.', 'error');
                return;
            }

            if (password !== confirmPassword) {
                showNotification('Passwords do not match.', 'error');
                return;
            }

            if (!termsAccepted) {
                showNotification('Please accept the Terms of Service.', 'error');
                return;
            }

            const submitBtn = this.querySelector('.btn');
            const originalText = submitBtn.innerHTML;

            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
            submitBtn.disabled = true;

            setTimeout(function() {
                showNotification('🚗 Driver account created successfully! Redirecting to login...', 'success');

                setTimeout(function() {
                    window.location.href = 'login.html';
                }, 1500);

                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 1500);
        });
    }

    // ================================================================
    //  6.  UTILITY FUNCTIONS
    // ================================================================

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    function showNotification(message, type) {
        // Remove existing notifications
        const existing = document.querySelector('.auth-notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = `auth-notification ${type}`;
        notification.innerHTML = `
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        `;

        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '10px',
            background: type === 'success' ? '#2B8A3E' : '#C92A2A',
            color: '#FFFFFF',
            fontSize: '14px',
            fontWeight: '500',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            zIndex: '9999',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            maxWidth: '400px',
            animation: 'slideDown 0.3s ease',
            border: 'none'
        });

        document.body.appendChild(notification);

        // Auto remove after 4 seconds
        setTimeout(function() {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.3s ease';
            setTimeout(function() {
                notification.remove();
            }, 300);
        }, 4000);
    }

    // Add notification animation if not exists
    if (!document.getElementById('notificationStyles')) {
        const style = document.createElement('style');
        style.id = 'notificationStyles';
        style.textContent = `
            @keyframes slideDown {
                0% { opacity: 0; transform: translateY(-20px); }
                100% { opacity: 1; transform: translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }

});