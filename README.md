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

  ---

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

---

# 🎯 Usage Guide

### Basic Portfolio Management
1. **Set Allocation**: Use sliders or +/- buttons to adjust token weights
2. **Apply Presets**: Click preset buttons for quick allocation templates
3. **Monitor Performance**: View real-time metrics in the status bar
4. **Theme Toggle**: Use Alt+T or the theme button for light/dark mode

### Advanced Features
1. **Backtesting**: Navigate to Analytics → Run historical simulations
2. **Stress Testing**: Use Stress Lab → Apply market scenarios
3. **Rebalancing**: Go to Rebalance → Simulate trades before execution
4. **System Health**: Backend monitoring available via API endpoints

### Keyboard Shortcuts
- `Alt + T`: Toggle theme (light/dark)
- `Arrow Keys`: Adjust focused slider
- `Page Up/Down`: Large slider adjustments
- `+/- Buttons`: Precise 1% weight changes

## 🔧 Configuration

### Supported Tokens
- **SOL**: Native Solana token
- **mSOL**: Marinade staked SOL
- **stSOL**: Lido staked SOL  
- **BONK**: Popular meme token
- **USDC**: USD Coin stable coin
- **USDT** Tether

  ---

### API Integration
- **Jupiter API**: Primary price feed via `price.jup.ag/v4`
- **Caching**: 5-10 second TTL with LRU cache
- **Fallbacks**: Mock price generation during API outages
- **Health Checks**: `/api/health/cache` and `/api/health/quotes`

  

### Performance Settings
```python
# Cache configuration
CACHE_TTL = 10          # seconds
CACHE_SIZE = 1000       # max entries
API_TIMEOUT = 10        # seconds
HEALTH_CHECK_INTERVAL = 10  # seconds
```

---

## 📊 API Endpoints

### Portfolio Management
- `GET /` - Main dashboard
- `POST /api/basket` - Update portfolio allocation
- `GET /api/quotes` - Current token prices
- `POST /api/rebalance` - Simulate rebalancing

### Analytics & Testing
- `GET /api/backtest` - Historical performance simulation
- `POST /api/stress-test` - Market stress scenarios
- `GET /api/factor-attribution` - Performance breakdown
- `POST /api/smart-rebalance` - Tax-optimized rebalancing

### Health Monitoring
- `GET /api/health/cache` - Cache performance metrics
- `GET /api/health/quotes` - API latency and status
- `GET /api/health/system` - Overall system health

  ## 🧪 Testing

### Manual Testing Checklist
- [✅ ]  Portfolio weight adjustments (sliders and buttons)
- [✅ ] Theme toggle functionality (light/dark)
- [ ] Keyboard navigation and shortcuts
- [ ] Health widget status updates
- [ ] Responsive design on mobile
- [ ] Screen reader compatibility

### Performance Testing
- [ ] Cache hit rates >70% during normal operation
- [ ] API response times <2s under normal load
- [ ] Health widget updates every 10 seconds
- [ ] Graceful fallback during API outages


## 🛡️ Security & Privacy

### Data Handling
- **Session-based**: No persistent user data storage
- **No Authentication**: Educational/demo application
- **Mock Fallbacks**: Simulated data during API outages
- **Client-side State**: Portfolio stored in browser sessions

### API Security
- **Rate Limiting**: Built-in Jupiter API rate limits
- **Timeout Protection**: 10-second request timeouts
- **Error Handling**: Comprehensive error catching and logging

---

### 💡 Inspiration
- After reviewing the recent executive order opening 401(k) plans to crypto, real estate, and other alternative assets, I was inspired to build a proof-of-concept over the weekend — the Solana Retirement Portfolio Builder. The idea was to explore how such a policy shift could translate into practical tools for portfolio construction, risk analysis, and performance modeling in a retirement-focused crypto allocation. This simulator serves as a research platform, enabling backtesting, stress testing, and advanced analytics for Solana-based portfolios, with potential applications in evaluating risk, rebalancing strategies, and long-term return profiles for 401(k) or retirement fund scenarios.

---

### 📸 Screenshots 

> ⚠️ **Note:** When these screenshots were taken, the API was not fetching live data for a few listed cryptocurrencies.  
> This was due to temporary data availability issues and does not reflect the current functionality.  
> I will be reviewing again to ensure prices are correct.


![Solana Retirement Portfolio Builder Screenshot](https://github.com/btorressz/SolanaRetirementPortfolioBuilder/blob/main/solretirement1.jpg)

![Solana Retirement Portfolio Builder Screenshot](https://github.com/btorressz/SolanaRetirementPortfolioBuilder/blob/main/solretirement2.jpg)

![Solana Retirement Portfolio Builder Screenshot](https://github.com/btorressz/SolanaRetirementPortfolioBuilder/blob/main/solretirement3.jpg)

![Solana Retirement Portfolio Builder Screenshot](https://github.com/btorressz/SolanaRetirementPortfolioBuilder/blob/main/solretirement4.jpg)






