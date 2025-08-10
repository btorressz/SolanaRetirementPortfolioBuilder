// Dashboard JavaScript for Solana Retirement Portfolio Builder
class PortfolioDashboard {
    constructor() {
        this.charts = {};
        this.updateInterval = null;
        this.isUpdating = false;
        this.currentBasket = {};
        this.totalValue = 10000;
        
        this.initializeCharts();
        this.bindEvents();
        this.startLiveUpdates();
        
        // Load initial data
        this.loadBasketData();
    }

    // Initialize Chart.js charts
    initializeCharts() {
        // NAV Chart
        const navCtx = document.getElementById('navChart').getContext('2d');
        this.charts.nav = new Chart(navCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Portfolio NAV',
                        data: [],
                        borderColor: '#9945FF',
                        backgroundColor: 'rgba(153, 69, 255, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'SOL Benchmark',
                        data: [],
                        borderColor: '#FF6B35',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [5, 5]
                    },
                    {
                        label: 'USDC Benchmark',
                        data: [],
                        borderColor: '#00D4AA',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [3, 3]
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0,0,0,0.05)'
                        },
                        title: {
                            display: true,
                            text: 'Value ($)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true
                        }
                    }
                }
            }
        });

        // Allocation Pie Chart
        const allocCtx = document.getElementById('allocationChart').getContext('2d');
        this.charts.allocation = new Chart(allocCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#9945FF',  // SOL - Purple
                        '#FF6B35',  // mSOL - Orange  
                        '#00D4AA',  // stSOL - Green
                        '#FFD700',  // BONK - Gold
                        '#FF69B4',  // USDC - Pink
                        '#20B2AA'   // USDT - Light Sea Green
                    ],
                    borderWidth: 0,
                    hoverBorderWidth: 3,
                    hoverBorderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }

    // Bind event listeners
    bindEvents() {
        // Weight sliders
        document.querySelectorAll('.weight-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                this.updateWeight(e.target.dataset.token, parseFloat(e.target.value));
            });
            
            slider.addEventListener('change', () => {
                this.normalizeWeights();
                this.saveBasket();
            });
        });

        // Preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.loadPreset(e.target.dataset.preset);
            });
        });

        // Rebalance button
        document.getElementById('rebalanceBtn').addEventListener('click', () => {
            window.location.href = '/rebalance';
        });

        // Timeframe buttons
        document.querySelectorAll('input[name="timeframe"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.updateChartTimeframe(e.target.id);
            });
        });

        // Smart rebalance mode selector
        const rebalanceModeSelect = document.getElementById('rebalanceModeSelect');
        if (rebalanceModeSelect) {
            rebalanceModeSelect.addEventListener('change', (e) => {
                this.updateSmartRebalanceMode(e.target.value);
            });
        }

        // Quick access buttons
        const depthSnapshotBtn = document.getElementById('depthSnapshotBtn');
        if (depthSnapshotBtn) {
            depthSnapshotBtn.addEventListener('click', () => {
                this.showDepthSnapshot();
            });
        }

        const glidepathBtn = document.getElementById('glidepathBtn');
        if (glidepathBtn) {
            glidepathBtn.addEventListener('click', () => {
                this.showGlidepathBuilder();
            });
        }
    }

    // Load basket data from session
    async loadBasketData() {
        try {
            const response = await fetch('/api/basket');
            const data = await response.json();
            
            if (data.success) {
                this.currentBasket = data.basket;
                this.totalValue = data.total_value;
                this.updateSliders();
                this.updateAllocation();
            }
        } catch (error) {
            console.error('Error loading basket data:', error);
        }
    }

    // Update weight for a token
    updateWeight(token, weight) {
        this.currentBasket[token] = weight;
        
        // Update display
        document.getElementById(`weight-${token}`).textContent = `${weight.toFixed(1)}%`;
        
        // Update total weight display
        this.updateTotalWeight();
        this.updateAllocation();
        this.checkDrift();
    }

    // Normalize weights to sum to 100%
    normalizeWeights() {
        const total = Object.values(this.currentBasket).reduce((sum, weight) => sum + weight, 0);
        
        if (Math.abs(total - 100) > 0.1) {
            const factor = 100 / total;
            for (const token in this.currentBasket) {
                this.currentBasket[token] *= factor;
            }
            this.updateSliders();
        }
        
        this.updateTotalWeight();
    }

    // Update slider positions
    updateSliders() {
        for (const token in this.currentBasket) {
            const slider = document.getElementById(`slider-${token}`);
            const display = document.getElementById(`weight-${token}`);
            
            if (slider && display) {
                slider.value = this.currentBasket[token];
                display.textContent = `${this.currentBasket[token].toFixed(1)}%`;
            }
        }
    }

    // Update total weight display
    updateTotalWeight() {
        const total = Object.values(this.currentBasket).reduce((sum, weight) => sum + weight, 0);
        document.getElementById('totalWeight').textContent = `${total.toFixed(1)}%`;
        
        // Color coding
        const element = document.getElementById('totalWeight');
        if (Math.abs(total - 100) > 0.1) {
            element.classList.add('text-warning');
        } else {
            element.classList.remove('text-warning');
        }
    }

    // Load preset configuration
    async loadPreset(presetName) {
        try {
            const response = await fetch(`/api/preset/${presetName}`);
            const data = await response.json();
            
            if (data.success) {
                this.currentBasket = data.basket;
                this.updateSliders();
                this.updateAllocation();
                this.checkDrift();
                
                // Highlight active preset
                document.querySelectorAll('.preset-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                document.querySelector(`[data-preset="${presetName}"]`).classList.add('active');
            }
        } catch (error) {
            console.error('Error loading preset:', error);
        }
    }

    // Save basket to session
    async saveBasket() {
        try {
            await fetch('/api/basket', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    weights: this.currentBasket,
                    total_value: this.totalValue
                })
            });
        } catch (error) {
            console.error('Error saving basket:', error);
        }
    }

    // Start live price updates
    startLiveUpdates() {
        this.updatePricesAndMetrics();
        this.updateInterval = setInterval(() => {
            this.updatePricesAndMetrics();
        }, 10000); // Update every 10 seconds
    }

    // Update prices and portfolio metrics
    async updatePricesAndMetrics() {
        if (this.isUpdating) return;
        this.isUpdating = true;

        try {
            // Update connection status
            document.getElementById('connectionStatus').innerHTML = 
                '<i class="fas fa-circle text-warning"></i>';

            // Fetch quotes
            const quotesResponse = await fetch('/api/quotes');
            const quotesData = await quotesResponse.json();

            if (quotesData.success) {
                this.updatePriceDisplays(quotesData.quotes);
                
                // Update connection status
                document.getElementById('connectionStatus').innerHTML = 
                    '<i class="fas fa-circle text-success"></i>';
            } else {
                throw new Error('Failed to fetch quotes');
            }

            // Fetch NAV and metrics
            const navResponse = await fetch('/api/nav');
            const navData = await navResponse.json();

            if (navData.success) {
                this.updateCharts(navData);
                this.updateMetrics(navData.metrics);
                document.getElementById('lastUpdate').textContent = 
                    new Date().toLocaleTimeString();
            }

        } catch (error) {
            console.error('Error updating prices:', error);
            document.getElementById('connectionStatus').innerHTML = 
                '<i class="fas fa-circle text-danger"></i>';
        } finally {
            this.isUpdating = false;
        }
    }

    // Update price displays
    updatePriceDisplays(quotes) {
        for (const token in quotes) {
            const priceElement = document.getElementById(`price-${token}`);
            const valueElement = document.getElementById(`value-${token}`);
            
            if (priceElement && valueElement) {
                const price = quotes[token];
                const weight = this.currentBasket[token] || 0;
                const value = this.totalValue * (weight / 100);
                
                priceElement.textContent = `$${price.toFixed(price < 1 ? 6 : 2)}`;
                valueElement.textContent = `$${value.toFixed(0)}`;
            }
        }
    }

    // Update charts with new data
    updateCharts(data) {
        // Update NAV chart
        if (data.nav_history && data.nav_history.length > 0) {
            const navChart = this.charts.nav;
            const maxPoints = 50; // Limit chart points for performance
            
            const navHistory = data.nav_history.slice(-maxPoints);
            const labels = navHistory.map(point => 
                new Date(point.timestamp).toLocaleTimeString()
            );
            const navValues = navHistory.map(point => point.nav);
            
            navChart.data.labels = labels;
            navChart.data.datasets[0].data = navValues;
            
            // Update benchmarks if available
            if (data.benchmark_history.SOL) {
                const solHistory = data.benchmark_history.SOL.slice(-maxPoints);
                const solValues = solHistory.map(point => point.value * this.totalValue);
                navChart.data.datasets[1].data = solValues;
            }
            
            if (data.benchmark_history.USDC) {
                const usdcHistory = data.benchmark_history.USDC.slice(-maxPoints);
                const usdcValues = usdcHistory.map(point => this.totalValue); // USDC is stable
                navChart.data.datasets[2].data = usdcValues;
            }
            
            navChart.update('none');
        }
        
        // Update portfolio value
        if (data.current_nav) {
            document.getElementById('totalValue').textContent = 
                `$${data.current_nav.toFixed(0)}`;
        }
    }

    // Update allocation chart
    updateAllocation() {
        const chart = this.charts.allocation;
        const tokens = Object.keys(this.currentBasket);
        const weights = Object.values(this.currentBasket);
        
        chart.data.labels = tokens;
        chart.data.datasets[0].data = weights;
        chart.update('none');
    }

    // Update performance metrics
    updateMetrics(metrics) {
        if (!metrics) return;
        
        // Update metric displays
        const updates = {
            'totalReturn': `${metrics.total_return >= 0 ? '+' : ''}${metrics.total_return.toFixed(2)}%`,
            'sharpeRatio': metrics.sharpe_ratio.toFixed(2),
            'maxDrawdown': `${metrics.max_drawdown.toFixed(2)}%`,
            'volatility': `${metrics.volatility.toFixed(2)}%`,
            'betaSol': metrics.beta_sol.toFixed(2),
            'alphaSol': `${metrics.alpha_sol >= 0 ? '+' : ''}${metrics.alpha_sol.toFixed(2)}%`,
            'totalRebalances': metrics.total_rebalances,
            'rebalanceCost': `$${metrics.total_rebalance_cost.toFixed(2)}`
        };

        for (const [id, value] of Object.entries(updates)) {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
                
                // Apply color classes
                if (id === 'totalReturn') {
                    element.className = metrics.total_return >= 0 ? 'text-success' : 'text-danger';
                }
            }
        }
    }

    // Check for weight drift
    checkDrift() {
        const driftContainer = document.getElementById('driftAlerts');
        const rebalanceBtn = document.getElementById('rebalanceBtn');
        
        // This would normally compare against actual portfolio weights
        // For now, just check if weights sum to 100%
        const totalWeight = Object.values(this.currentBasket).reduce((sum, w) => sum + w, 0);
        const needsRebalancing = Math.abs(totalWeight - 100) > 0.1;
        
        if (needsRebalancing) {
            driftContainer.innerHTML = `
                <div class="drift-alert warning">
                    <span>Weights don't sum to 100%</span>
                    <span class="fw-bold">${totalWeight.toFixed(1)}%</span>
                </div>
            `;
            rebalanceBtn.disabled = false;
        } else {
            driftContainer.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-check-circle fa-2x mb-2"></i>
                    <div>All weights on target</div>
                </div>
            `;
            rebalanceBtn.disabled = true;
        }
    }

    // Update chart timeframe
    updateChartTimeframe(timeframe) {
        // This would filter the chart data based on timeframe
        // Implementation depends on how much historical data you want to store
        console.log('Switching to timeframe:', timeframe);
    }

    // Smart rebalance mode functions
    async updateSmartRebalanceMode(mode) {
        try {
            const response = await fetch('/api/rebalance/check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: mode })
            });

            const data = await response.json();
            
            if (data.success) {
                const decision = data.decision;
                
                // Update UI elements
                document.getElementById('nextCheck').textContent = 
                    decision.next_check ? new Date(decision.next_check).toLocaleDateString() : 'Manual';
                document.getElementById('estSavings').textContent = 
                    `$${decision.savings.toFixed(2)}`;
                document.getElementById('smartRebalanceReason').textContent = 
                    decision.reason;
                
                // Update rebalance button based on decision
                const rebalanceBtn = document.getElementById('rebalanceBtn');
                if (decision.should_rebalance) {
                    rebalanceBtn.disabled = false;
                    rebalanceBtn.className = 'btn btn-warning btn-sm w-100';
                } else {
                    rebalanceBtn.disabled = true;
                    rebalanceBtn.className = 'btn btn-outline-secondary btn-sm w-100';
                }
            }
        } catch (error) {
            console.error('Error updating smart rebalance mode:', error);
        }
    }

    async showDepthSnapshot() {
        try {
            const modalElement = document.createElement('div');
            modalElement.className = 'modal fade';
            modalElement.setAttribute('tabindex', '-1');
            
            modalElement.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Liquidity Depth Snapshot</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row" id="depthCharts">
                                <div class="col-12 text-center py-4">
                                    <div class="spinner-border" role="status"></div>
                                    <div class="mt-2">Loading depth data...</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modalElement);
            const modal = new bootstrap.Modal(modalElement);
            modal.show();

            // Show simplified depth overview for better performance
            const tokens = ['SOL', 'USDC'];  // Focus on main tokens only
            const tokenInfo = {
                'SOL': { name: 'Solana', mint: 'So11111111111111111111111111111111111111112' },
                'USDC': { name: 'USD Coin', mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' }
            };

            let chartsHtml = `
                <div class="col-12 mb-3">
                    <div class="alert alert-info">
                        <strong>Liquidity Overview:</strong> Showing depth analysis for main portfolio tokens
                    </div>
                </div>
            `;

            // Create summary cards instead of complex charts
            for (const token of tokens) {
                const info = tokenInfo[token];
                chartsHtml += `
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">${info.name} (${token})</h6>
                                <div id="depthInfo_${token}" class="depth-loading">
                                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                                    Loading depth data...
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }

            document.getElementById('depthCharts').innerHTML = chartsHtml;

            // Load depth data with timeout and simplified display
            for (const token of tokens) {
                const info = tokenInfo[token];
                const depthInfoElement = document.getElementById(`depthInfo_${token}`);
                
                try {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
                    
                    const response = await fetch(`/api/quotes/ladder?mint=${info.mint}`, {
                        signal: controller.signal
                    });
                    clearTimeout(timeoutId);
                    
                    if (response.ok) {
                        const data = await response.json();
                        
                        if (data.success && data.ladder && data.ladder.length > 0) {
                            const ladder = data.ladder;
                            const maxSlippage = Math.max(...ladder.map(l => l.slippage_bps / 100));
                            const bestPrice = ladder[0]?.quote_price || 'N/A';
                            const liquidityScore = Math.max(10, 100 - maxSlippage * 10);
                            
                            depthInfoElement.innerHTML = `
                                <div class="row text-center">
                                    <div class="col-6">
                                        <div class="h5 text-primary">$${bestPrice}</div>
                                        <div class="small text-muted">Best Price</div>
                                    </div>
                                    <div class="col-6">
                                        <div class="h5 text-warning">${maxSlippage.toFixed(2)}%</div>
                                        <div class="small text-muted">Max Slippage</div>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <div class="progress" style="height: 20px;">
                                        <div class="progress-bar ${liquidityScore > 70 ? 'bg-success' : liquidityScore > 40 ? 'bg-warning' : 'bg-danger'}" 
                                             style="width: ${liquidityScore}%"></div>
                                    </div>
                                    <div class="small text-muted mt-1">Liquidity Quality: ${liquidityScore.toFixed(0)}%</div>
                                </div>
                            `;
                        } else {
                            depthInfoElement.innerHTML = `
                                <div class="text-muted text-center">
                                    <i class="fas fa-exclamation-triangle"></i>
                                    <div>No depth data available</div>
                                </div>
                            `;
                        }
                    } else {
                        throw new Error(`HTTP ${response.status}`);
                    }
                } catch (error) {
                    console.warn(`Failed to load depth for ${token}:`, error);
                    depthInfoElement.innerHTML = `
                        <div class="text-muted text-center">
                            <i class="fas fa-clock"></i>
                            <div>Timeout - data unavailable</div>
                            <div class="small">Try again later</div>
                        </div>
                    `;
                }
            }

            // Clean up when modal closes
            modalElement.addEventListener('hidden.bs.modal', () => {
                modalElement.remove();
            });

        } catch (error) {
            console.error('Error showing depth snapshot:', error);
            console.error('Error details:', error.message, error.stack);
            alert('Failed to load depth data: ' + error.message);
        }
    }

    async showGlidepathBuilder() {
        try {
            const response = await fetch('/api/glidepath');
            const data = await response.json();
            
            if (!data.success) {
                throw new Error('Failed to load glidepath data');
            }

            const modalElement = document.createElement('div');
            modalElement.className = 'modal fade';
            modalElement.setAttribute('tabindex', '-1');
            
            modalElement.innerHTML = `
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Portfolio Glidepath Builder</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-8">
                                    <canvas id="glidepathPreview" height="300"></canvas>
                                </div>
                                <div class="col-md-4">
                                    <h6>Glidepath Settings</h6>
                                    <div class="mb-3">
                                        <label class="form-label">Years to Retirement</label>
                                        <input type="range" class="form-range" id="glidepathYears" 
                                               min="5" max="40" value="20" step="1">
                                        <span id="yearsDisplay">20 years</span>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Risk Tolerance</label>
                                        <select class="form-select" id="riskTolerance">
                                            <option value="conservative">Conservative</option>
                                            <option value="moderate" selected>Moderate</option>
                                            <option value="aggressive">Aggressive</option>
                                        </select>
                                    </div>
                                    <button class="btn btn-primary w-100" id="applyGlidepath">
                                        Apply Glidepath
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modalElement);
            const modal = new bootstrap.Modal(modalElement);
            modal.show();

            // Create glidepath chart
            const ctx = document.getElementById('glidepathPreview').getContext('2d');
            const glidepathChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.glidepath.map(point => point.years_from_now),
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { 
                            title: { display: true, text: 'Years from Now' }
                        },
                        y: { 
                            beginAtZero: true, 
                            max: 100,
                            title: { display: true, text: 'Allocation %' }
                        }
                    }
                }
            });

            // Update glidepath chart with data
            const tokens = ['SOL', 'mSOL', 'stSOL', 'BONK', 'USDC', 'USDT'];
            const colors = ['#9945FF', '#FF6B35', '#00D4AA', '#FFD700', '#FF69B4', '#20B2AA'];
            
            tokens.forEach((token, index) => {
                glidepathChart.data.datasets.push({
                    label: token,
                    data: data.glidepath.map(point => point[token] || 0),
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length] + '20',
                    fill: false
                });
            });
            
            glidepathChart.update();
            
            // Add interactive slider for years
            document.getElementById('glidepathYears').addEventListener('input', async (e) => {
                const years = parseInt(e.target.value);
                const riskTolerance = document.getElementById('riskTolerance').value;
                
                // Update display
                document.getElementById('yearsDisplay').textContent = years;
                
                try {
                    const response = await fetch('/api/glidepath', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            years: years,
                            risk_tolerance: riskTolerance
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        const newData = result.glidepath;
                        
                        // Update chart datasets for all 6 tokens
                        glidepathChart.data.datasets[0].data = newData.map(point => point.SOL);
                        glidepathChart.data.datasets[1].data = newData.map(point => point.mSOL);
                        glidepathChart.data.datasets[2].data = newData.map(point => point.stSOL);
                        glidepathChart.data.datasets[3].data = newData.map(point => point.BONK);
                        glidepathChart.data.datasets[4].data = newData.map(point => point.USDC);
                        glidepathChart.data.datasets[5].data = newData.map(point => point.USDT);
                        
                        // Update labels
                        glidepathChart.data.labels = newData.map(point => 
                            new Date(point.date).getFullYear().toString()
                        );
                        
                        glidepathChart.update('none'); // Fast update without animation
                    }
                } catch (error) {
                    console.error('Error updating glidepath:', error);
                }
            });
            
            // Add interactive risk tolerance dropdown
            document.getElementById('riskTolerance').addEventListener('change', async (e) => {
                const riskTolerance = e.target.value;
                const years = parseInt(document.getElementById('glidepathYears').value);
                
                try {
                    const response = await fetch('/api/glidepath', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            years: years,
                            risk_tolerance: riskTolerance
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        const newData = result.glidepath;
                        
                        // Update chart datasets for all 6 tokens
                        glidepathChart.data.datasets[0].data = newData.map(point => point.SOL);
                        glidepathChart.data.datasets[1].data = newData.map(point => point.mSOL);
                        glidepathChart.data.datasets[2].data = newData.map(point => point.stSOL);
                        glidepathChart.data.datasets[3].data = newData.map(point => point.BONK);
                        glidepathChart.data.datasets[4].data = newData.map(point => point.USDC);
                        glidepathChart.data.datasets[5].data = newData.map(point => point.USDT);
                        
                        // Update labels
                        glidepathChart.data.labels = newData.map(point => 
                            new Date(point.date).getFullYear().toString()
                        );
                        
                        glidepathChart.update('none'); // Fast update without animation
                    }
                } catch (error) {
                    console.error('Error updating glidepath:', error);
                }
            });

            // Add event listener for the Apply Glidepath button
            document.getElementById('applyGlidepath').addEventListener('click', async () => {
                try {
                    const years = parseInt(document.getElementById('glidepathYears').value);
                    const riskTolerance = document.getElementById('riskTolerance').value;
                    
                    console.log('Applying glidepath:', { years, riskTolerance });
                    
                    const response = await fetch('/api/glidepath', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            years: years,
                            risk_tolerance: riskTolerance
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        // Update the glidepath chart with new data
                        const newData = result.glidepath;
                        
                        // Update chart datasets for all 6 tokens
                        glidepathChart.data.datasets[0].data = newData.map(point => point.SOL);
                        glidepathChart.data.datasets[1].data = newData.map(point => point.mSOL);
                        glidepathChart.data.datasets[2].data = newData.map(point => point.stSOL);
                        glidepathChart.data.datasets[3].data = newData.map(point => point.BONK);
                        glidepathChart.data.datasets[4].data = newData.map(point => point.USDC);
                        glidepathChart.data.datasets[5].data = newData.map(point => point.USDT);
                        
                        // Update labels if years changed
                        glidepathChart.data.labels = newData.map(point => 
                            new Date(point.date).getFullYear().toString()
                        );
                        
                        glidepathChart.update();
                        
                        // Show success message
                        const button = document.getElementById('applyGlidepath');
                        const originalText = button.textContent;
                        button.textContent = 'Applied!';
                        button.className = 'btn btn-success w-100';
                        
                        setTimeout(() => {
                            button.textContent = originalText;
                            button.className = 'btn btn-primary w-100';
                        }, 2000);
                        
                    } else {
                        console.error('Failed to apply glidepath:', result.error);
                    }
                    
                } catch (error) {
                    console.error('Error applying glidepath:', error);
                }
            });

            // Clean up when modal closes
            modalElement.addEventListener('hidden.bs.modal', () => {
                glidepathChart.destroy();
                modalElement.remove();
            });

        } catch (error) {
            console.error('Error showing glidepath builder:', error);
            console.error('Error details:', error.message, error.stack);
            alert('Failed to load glidepath data: ' + error.message);
        }
    }

    // Cleanup
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        Object.values(this.charts).forEach(chart => {
            chart.destroy();
        });
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PortfolioDashboard();
});

// Handle page visibility for performance
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Pause updates when tab is not visible
        console.log('Dashboard paused');
    } else {
        // Resume updates when tab becomes visible
        console.log('Dashboard resumed');
    }
});
