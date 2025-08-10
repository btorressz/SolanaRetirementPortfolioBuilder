# Overview

The Solana Retirement Portfolio Builder is a comprehensive Flask-based web application that enables users to create, manage, and rebalance cryptocurrency portfolios focused on Solana ecosystem tokens (SOL, mSOL, stSOL, BONK, USDC). The application features live Jupiter API pricing, interactive portfolio management, advanced rebalancing modes, risk analytics, tax simulation, factor attribution, backtesting capabilities, stress testing, operational resilience with caching/health monitoring, and accessibility-enhanced UI with theme support.


# System Architecture

## Frontend Architecture
- **Flask Templates**: Server-side rendered HTML using Jinja2 templating with Bootstrap 5 for responsive UI
- **Chart.js Integration**: Real-time portfolio visualization and performance charts with accessibility enhancements
- **JavaScript Classes**: Modular client-side architecture with `PortfolioDashboard` and `RebalanceManager` classes for state management
- **CSS Variables**: Solana-themed design system with light/dark theme support using CSS custom properties
- **Accessibility Features**: WCAG-compliant design with keyboard navigation, screen reader support, and step controls
- **Theme System**: Complete light/dark mode toggle with localStorage persistence and smooth transitions

## Backend Architecture
- **Flask Web Framework**: Lightweight Python web server handling routing, session management, and API endpoints
- **Modular Component Design**: Separated concerns with dedicated classes:
  - `JupiterAPI`: External price data integration with LRU caching and health monitoring
  - `BasketEngine`: Portfolio rebalancing logic and trade calculations with slippage analysis
  - `MetricsCalculator`: Performance analytics, risk metrics, and factor attribution
  - `BacktestEngine`: Historical performance simulation and strategy validation
  - `StressTester`: Portfolio stress testing under various market scenarios
  - `SmartRebalancer`: Advanced rebalancing with tax-loss harvesting and guardrails
- **Session-based State**: User portfolio data stored in Flask sessions for temporary persistence
- **Health Monitoring**: Real-time system health tracking with cache metrics and API latency monitoring
- **Configuration Management**: Environment-based configuration for API keys and secrets

## Data Flow and Processing
- **Real-time Price Feeds**: Jupiter API integration with LRU caching (5-10 second TTL) and mock fallbacks
- **Portfolio Calculations**: Weight-based allocation system with percentage-driven rebalancing
- **Trade Simulation**: Pre-execution trade impact analysis with slippage calculations and depth analysis
- **Performance Metrics**: Comprehensive analytics including Sharpe ratio, volatility, drawdown, and factor attribution
- **Backtesting Engine**: Historical simulation with configurable date ranges and benchmark comparisons
- **Stress Testing**: Portfolio resilience testing under various market crash and volatility scenarios

## Error Handling and Resilience
- **Multi-API Fallback System**: Jupiter API (primary) → CoinGecko → Kraken with automatic rate limit handling
- **API Timeout Protection**: 10-second request timeouts with graceful fallbacks to cached data
- **LRU Cache System**: Intelligent caching with TTL, hit/miss tracking, and performance metrics
- **Health Monitoring**: Backend health endpoints (/api/health/cache, /api/health/quotes) with status indicators
- **Logging Integration**: Comprehensive logging for debugging and monitoring with error tracking

# External Dependencies

## Core APIs
- **Jupiter API**: Primary price data source for Solana tokens via `price.jup.ag/v4` and quote API
- **CoinGecko API**: Secondary fallback for price data with rate limit handling
- **Kraken API**: Tertiary fallback for SOL and USDC pricing
- **Supported Token Mints**: Pre-configured mint addresses for SOL, mSOL, stSOL, BONK, USDT  and USDC

## Frontend Libraries
- **Bootstrap 5.3.0**: UI framework for responsive design and components
- **Chart.js 4.4.0**: Data visualization for portfolio performance charts
- **Font Awesome 6.4.0**: Icon library for enhanced user interface

## Python Dependencies
- **Flask**: Web framework for application server
- **NumPy**: Mathematical computations for portfolio analytics
- **Pandas**: Data manipulation for time series analysis
- **Requests**: HTTP client for external API communication

## Infrastructure Requirements
- **Session Management**: Requires session secret configuration for user state persistence
- **Environment Variables**: Uses `SESSION_SECRET` for production security
- **Port Configuration**: Runs on port 5000 with host binding to 0.0.0.0 for container compatibility
- **Accessibility Compliance**: WCAG 2.1 AA compliant with keyboard navigation and screen reader support

## Recent Changes (August 2025)
- **Multi-API Fallback System**: Implemented Jupiter → CoinGecko → Kraken fallback chain for maximum uptime
- **Operational Resilience**: Added LRU cache with TTL, health monitoring endpoints, and performance metrics  
- **Rate Limit Handling**: Automatic fallback when APIs hit rate limits (429 errors)
- **Accessibility Enhancements**: Implemented keyboard-first controls, step buttons for weight adjustment, comprehensive aria-labels
- **Theme System**: Complete light/dark mode toggle with CSS variables and localStorage persistence
- **UI Cleanup**: Removed health monitoring widget from frontend for cleaner interface
- **Advanced Features**: Backtesting engine, stress testing, factor attribution, and tax-loss harvesting capabilities
- **Performance**: Optimized with intelligent caching, reduced API calls, and improved error handling
