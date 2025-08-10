# Solana Retirement Portfolio Builder

A comprehensive Flask-based web application for creating, managing, and rebalancing cryptocurrency portfolios focused on Solana ecosystem tokens. Features live pricing, advanced analytics, backtesting, stress testing, and accessibility-enhanced UI.


## 🚀 Features

### Core Portfolio Management
- **Live Pricing**: Real-time token prices via Jupiter API with intelligent caching
- **Interactive Allocation**: Drag sliders or use +/- buttons to adjust portfolio weights
- **Preset Baskets**: Quick allocation templates (Blue Chips, Yield Tilt, Balanced)
- **Performance Tracking**: Real-time NAV, returns, Sharpe ratio, and drawdown metrics

### Advanced Analytics
- **Backtesting Engine**: Historical performance simulation with custom date ranges
- **Stress Testing**: Portfolio resilience under market crash scenarios
- **Factor Attribution**: Performance breakdown by asset class and risk factors
- **Risk Metrics**: Comprehensive volatility, correlation, and risk-adjusted return analysis

### Smart Rebalancing
- **Trade Simulation**: Pre-execution impact analysis with slippage estimates
- **Tax-Loss Harvesting**: Optimized rebalancing to minimize tax impact
- **Guardrails**: Automated risk controls and position limits
- **Cost Analysis**: Total trade costs and portfolio impact calculations

### Operational Excellence
- **Health Monitoring**: Real-time system health with cache and API latency tracking
- **LRU Caching**: Intelligent price caching with 5-10 second TTL for optimal performance
- **Error Resilience**: Graceful fallbacks and comprehensive error handling
- **Performance Metrics**: Cache hit rates, response times, and system status indicators

### Accessibility & UX
- **Theme Support**: Complete light/dark mode toggle with localStorage persistence
- **Keyboard Navigation**: Full keyboard accessibility with shortcuts (Alt+T, Ctrl+H)
- **Step Controls**: Precise +/- buttons for weight adjustments
- **Screen Reader**: WCAG 2.1 AA compliant with comprehensive aria-labels
- **Responsive Design**: Mobile-first responsive layout with Bootstrap 5

## 🏗️ Architecture

### Backend Components
```
app.py              # Flask application and routing
jupiter_api.py      # Price data integration with caching
basket_engine.py    # Portfolio rebalancing logic
backtest_engine.py  # Historical simulation engine
stress_test.py      # Market stress testing
smart_rebalance.py  # Tax-optimized rebalancing
metrics.py          # Performance analytics
factors.py          # Factor attribution analysis
guardrails.py       # Risk management controls
tax_lot.py          # Tax-loss harvesting
rvi_service.py      # Risk-adjusted returns
```

### Frontend Structure
```
templates/          # Jinja2 templates with Bootstrap 5
├── base.html       # Base layout with theme toggle
├── dashboard.html  # Main portfolio interface
├── rebalance.html  # Rebalancing simulation
├── analytics.html  # Advanced analytics dashboard
└── stress_lab.html # Stress testing interface

static/
├── css/main.css    # Solana-themed styles with CSS variables
├── js/dashboard.js # Portfolio management logic
├── js/rebalance.js # Rebalancing interface


└── js/accessibility.js # Keyboard navigation & screen reader support
```
