// Accessibility enhancement JavaScript for Solana Retirement Portfolio Builder

// Initialize accessibility features when DOM loads
document.addEventListener('DOMContentLoaded', function() {
    initializeStepButtons();
    enhanceKeyboardNavigation();
    improveChartAccessibility();
});

// Initialize step buttons for weight controls
function initializeStepButtons() {
    document.querySelectorAll('.step-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const token = this.dataset.token;
            const action = this.dataset.action;
            const slider = document.getElementById(`slider-${token}`);
            
            if (!slider) return;
            
            let currentValue = parseFloat(slider.value);
            let newValue;
            
            if (action === 'increase') {
                newValue = Math.min(parseFloat(slider.max), currentValue + 1);
            } else {
                newValue = Math.max(parseFloat(slider.min), currentValue - 1);
            }
            
            // Update slider value
            slider.value = newValue;
            
            // Trigger input event to update the portfolio
            const event = new Event('input', { bubbles: true });
            slider.dispatchEvent(event);
            
            // Update visual display
            const weightDisplay = document.getElementById(`weight-${token}`);
            if (weightDisplay) {
                weightDisplay.textContent = `${newValue.toFixed(1)}%`;
            }
            
            // Focus the slider for keyboard users
            slider.focus();
            
            // Announce the change to screen readers
            announceWeightChange(token, newValue);
        });
    });
}

// Enhance keyboard navigation
function enhanceKeyboardNavigation() {
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Alt+T for theme toggle (already handled in base.html)
        
        // Ctrl+H to focus on health widget
        if (e.ctrlKey && e.key === 'h') {
            e.preventDefault();
            const healthWidget = document.getElementById('healthWidget');
            if (healthWidget) {
                healthWidget.tabIndex = 0;
                healthWidget.focus();
                healthWidget.style.outline = '2px solid var(--solana-purple)';
                setTimeout(() => {
                    healthWidget.style.outline = '';
                }, 2000);
            }
        }
        
        // Arrow keys for slider navigation when focused
        if (e.target.classList.contains('weight-slider')) {
            const step = parseFloat(e.target.step) || 0.5;
            let handled = false;
            
            switch(e.key) {
                case 'ArrowUp':
                case 'ArrowRight':
                    e.target.value = Math.min(
                        parseFloat(e.target.max), 
                        parseFloat(e.target.value) + step
                    );
                    handled = true;
                    break;
                    
                case 'ArrowDown':
                case 'ArrowLeft':
                    e.target.value = Math.max(
                        parseFloat(e.target.min), 
                        parseFloat(e.target.value) - step
                    );
                    handled = true;
                    break;
                    
                case 'PageUp':
                    e.target.value = Math.min(
                        parseFloat(e.target.max), 
                        parseFloat(e.target.value) + 5
                    );
                    handled = true;
                    break;
                    
                case 'PageDown':
                    e.target.value = Math.max(
                        parseFloat(e.target.min), 
                        parseFloat(e.target.value) - 5
                    );
                    handled = true;
                    break;
            }
            
            if (handled) {
                e.preventDefault();
                const event = new Event('input', { bubbles: true });
                e.target.dispatchEvent(event);
            }
        }
    });
    
    // Improve focus indicators for sliders
    document.querySelectorAll('.weight-slider').forEach(slider => {
        slider.addEventListener('focus', function() {
            this.classList.add('keyboard-focused');
        });
        
        slider.addEventListener('blur', function() {
            this.classList.remove('keyboard-focused');
        });
    });
}

// Improve chart accessibility
function improveChartAccessibility() {
    // Add aria-labels and make charts focusable
    const chartCanvases = document.querySelectorAll('canvas');
    
    chartCanvases.forEach((canvas, index) => {
        canvas.setAttribute('tabindex', '0');
        canvas.setAttribute('role', 'img');
        
        // Add specific labels based on chart container
        const chartContainer = canvas.closest('[id]');
        if (chartContainer) {
            const containerId = chartContainer.id;
            
            switch(containerId) {
                case 'navChart':
                    canvas.setAttribute('aria-label', 'Portfolio net asset value line chart showing performance over time');
                    break;
                case 'allocationChart':
                    canvas.setAttribute('aria-label', 'Portfolio allocation pie chart showing distribution of assets');
                    break;
                case 'performanceChart':
                    canvas.setAttribute('aria-label', 'Portfolio performance comparison chart');
                    break;
                default:
                    canvas.setAttribute('aria-label', `Interactive chart displaying portfolio data`);
            }
        }
        
        // Add keyboard interaction
        canvas.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                announceChartData(this);
            }
        });
    });
}

// Announce weight changes to screen readers
function announceWeightChange(token, newValue) {
    // Create or update live region
    let liveRegion = document.getElementById('weight-announcer');
    if (!liveRegion) {
        liveRegion = document.createElement('div');
        liveRegion.id = 'weight-announcer';
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.style.position = 'absolute';
        liveRegion.style.left = '-10000px';
        liveRegion.style.width = '1px';
        liveRegion.style.height = '1px';
        liveRegion.style.overflow = 'hidden';
        document.body.appendChild(liveRegion);
    }
    
    liveRegion.textContent = `${token} weight adjusted to ${newValue.toFixed(1)} percent`;
}

// Announce chart data when focused
function announceChartData(canvas) {
    const chartContainer = canvas.closest('[id]');
    if (!chartContainer) return;
    
    let announcement = '';
    const containerId = chartContainer.id;
    
    // Try to get current portfolio data for announcement
    if (containerId === 'allocationChart') {
        // Get allocation data from the page
        const weightDisplays = document.querySelectorAll('[id^="weight-"]');
        const allocations = [];
        
        weightDisplays.forEach(display => {
            const token = display.id.replace('weight-', '');
            const weight = display.textContent;
            allocations.push(`${token}: ${weight}`);
        });
        
        announcement = `Portfolio allocation: ${allocations.join(', ')}`;
    } else if (containerId === 'navChart') {
        const totalValue = document.getElementById('totalValue');
        const totalReturn = document.getElementById('totalReturn');
        
        announcement = `Current portfolio value: ${totalValue ? totalValue.textContent : 'Loading'}`;
        if (totalReturn) {
            announcement += `, Total return: ${totalReturn.textContent}`;
        }
    }
    
    // Announce the data
    if (announcement) {
        const liveRegion = document.getElementById('chart-announcer') || createLiveRegion('chart-announcer');
        liveRegion.textContent = announcement;
    }
}

// Create live region for announcements
function createLiveRegion(id) {
    const liveRegion = document.createElement('div');
    liveRegion.id = id;
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.style.position = 'absolute';
    liveRegion.style.left = '-10000px';
    liveRegion.style.width = '1px';
    liveRegion.style.height = '1px';
    liveRegion.style.overflow = 'hidden';
    document.body.appendChild(liveRegion);
    return liveRegion;
}

// Add accessible keyboard shortcuts help
function addKeyboardShortcutsInfo() {
    const helpInfo = document.createElement('div');
    helpInfo.className = 'keyboard-shortcuts-help';
    helpInfo.innerHTML = `
        <div class="small text-muted mt-2">
            <i class="fas fa-keyboard me-1"></i>
            <strong>Keyboard Shortcuts:</strong>
            Alt+T (theme toggle), 
            Arrow keys (adjust sliders), 
            +/- buttons (precise control),
            Ctrl+H (focus health widget)
        </div>
    `;
    
    const firstCard = document.querySelector('.card-body');
    if (firstCard && !document.querySelector('.keyboard-shortcuts-help')) {
        firstCard.appendChild(helpInfo);
    }
}

// Initialize help info after page loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(addKeyboardShortcutsInfo, 1000);
});