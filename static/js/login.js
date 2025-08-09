
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
        function validateEmail(email) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        }

        function validatePassword(password) {
            return password.length >= 6; 
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

        // Password visibility toggle
        function initPasswordToggle() {
            const passwordInput = document.getElementById('id_password');
            const passwordToggle = document.getElementById('passwordToggle');

            passwordToggle.addEventListener('click', function() {
                const isPassword = passwordInput.type === 'password';
                passwordInput.type = isPassword ? 'text' : 'password';
                this.textContent = isPassword ? '🙈' : '👁️';
            });
        }

        
       function initFormSubmission() {
    const form = document.getElementById('loginForm');
    const submitBtn = document.getElementById('submitBtn');
    const loading = document.getElementById('loading');

    form.addEventListener('submit', function(e) {
        // Stop the form until we validate
        e.preventDefault();

        // Clear previous messages
        document.getElementById('messages').innerHTML = '';

        // Validate all fields
        let isValid = true;
        const formData = new FormData(this);

        // Email validation
        const email = formData.get('email');
        if (!validateEmail(email)) {
            showError('email', 'Please enter a valid email address');
            isValid = false;
        } else {
            showSuccess('email');
        }

        // Password validation
        const password = formData.get('password');
        if (!password || password.trim() === '') {
            showError('password', 'Please enter your password');
            isValid = false;
        } else {
            showSuccess('password');
        }

        if (!isValid) {
            showMessage('Please fix the errors above and try again.', 'error');
            return; // Stop here if validation fails
        }

        // Show loading state
        submitBtn.disabled = true;
        loading.style.display = 'inline-block';
        submitBtn.textContent = 'Signing In...';

    
        this.submit();
    });
}


        // Google Sign In
        function initGoogleSignIn() {
            const googleBtn = document.getElementById('googleSignIn');
            
            googleBtn.addEventListener('click', function() {
                // Add loading state
                this.innerHTML = '<div class="google-icon"></div>Connecting to Google...';
                this.disabled = true;
                
                
                
                // For demonstration purposes
                setTimeout(() => {
                    this.innerHTML = '<div class="google-icon"></div>Continue with Google';
                    this.disabled = false;
                    showMessage('Google Sign-In integration ready for Django setup', 'success');
                }, 1500);
                
                console.log('Google OAuth integration needed for Django');
            });
        }

        
        // Handle Enter key in form fields
        function initKeyboardHandlers() {
            const formInputs = document.querySelectorAll('.form-input');
            
            formInputs.forEach(input => {
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        document.getElementById('loginForm').dispatchEvent(new Event('submit'));
                    }
                });
            });
        }

        // Initialize everything when DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {
            createParticles();
            initPasswordToggle();
            initFormValidation();
            initFormSubmission();
            initGoogleSignIn();
            initKeyboardHandlers();
           
            
            // Animate page load
            document.body.style.opacity = '0';
            setTimeout(() => {
                document.body.style.transition = 'opacity 0.5s ease';
                document.body.style.opacity = '1';
            }, 100);

            // Focus first input after animations
            setTimeout(() => {
                document.getElementById('id_email').focus();
            }, 1000);
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

        // Clear form errors on input
        function clearErrorOnInput() {
            const inputs = document.querySelectorAll('.form-input');
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    if (this.classList.contains('error')) {
                        const fieldName = this.name;
                        const errorDiv = document.getElementById(`${fieldName}_error`);
                        if (errorDiv) {
                            errorDiv.classList.remove('show');
                            this.classList.remove('error');
                        }
                    }
                });
            });
        }


        // Initialize error clearing
        document.addEventListener('DOMContentLoaded', function() {
            clearErrorOnInput();
        });