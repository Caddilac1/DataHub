
        // Create floating particles
        function createParticles() {
            const particlesContainer = document.getElementById('particles');
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

        // Form validation functions
        function validateFullName(name) {
            return name.trim().length >= 2 && /^[a-zA-Z\s]+$/.test(name.trim());
        }

        function validatePhoneNumber(phone) {
            // Ghana phone number: must be 10 digits starting with 0
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
            }
            
            strengthText.textContent = feedback;
            return strength >= 3; // Require at least "good" strength
        }

        function showError(fieldId, message) {
            const field = document.getElementById(`id_${fieldId}`);
            const errorDiv = document.getElementById(`${fieldId}_error`);
            
            field.classList.add('error');
            field.classList.remove('valid');
            errorDiv.textContent = message;
            errorDiv.classList.add('show');
            
            // Shake animation
            field.style.animation = 'shake 0.5s ease-in-out';
            setTimeout(() => {
                field.style.animation = '';
            }, 500);
        }

        function showSuccess(fieldId) {
            const field = document.getElementById(`id_${fieldId}`);
            const errorDiv = document.getElementById(`${fieldId}_error`);
            
            field.classList.remove('error');
            field.classList.add('valid');
            errorDiv.classList.remove('show');
        }

        function showMessage(message, type = 'error') {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            messageDiv.textContent = message;
            
            messagesDiv.innerHTML = '';
            messagesDiv.appendChild(messageDiv);
            
            // Auto remove success messages
            if (type === 'success') {
                setTimeout(() => {
                    messageDiv.style.opacity = '0';
                    setTimeout(() => messageDiv.remove(), 300);
                }, 5000);
            }
        }

        // Real-time validation
        function initFormValidation() {
            const fullNameInput = document.getElementById('id_full_name');
            const phoneInput = document.getElementById('id_phone_number');
            const emailInput = document.getElementById('id_email');
            const password1Input = document.getElementById('id_password1');
            const password2Input = document.getElementById('id_password2');

            // Full name validation
            fullNameInput.addEventListener('blur', function() {
                if (this.value.trim()) {
                    if (validateFullName(this.value)) {
                        showSuccess('full_name');
                    } else {
                        showError('full_name', 'Please enter a valid full name (letters only)');
                    }
                }
            });

            // Phone number validation and formatting
            phoneInput.addEventListener('input', function() {
                // Remove all non-digits
                let value = this.value.replace(/\D/g, '');
                
                // Ensure it starts with 0
                if (value.length > 0 && !value.startsWith('0')) {
                    value = '0' + value.slice(0, 9);
                }
                
                // Limit to 10 digits
                if (value.length > 10) {
                    value = value.slice(0, 10);
                }
                
                this.value = value;
            });

            phoneInput.addEventListener('blur', function() {
                if (this.value) {
                    if (validatePhoneNumber(this.value)) {
                        showSuccess('phone_number');
                    } else {
                        showError('phone_number', 'Please enter a valid Ghana phone number (e.g., 0244123456)');
                    }
                }
            });

            // Email validation
            emailInput.addEventListener('blur', function() {
                if (this.value.trim()) {
                    if (validateEmail(this.value)) {
                        showSuccess('email');
                    } else {
                        showError('email', 'Please enter a valid email address');
                    }
                }
            });

            // Password strength checking
            password1Input.addEventListener('input', function() {
                if (this.value.length > 0) {
                    checkPasswordStrength(this.value);
                } else {
                    document.getElementById('strengthBar').className = 'password-strength-bar';
                    document.getElementById('strengthText').textContent = '';
                }
            });

            password1Input.addEventListener('blur', function() {
                if (this.value.trim()) {
                    if (this.value.length < 8) {
                        showError('password1', 'Password must be at least 8 characters long');
                    } else if (!checkPasswordStrength(this.value)) {
                        showError('password1', 'Please choose a stronger password');
                    } else {
                        showSuccess('password1');
                    }
                }
            });

            // Confirm password validation
            password2Input.addEventListener('blur', function() {
                if (this.value.trim()) {
                    if (this.value !== password1Input.value) {
                        showError('password2', 'Passwords do not match');
                    } else if (password1Input.value.trim()) {
                        showSuccess('password2');
                    }
                }
            });
        }

// Initialize form submission
function initFormSubmission() {
    const form = document.getElementById('registrationForm');
    const submitBtn = document.getElementById('submitBtn');
    const loading = document.getElementById('loading');

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        let isValid = true;
        const formData = new FormData(this);

        // Full name validation
        const fullName = formData.get('full_name');
        if (!validateFullName(fullName)) {
            showError('full_name', 'Please enter a valid full name');
            isValid = false;
        }

        // Phone number validation
        const phone = formData.get('phone_number');
        if (!validatePhoneNumber(phone)) {
            showError('phone_number', 'Please enter a valid Ghana phone number');
            isValid = false;
        }

        // Email validation
        const email = formData.get('email');
        if (!validateEmail(email)) {
            showError('email', 'Please enter a valid email address');
            isValid = false;
        }

        // Password validation
        const password1 = formData.get('password1');
        const password2 = formData.get('password2');

        if (password1.length < 8) {
            showError('password1', 'Password must be at least 8 characters long');
            isValid = false;
        } else if (!checkPasswordStrength(password1)) {
            showError('password1', 'Please choose a stronger password');
            isValid = false;
        }

        if (password1 !== password2) {
            showError('password2', 'Passwords do not match');
            isValid = false;
        }

        if (!isValid) {
            showMessage('Please fix the errors above and try again.', 'error');
            return;
        }

        // Show loading state
        submitBtn.disabled = true;
        loading.style.display = 'inline-block';
        submitBtn.textContent = 'Creating Account...';

        // Submit the form to Django
        setTimeout(() => {
            // Remove loading
            loading.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create Account';

            // Submit to Django backend
            form.submit();
        }, 500); // short delay for loading animation
    });
}

// Run the function after DOM loads
document.addEventListener('DOMContentLoaded', initFormSubmission);

        // Google Sign Up
        function initGoogleSignUp() {
            const googleBtn = document.getElementById('googleSignUp');
            
            googleBtn.addEventListener('click', function() {
                // Add loading state
                this.innerHTML = '<div class="google-icon"></div>Connecting to Google...';
                this.disabled = true;
                
                // In a real Django app with django-allauth or similar:
                // window.location.href = '/accounts/google/login/';
                
                // For demonstration purposes
                setTimeout(() => {
                    this.innerHTML = '<div class="google-icon"></div>Sign up with Google';
                    this.disabled = false;
                    showMessage('Google Sign-Up integration ready for Django setup', 'success');
                }, 1500);
                
                console.log('Google OAuth integration needed for Django');
            });
        }

       

        // Initialize everything when DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {
            createParticles();
            initFormValidation();
            initFormSubmission();
            initGoogleSignUp();
            addDemoData(); // Remove this in production
            
            // Animate page load
            document.body.style.opacity = '0';
            setTimeout(() => {
                document.body.style.transition = 'opacity 0.5s ease';
                document.body.style.opacity = '1';
            }, 100);
        });

        // Handle window resize for particles
        window.addEventListener('resize', function() {
            // Recreate particles on resize
            const particlesContainer = document.getElementById('particles');
            particlesContainer.innerHTML = '';
            createParticles();
        });

        // Performance optimization: Pause animations when page is not visible
        document.addEventListener('visibilitychange', function() {
            const particles = document.querySelectorAll('.particle');
            particles.forEach(particle => {
                if (document.hidden) {
                    particle.style.animationPlayState = 'paused';
                } else {
                    particle.style.animationPlayState = 'running';
                }
            });
        });

        // Django integration helper functions
        function getDjangoCSRFToken() {
            // In your Django template, you would get this from {% csrf_token %}
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        }

        function handleDjangoFormErrors(errors) {
            // Handle Django form errors returned from the server
            for (const [field, messages] of Object.entries(errors)) {
                if (messages && messages.length > 0) {
                    showError(field, messages[0]);
                }
            }
        }

        // Export functions for Django integration
        window.DataHubAuth = {
            validateFullName,
            validatePhoneNumber,
            validateEmail,
            checkPasswordStrength,
            showError,
            showSuccess,
            showMessage,
            handleDjangoFormErrors,
            getDjangoCSRFToken
        };
