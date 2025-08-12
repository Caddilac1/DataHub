// Global variables
let selectedNetwork = '';
let selectedPlan = null;

// Stock status simulation (remains a JS-based mock for now)
const stockStatuses = {
    'MTN': 'in-stock',
    'AirtelTigo': 'limited',
    'Telecel': 'out-of-stock'
};

// Create floating particles
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    for (let i = 0; i < 6; i++) {
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

// Animate counting numbers
function animateCountUp(element, target, duration = 2000) {
    const start = 0;
    const startTime = performance.now();
    const isDecimal = target.toString().includes('.');
    
    function updateCount(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = start + (target - start) * easeOutExpo(progress);
        
        if (isDecimal) {
            element.textContent = current.toFixed(1);
        } else {
            element.textContent = Math.floor(current);
        }
        
        if (progress < 1) {
            requestAnimationFrame(updateCount);
        }
    }
    
    requestAnimationFrame(updateCount);
}

function easeOutExpo(t) {
    return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

// Dynamic greeting based on time
function setGreeting() {
    const now = new Date();
    const hour = now.getHours();
    const greetingEl = document.getElementById('greeting');
    // Get user full name from the template, falling back to 'Guest' if not provided
    const userFullName = greetingEl.dataset.user || "Guest";
    
    let greeting;
    if (hour < 12) {
        greeting = `Good Morning, ${userFullName}! Welcome to DataHub 🌅`;
    } else if (hour < 17) {
        greeting = `Good Afternoon, ${userFullName}! Welcome to DataHub ☀️`;
    } else {
        greeting = `Good Evening, ${userFullName}! Welcome to DataHub 🌙`;
    }

    greetingEl.textContent = greeting;
}

// Update stock status dynamically
function updateStockStatus(network, status) {
    const card = document.querySelector(`.network-card[data-network="${network.toLowerCase()}"]`);
    if (!card) return;

    const statusBadge = card.querySelector('.stock-status');
    const buyBtn = card.querySelector('.buy-btn');

    // Remove existing classes
    card.classList.remove('out-of-stock', 'limited-stock');
    statusBadge.classList.remove('stock-in', 'stock-out', 'stock-limited');

    switch(status) {
        case 'out-of-stock':
            card.classList.add('out-of-stock');
            statusBadge.classList.add('stock-out');
            statusBadge.textContent = 'OUT OF STOCK';
            buyBtn.disabled = true;
            buyBtn.textContent = 'Currently Unavailable';
            break;
        case 'limited':
            card.classList.add('limited-stock');
            statusBadge.classList.add('stock-limited');
            statusBadge.textContent = 'LIMITED';
            buyBtn.disabled = false;
            buyBtn.textContent = 'Buy Data Bundle';
            break;
        default:
            statusBadge.classList.add('stock-in');
            statusBadge.textContent = 'IN STOCK';
            buyBtn.disabled = false;
            buyBtn.textContent = 'Buy Data Bundle';
    }
}

// Tab navigation with enhanced animations
function initNavigation() {
    // Handle navbar navigation
    document.querySelectorAll('[data-nav]').forEach(navItem => {
        navItem.addEventListener('click', function(e) {
            e.preventDefault();
            const tabId = this.dataset.nav;
            switchToTab(tabId);
            
            // Update active state
            document.querySelectorAll('[data-nav]').forEach(item => item.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Switch to tab function
function switchToTab(tab) {
    // Hide all content sections with fade out
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        setTimeout(() => {
            section.classList.remove('active');
        }, 200);
    });
    
    // Hide notices when not on dashboard
    if (tab !== 'dashboard') {
        document.body.classList.add('hidden-notices');
    } else {
        document.body.classList.remove('hidden-notices');
    }
    
    // Show selected section with fade in
    const targetSection = document.getElementById(tab);
    if (targetSection) {
        setTimeout(() => {
            targetSection.classList.add('active');
            targetSection.style.opacity = '1';
            targetSection.style.transform = 'translateY(0)';
        }, 300);
    }
}

// Open modal for purchasing data
function openModal(network) {
    const card = document.querySelector(`.network-card[data-network="${network.toLowerCase()}"]`);
    if (card && card.classList.contains('out-of-stock')) {
        showMessage('This network is currently out of stock. Please try another network.', 'error');
        return;
    }

    selectedNetwork = network;
    document.getElementById('modalTitle').textContent = `Purchase ${network} Data Bundle`;
    
    // Hide all plan groups and show only the one for the selected network
    document.querySelectorAll('.plans-group').forEach(group => {
        if (group.dataset.telco === network) {
            group.style.display = 'block';
        } else {
            group.style.display = 'none';
        }
    });

    // Clear previous selections
    document.querySelectorAll('.plan-item').forEach(p => p.classList.remove('selected'));
    
    // Add click event listeners to the dynamically rendered plan options
    document.querySelectorAll(`.plans-group[data-telco="${network}"] .plan-item`).forEach(planElement => {
        planElement.addEventListener('click', function() {
            document.querySelectorAll(`.plans-group[data-telco="${network}"] .plan-item`).forEach(p => p.classList.remove('selected'));
            this.classList.add('selected');

            // Get selected plan details from data attributes
            selectedPlan = {
                id: this.dataset.id,
                size: this.querySelector('.plan-size').textContent,
                price: this.querySelector('.plan-price').textContent,
                validity: this.querySelector('.plan-validity').textContent.replace('Valid for ', '')
            };
            
            updateSelectedPlan();
            checkFormValidity();
            
            this.style.transform = 'scale(1.05)';
            setTimeout(() => {
                this.style.transform = '';
            }, 200);
        });
    });
    
    document.getElementById('purchaseModal').style.display = 'block';
    document.getElementById('phoneInput').value = '';
    document.getElementById('phoneError').style.display = 'none';
    selectedPlan = null;
    updateSelectedPlan();
    checkFormValidity();
}

// Close modal with animation
function closeModal() {
    const modal = document.getElementById('purchaseModal');
    if (!modal) return;
    const modalContent = modal.querySelector('.modal-content');
    
    modalContent.style.transform = 'translate(-50%, -50%) scale(0.8)';
    modalContent.style.opacity = '0';
    modal.style.opacity = '0';
    
    setTimeout(() => {
        modal.style.display = 'none';
        modalContent.style.transform = 'translate(-50%, -50%) scale(1)';
        modalContent.style.opacity = '1';
        modal.style.opacity = '1';
    }, 300);
}

// Update selected plan display
function updateSelectedPlan() {
    const selectedPlanDiv = document.getElementById('selectedPlan');
    const selectedPlanDetails = document.getElementById('selectedPlanDetails');
    
    if (selectedPlan) {
        selectedPlanDiv.style.display = 'block';
        selectedPlanDiv.style.animation = 'fadeInScale 0.5s ease-out';
        selectedPlanDetails.innerHTML = `
            <strong style="color: #2c3e50; font-size: 1.1rem;">${selectedPlan.size}</strong> - <span style="color: #4CAF50; font-weight: bold;">${selectedPlan.price}</span><br>
            <small style="color: #6c757d;">${selectedPlan.validity}</small>
        `;
    } else {
        selectedPlanDiv.style.display = 'none';
    }
}

// Enhanced message system
function showMessage(text, type = 'info') {
    const existingMessage = document.querySelector('.message');
    if (existingMessage) {
        existingMessage.remove();
    }

    const message = document.createElement('div');
    message.className = `message ${type}`;
    message.textContent = text;
    
    const header = document.querySelector('.header');
    if (header) {
      header.parentNode.insertBefore(message, header.nextSibling);
    } else {
      document.body.prepend(message);
    }
    
    setTimeout(() => {
        message.style.opacity = '0';
        message.style.transform = 'translateY(-20px)';
        setTimeout(() => message.remove(), 300);
    }, 5000);
}

// Validate phone number
function validatePhone(phone) {
    const phoneRegex = /^0\d{9}$/;
    return phoneRegex.test(phone);
}

// Check form validity
function checkFormValidity() {
    const phoneInput = document.getElementById('phoneInput');
    const purchaseBtn = document.getElementById('purchaseBtn');
    const phoneError = document.getElementById('phoneError');
    
    const phone = phoneInput.value;
    const isPhoneValid = validatePhone(phone);
    const isPlanSelected = selectedPlan !== null;
    
    if (phone.length > 0) {
        if (!phone.startsWith('0')) {
            phoneError.textContent = 'Phone number must start with 0';
            phoneError.style.display = 'block';
            phoneInput.classList.add('error');
        } else if (phone.length !== 10) {
            phoneError.textContent = 'Phone number must be exactly 10 digits';
            phoneError.style.display = 'block';
            phoneInput.classList.add('error');
        } else if (!isPhoneValid) {
            phoneError.textContent = 'Please enter a valid phone number';
            phoneError.style.display = 'block';
            phoneInput.classList.add('error');
        } else {
            phoneError.style.display = 'none';
            phoneInput.classList.remove('error');
            phoneInput.style.borderColor = '#4CAF50';
            setTimeout(() => {
                phoneInput.style.borderColor = '';
            }, 1000);
        }
    } else {
        phoneError.style.display = 'none';
        phoneInput.classList.remove('error');
    }
    
    const wasDisabled = purchaseBtn.disabled;
    purchaseBtn.disabled = !(isPhoneValid && isPlanSelected);
    
    if (wasDisabled && !purchaseBtn.disabled) {
        purchaseBtn.style.transform = 'scale(1.05)';
        setTimeout(() => {
            purchaseBtn.style.transform = '';
        }, 200);
    }
}

// Phone input validation
function initPhoneValidation() {
    const phoneInput = document.getElementById('phoneInput');
    
    phoneInput.addEventListener('input', function() {
        this.value = this.value.replace(/\D/g, '');
        
        if (this.value.length > 0 && !this.value.startsWith('0')) {
            this.value = '0' + this.value.slice(0, 9);
        }
        
        if (this.value.length > 10) {
            this.value = this.value.slice(0, 10);
        }
        
        checkFormValidity();
    });

    phoneInput.addEventListener('focus', function() {
        this.style.transform = 'scale(1.02)';
    });

    phoneInput.addEventListener('blur', function() {
        this.style.transform = '';
    });
}

// Process purchase
function processPurchase() {
    const phoneNumber = document.getElementById('phoneInput').value;
    const purchaseBtn = document.getElementById('purchaseBtn');
    
    if (!selectedPlan || !validatePhone(phoneNumber)) {
        showMessage('Please select a plan and enter a valid phone number starting with 0', 'error');
        return;
    }
    
    purchaseBtn.innerHTML = 'Processing... <span class="loading"></span>';
    purchaseBtn.disabled = true;
    purchaseBtn.style.transform = 'scale(0.98)';
    
    // Simulate API call
    setTimeout(() => {
        const orderId = '#DH' + Math.random().toString(36).substr(2, 6).toUpperCase();
        
        purchaseBtn.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
        purchaseBtn.innerHTML = '✓ Order Placed Successfully!';
        
        setTimeout(() => {
            const successMessage = `Order placed successfully!\n\nOrder ID: ${orderId}\nNetwork: ${selectedNetwork}\nPlan: ${selectedPlan.size}\nPhone: ${phoneNumber}\nAmount: ${selectedPlan.price}\n\nData will be delivered within 5 minutes.\n\nThank you for your patience!`;
            alert(successMessage);
            
            showMessage(`Order ${orderId} placed successfully! Data will be delivered within 5 minutes.`, 'success');
            
            purchaseBtn.innerHTML = 'Complete Purchase';
            purchaseBtn.disabled = false;
            purchaseBtn.style.background = '';
            purchaseBtn.style.transform = '';
            
            closeModal();
            
            console.log('Purchase data for Django:', {
                network: selectedNetwork,
                plan: selectedPlan,
                phone: phoneNumber,
                orderId: orderId,
                timestamp: new Date().toISOString()
            });
        }, 1000);
    }, 3000);
}

// Modal click handler
function initModalClickHandler() {
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('purchaseModal');
        if (event.target === modal) {
            closeModal();
        }
    });
}

// Real-time updates simulation
function startRealTimeUpdates() {
    setInterval(() => {
        const statNumbers = document.querySelectorAll('.stat-number');
        statNumbers.forEach((stat) => {
            if (stat.dataset.target) {
                // If a data-target is defined, don't randomly update it
                return;
            }
            if (stat.textContent && !isNaN(parseInt(stat.textContent)) && Math.random() > 0.97) {
                const currentValue = parseInt(stat.textContent);
                const newValue = currentValue + Math.floor(Math.random() * 3) + 1;
                
                stat.style.transform = 'scale(1.2)';
                stat.style.color = '#4CAF50';
                
                setTimeout(() => {
                    stat.textContent = newValue;
                    setTimeout(() => {
                        stat.style.transform = '';
                        stat.style.color = '';
                    }, 200);
                }, 100);
            }
        });

        if (Math.random() > 0.995) {
            const networks = ['MTN', 'AirtelTigo', 'Telecel'];
            const statuses = ['in-stock', 'limited', 'out-of-stock'];
            const randomNetwork = networks[Math.floor(Math.random() * networks.length)];
            const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
            
            stockStatuses[randomNetwork] = randomStatus;
            updateStockStatus(randomNetwork, randomStatus);
        }
    }, 2000);
}

// Initialize counting animations
function initCountAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = entry.target;
                const finalValue = parseFloat(target.dataset.target);
                if (!isNaN(finalValue)) {
                    animateCountUp(target, finalValue);
                    observer.unobserve(target);
                }
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('[data-target]').forEach(el => {
        observer.observe(el);
    });
}

// Initialize profile data
function initProfileData() {
    // These values are now populated directly by Django in the template.
    // The JS functions are no longer needed to write them to the DOM.
}

// Logout function
function logoutUser() {
    if (confirm('Are you sure you want to logout?')) {
        const form = document.createElement('form');
        form.method = 'post';
        form.action = '{% url "signout" %}';
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        if (csrfToken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
        }
        
        document.body.appendChild(form);
        form.submit();
    }
}

// Enhanced CSS transition styles
function addTransitionStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .content-section {
            transition: opacity 0.3s ease, transform 0.3s ease;
        }
        .phone-input, .purchase-btn, .buy-btn {
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        .plans-group {
            display: none; /* Initially hide all plans groups */
        }
    `;
    document.head.appendChild(style);
}

// Initialize everything
document.addEventListener('DOMContentLoaded', function() {
    createParticles();
    addTransitionStyles();
    setGreeting();
    initNavigation();
    initPhoneValidation();
    initModalClickHandler();
    initCountAnimations();
    startRealTimeUpdates();
    
    // Attach event listeners to the dynamically rendered buy buttons
    document.querySelectorAll('.buy-btn').forEach(button => {
        const card = button.closest('.network-card');
        const networkName = card.querySelector('.network-name').textContent.trim();
        button.addEventListener('click', () => openModal(networkName));
    });
    
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);
});

// Keyboard navigation
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('purchaseModal');
        if (modal.style.display === 'block') {
            closeModal();
        }
    }
});

// Performance optimization
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