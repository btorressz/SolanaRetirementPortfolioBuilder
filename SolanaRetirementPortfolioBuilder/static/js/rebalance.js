// Rebalance JavaScript for Solana Retirement Portfolio Builder
class RebalanceManager {
    constructor() {
        this.currentPrices = {};
        this.currentBasket = {};
        this.totalValue = 10000;
        this.simulationData = null;
        
        this.bindEvents();
        this.loadInitialData();
    }

    // Bind event listeners
    bindEvents() {
        // Simulate button
        document.getElementById('simulateBtn').addEventListener('click', () => {
            this.simulateRebalance();
        });

        // Tax simulation button
        document.getElementById('taxSimulateBtn').addEventListener('click', () => {
            this.simulateTaxImpact();
        });

        // Execute button
        document.getElementById('executeBtn').addEventListener('click', () => {
            this.showConfirmModal();
        });

        // Cancel button
        document.getElementById('cancelBtn').addEventListener('click', () => {
            this.cancelSimulation();
        });

        // Confirm execute button
        document.getElementById('confirmExecute').addEventListener('click', () => {
            this.executeRebalance();
        });
    }

    // Load initial data
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadBasketData(),
                this.loadCurrentPrices(),
                this.loadRebalanceHistory()
            ]);
            
            this.updateWeightsTable();
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    // Load basket configuration
    async loadBasketData() {
        const response = await fetch('/api/basket');
        const data = await response.json();
        
        if (data.success) {
            this.currentBasket = data.basket;
            this.totalValue = data.total_value;
        }
    }

    // Load current prices
    async loadCurrentPrices() {
        const response = await fetch('/api/quotes');
        const data = await response.json();
        
        if (data.success) {
            this.currentPrices = data.quotes;
        }
    }

    // Update weights comparison table
    updateWeightsTable() {
        const tableBody = document.getElementById('weightsTable');
        tableBody.innerHTML = '';

        for (const [token, targetWeight] of Object.entries(this.currentBasket)) {
            const price = this.currentPrices[token] || 0;
            const targetValue = this.totalValue * (targetWeight / 100);
            
            // For simulation, assume current weights match target
            // In a real app, this would come from actual holdings
            const currentWeight = targetWeight;
            const currentValue = targetValue;
            const drift = currentWeight - targetWeight;

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <strong>${token}</strong>
                </td>
                <td>$${price.toFixed(price < 1 ? 6 : 2)}</td>
                <td>
                    <span class="badge bg-secondary">${currentWeight.toFixed(1)}%</span>
                </td>
                <td>
                    <span class="badge bg-primary">${targetWeight.toFixed(1)}%</span>
                </td>
                <td>
                    <span class="badge ${Math.abs(drift) > 2 ? 'bg-warning' : 'bg-success'}">
                        ${drift >= 0 ? '+' : ''}${drift.toFixed(1)}%
                    </span>
                </td>
                <td>$${currentValue.toFixed(0)}</td>
                <td>$${targetValue.toFixed(0)}</td>
            `;
            
            tableBody.appendChild(row);
        }
    }

    // Simulate rebalancing
    async simulateRebalance() {
        const btn = document.getElementById('simulateBtn');
        const originalHtml = btn.innerHTML;
        
        try {
            // Show loading
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Simulating...';
            btn.disabled = true;

            const response = await fetch('/api/simulate/rebalance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            const data = await response.json();

            if (data.success) {
                this.simulationData = data;
                this.displaySimulationResults(data);
            } else {
                throw new Error(data.error || 'Simulation failed');
            }

        } catch (error) {
            console.error('Error simulating rebalance:', error);
            alert('Failed to simulate rebalance: ' + error.message);
        } finally {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    }

    // Display simulation results
    displaySimulationResults(data) {
        document.getElementById('noSimulation').style.display = 'none';
        document.getElementById('simulationResults').style.display = 'block';

        // Populate trades table
        const tradesTable = document.getElementById('tradesTable');
        tradesTable.innerHTML = '';

        let totalTradeValue = 0;
        let totalSlippage = 0;

        data.trades.forEach(trade => {
            const slippage = this.estimateTradeSlippage(trade);
            totalTradeValue += trade.value;
            totalSlippage += slippage;

            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${trade.token}</strong></td>
                <td>
                    <span class="badge ${trade.side === 'buy' ? 'bg-success' : 'bg-danger'}">
                        ${trade.side.toUpperCase()}
                    </span>
                </td>
                <td>${trade.quantity.toFixed(4)}</td>
                <td>$${trade.value.toFixed(2)}</td>
                <td class="text-warning">$${slippage.toFixed(2)}</td>
            `;
            tradesTable.appendChild(row);
        });

        // Update summary
        const totalCost = totalSlippage; // In this simulation, only slippage costs
        const costPercentage = (totalCost / this.totalValue) * 100;
        const avgSlippage = data.trades.length > 0 ? (totalSlippage / totalTradeValue) * 100 : 0;

        document.getElementById('totalTradeValue').textContent = `$${totalTradeValue.toFixed(2)}`;
        document.getElementById('totalSlippage').textContent = `$${totalSlippage.toFixed(2)}`;
        document.getElementById('totalCost').textContent = `$${totalCost.toFixed(2)}`;
        document.getElementById('costPercentage').textContent = `${costPercentage.toFixed(3)}%`;
        document.getElementById('numTrades').textContent = data.trades.length;
        document.getElementById('avgSlippage').textContent = `${avgSlippage.toFixed(3)}%`;
    }

    // Estimate slippage for individual trade
    estimateTradeSlippage(trade) {
        // Simple slippage model based on token and trade size
        const slippageRates = {
            'SOL': 0.001,
            'mSOL': 0.002,
            'stSOL': 0.002,
            'BONK': 0.005,
            'USDC': 0.0005
        };

        let baseRate = slippageRates[trade.token] || 0.003;
        
        // Size ladder
        if (trade.value > 10000) {
            baseRate *= 2;
        } else if (trade.value > 1000) {
            baseRate *= 1.5;
        }

        return trade.value * baseRate;
    }

    // Show confirmation modal
    showConfirmModal() {
        if (!this.simulationData) return;

        const totalCost = this.simulationData.slippage_cost || 0;
        const numTrades = this.simulationData.trades.length;
        const slippage = this.simulationData.slippage_cost || 0;

        document.getElementById('confirmCost').textContent = `$${totalCost.toFixed(2)}`;
        document.getElementById('confirmTrades').textContent = numTrades;
        document.getElementById('confirmSlippage').textContent = `$${slippage.toFixed(2)}`;

        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
    }

    // Execute rebalance
    async executeRebalance() {
        if (!this.simulationData) return;

        try {
            const response = await fetch('/api/execute/rebalance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    trades: this.simulationData.trades,
                    total_cost: this.simulationData.slippage_cost,
                    slippage_cost: this.simulationData.slippage_cost
                })
            });

            const data = await response.json();

            if (data.success) {
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('confirmModal'));
                modal.hide();

                // Show success message
                this.showSuccessMessage();

                // Refresh data
                setTimeout(() => {
                    this.loadRebalanceHistory();
                    this.updateRebalanceStats();
                    this.cancelSimulation();
                }, 1000);

            } else {
                throw new Error(data.error || 'Execution failed');
            }

        } catch (error) {
            console.error('Error executing rebalance:', error);
            alert('Failed to execute rebalance: ' + error.message);
        }
    }

    // Show success message
    showSuccessMessage() {
        // Create temporary success alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
            <i class="fas fa-check-circle me-2"></i>
            Rebalance executed successfully!
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        const container = document.querySelector('.container');
        container.insertBefore(alert, container.firstChild);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    // Cancel simulation
    cancelSimulation() {
        document.getElementById('simulationResults').style.display = 'none';
        document.getElementById('noSimulation').style.display = 'block';
        this.simulationData = null;
    }

    // Load rebalance history
    async loadRebalanceHistory() {
        try {
            // For this demo, we'll create some sample history
            // In a real app, this would come from the session/database
            const historyContainer = document.getElementById('rebalanceHistory');
            
            // This would typically fetch from an API endpoint
            // For now, show empty state or sample data
            historyContainer.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-history fa-2x mb-2"></i>
                    <div>No rebalances yet</div>
                </div>
            `;
            
            this.updateRebalanceStats();
            
        } catch (error) {
            console.error('Error loading rebalance history:', error);
        }
    }

    // Update rebalance statistics
    updateRebalanceStats() {
        // These would come from actual session data
        document.getElementById('totalRebalances').textContent = '0';
        document.getElementById('totalCostPaid').textContent = '$0.00';
        document.getElementById('avgCostPaid').textContent = '$0.00';
        document.getElementById('lastRebalance').textContent = 'Never';
    }

    // Add rebalance to history display
    addToHistory(rebalanceData) {
        const historyContainer = document.getElementById('rebalanceHistory');
        
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item p-3 border rounded mb-2';
        historyItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <div class="fw-bold">${rebalanceData.trades.length} trades</div>
                    <div class="small text-muted">${new Date().toLocaleString()}</div>
                </div>
                <div class="text-end">
                    <div class="fw-bold text-danger">$${rebalanceData.total_cost.toFixed(2)}</div>
                    <div class="small text-muted">Cost</div>
                </div>
            </div>
        `;

        // Replace empty state if present
        if (historyContainer.querySelector('.text-center.text-muted')) {
            historyContainer.innerHTML = '';
        }

        historyContainer.insertBefore(historyItem, historyContainer.firstChild);
    }

    // Utility function to format currency
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(amount);
    }

    // Utility function to format percentage
    formatPercentage(value) {
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    }

    // Tax simulation functionality
    async simulateTaxImpact() {
        const taxMethod = document.getElementById('taxMethod').value;
        const taxRate = parseFloat(document.getElementById('taxRate').value);
        const ltcgRate = parseFloat(document.getElementById('ltcgRate').value);
        
        try {
            const response = await fetch('/api/tax/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    method: taxMethod,
                    tax_rate: taxRate,
                    ltcg_rate: ltcgRate
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayTaxResults(data);
            } else {
                console.error('Tax simulation failed:', data.error);
            }
        } catch (error) {
            console.error('Tax simulation error:', error);
        }
    }
    
    displayTaxResults(data) {
        const { summary, details } = data;
        
        // Update summary metrics
        document.getElementById('taxLossHarvest').textContent = 
            `$${Math.abs(summary.tax_loss_harvest).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('taxLiability').textContent = 
            `$${Math.abs(summary.tax_liability).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('netTaxImpact').textContent = 
            `$${summary.net_tax_impact.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('afterTaxReturn').textContent = 
            `$${summary.after_tax_return.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
        // Populate tax lots table
        const tbody = document.getElementById('taxLotsTable');
        tbody.innerHTML = details.map(detail => `
            <tr>
                <td><span class="badge bg-secondary">${detail.token}</span></td>
                <td>${detail.lots_used}</td>
                <td class="${detail.gain_loss >= 0 ? 'text-success' : 'text-danger'}">
                    $${detail.gain_loss.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </td>
                <td>
                    <span class="badge ${detail.is_long_term ? 'bg-success' : 'bg-warning'}">
                        ${detail.is_long_term ? 'Long-term' : 'Short-term'}
                    </span>
                </td>
                <td class="${detail.tax_impact >= 0 ? 'text-danger' : 'text-success'}">
                    $${detail.tax_impact.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </td>
            </tr>
        `).join('');
        
        // Show results
        document.getElementById('taxResults').style.display = 'block';
    }
}

// Initialize rebalance manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new RebalanceManager();
});
