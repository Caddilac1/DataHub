// register.js

// Run the function after the DOM loads
document.addEventListener('DOMContentLoaded', function () {
    // Floating Particles
    function createParticles() {
        const particlesContainer = document.getElementById('particles');
        if (!particlesContainer) return;
        for (let i = 0; i < 8; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + 'vw';
            particle.style.width = Math.random() * 8 + 4 + 'px';
            particle.style.height = particle.style.width;
            particle.style.animationDelay = Math.random() * 15 + 's';
            particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
            particlesContainer.appendChild(particle);
        }
    }

    // --- Form validation functions ---
    function validateFullName(name) {
        return name.trim().length >= 2 && /^[a-zA-Z\s]+$/.test(name.trim());
    }

    function validatePhoneNumber(phone) {
        const ghanaPhoneRegex = /^0[2-9]\d{8}$/;
        return ghanaPhoneRegex.test(phone.replace(/\s/g, ''));
    }

    function validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    function checkPasswordStrength(password) {
        let strength = 0;
        let feedback = '';

        if (password.length >= 8) strength += 1;
        if (/[a-z]/.test(password)) strength += 1;
        if (/[A-Z]/.test(password)) strength += 1;
        if (/\d/.test(password)) strength += 1;
        if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) strength += 1;

        const strengthBar = document.getElementById('strengthBar');
        const strengthText = document.getElementById('strengthText');

        if (strengthBar && strengthText) {
            switch (strength) {
                case 0:
                case 1:
                    strengthBar.className = 'password-strength-bar strength-weak';
                    feedback = 'Weak password';
                    strengthText.style.color = '#e74c3c';
                    break;
                case 2:
                    strengthBar.className = 'password-strength-bar strength-fair';
                    feedback = 'Fair password';
                    strengthText.style.color = '#f39c12';
                    break;
                case 3:
                case 4:
                    strengthBar.className = 'password-strength-bar strength-good';
                    feedback = 'Good password';
                    strengthText.style.color = '#3498db';
                    break;
                case 5:
                    strengthBar.className = 'password-strength-bar strength-strong';
                    feedback = 'Strong password';
                    strengthText.style.color = '#27ae60';
                    break;
                default:
                    strengthBar.className = 'password-strength-bar';
                    feedback = '';
                    strengthText.style.color = 'inherit';
            }
            strengthText.textContent = feedback;
        }

        return strength >= 3; // Require at least "good" strength
    }

    // --- DOM manipulation for errors and success ---
    function showError(fieldId, message) {
        const field = document.getElementById(`id_${fieldId}`);
        const errorDiv = field ? field.nextElementSibling : null; // Get the next sibling for the error message
        
        if (field) {
            field.classList.add('error');
            field.classList.remove('valid');
            field.style.animation = 'shake 0.5s ease-in-out';
            setTimeout(() => { field.style.animation = ''; }, 500);
        }
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.add('show');
        }
    }

    function showSuccess(fieldId) {
        const field = document.getElementById(`id_${fieldId}`);
        const errorDiv = field ? field.nextElementSibling : null;
        
        if (field) {
            field.classList.remove('error');
            field.classList.add('valid');
        }
        if (errorDiv) {
            errorDiv.classList.remove('show');
            errorDiv.textContent = '';
        }
    }
    
    function clearErrors() {
        // Find and clear all error messages
        document.querySelectorAll('.error-message').forEach(el => {
            el.textContent = '';
            el.classList.remove('show');
        });
        document.querySelectorAll('.form-input.error, .form-input.valid').forEach(el => {
            el.classList.remove('error', 'valid');
        });
    }

    // --- Real-time validation event listeners ---
    function initFormValidation() {
        const form = document.getElementById('registrationForm');
        if (!form) return;
        
        const fields = ['full_name', 'phone_number', 'email', 'password1', 'password2'];
        fields.forEach(fieldId => {
            const input = document.getElementById(`id_${fieldId}`);
            if (input) {
                input.addEventListener('input', () => {
                    // Clear previous state on new input
                    showSuccess(fieldId);
                });
                
                input.addEventListener('blur', () => {
                    // Trigger validation on blur
                    switch (fieldId) {
                        case 'full_name':
                            if (!validateFullName(input.value)) {
                                showError(fieldId, 'Please enter a valid full name (letters only)');
                            }
                            break;
                        case 'phone_number':
                            if (!validatePhoneNumber(input.value)) {
                                showError(fieldId, 'Please enter a valid Ghana phone number (e.g., 0244123456)');
                            }
                            break;
                        case 'email':
                            if (!validateEmail(input.value)) {
                                showError(fieldId, 'Please enter a valid email address');
                            }
                            break;
                        case 'password1':
                            if (input.value.length < 8) {
                                showError(fieldId, 'Password must be at least 8 characters long');
                            } else if (!checkPasswordStrength(input.value)) {
                                showError(fieldId, 'Please choose a stronger password');
                            }
                            break;
                        case 'password2':
                            const password1Input = document.getElementById('id_password1');
                            if (input.value !== password1Input.value) {
                                showError(fieldId, 'Passwords do not match');
                            }
                            break;
                    }
                });
            }
        });
        
        // Add password strength check on input
        const password1Input = document.getElementById('id_password1');
        if (password1Input) {
            password1Input.addEventListener('input', function() {
                if (this.value.length > 0) {
                    checkPasswordStrength(this.value);
                } else {
                    document.getElementById('strengthBar').className = 'password-strength-bar';
                    document.getElementById('strengthText').textContent = '';
                }
            });
        }
    }
    
    // --- Form submission handler ---
    // The previous initFormSubmission is removed as Django's form handles it.
    // We can add a function here to handle the loading state
    const form = document.getElementById('registrationForm');
    if (form) {
        form.addEventListener('submit', function () {
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            
            submitBtn.disabled = true;
            loading.style.display = 'inline-block';
            submitBtn.textContent = 'Creating Account...';
        });
    }

    // --- Other initialization ---
    createParticles();
    initFormValidation();
    
    // Animate page load
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);

    // Handle window resize for particles
    window.addEventListener('resize', function () {
        const particlesContainer = document.getElementById('particles');
        if (particlesContainer) {
            particlesContainer.innerHTML = '';
            createParticles();
        }
    });

    // Performance optimization: Pause animations when page is not visible
    document.addEventListener('visibilitychange', function () {
        const particles = document.querySelectorAll('.particle');
        particles.forEach(particle => {
            particle.style.animationPlayState = document.hidden ? 'paused' : 'running';
        });
    });

    // Google Sign-Up handler
    function initGoogleSignUp() {
        const googleBtn = document.getElementById('googleSignUp');
        if (!googleBtn) return;
        
        googleBtn.addEventListener('click', function() {
            this.innerHTML = '<div class="google-icon"></div>Connecting to Google...';
            this.disabled = true;
            
            // In a real Django app, this would redirect to the OAuth URL
            // window.location.href = '/accounts/google/login/';
        });
    }
    initGoogleSignUp();
});