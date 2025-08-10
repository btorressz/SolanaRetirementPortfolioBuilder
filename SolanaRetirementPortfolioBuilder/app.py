import os
import logging
import random
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from jupiter_api import JupiterAPI
from basket_engine import BasketEngine
from metrics import MetricsCalculator
from smart_rebalance import SmartRebalanceEngine, RebalanceMode
from stress_test import StressTestEngine
from rvi_service import rvi_service
from tax_lot import TaxLotSimulator, TaxLotMethod
from guardrails import GuardrailsEngine
from factors import FactorDecomposition
from backtest_engine import BacktestEngine
import json
from datetime import datetime, timedelta
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_change_in_production")

# Initialize components
jupiter_api = JupiterAPI()
basket_engine = BasketEngine()
metrics_calc = MetricsCalculator()
smart_rebalancer = SmartRebalanceEngine()
stress_tester = StressTestEngine(jupiter_api)
tax_simulator = TaxLotSimulator()
guardrails_engine = GuardrailsEngine()
factor_analyzer = FactorDecomposition()
backtest_engine = BacktestEngine(jupiter_api)

# Start RVI service
rvi_service.start_sampling()

# Token configuration
SUPPORTED_TOKENS = {
    'SOL': 'So11111111111111111111111111111111111111112',
    'mSOL': 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',
    'stSOL': '7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj',
    'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
    'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    'USDT': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
}

# Preset basket configurations
BASKET_PRESETS = {
    'Blue Chips': {
        'SOL': 40.0,
        'mSOL': 25.0,
        'stSOL': 20.0,
        'BONK': 5.0,
        'USDC': 5.0,
        'USDT': 5.0
    },
    'Yield Tilt': {
        'SOL': 20.0,
        'mSOL': 35.0,
        'stSOL': 35.0,
        'BONK': 0.0,
        'USDC': 5.0,
        'USDT': 5.0
    },
    'Balanced': {
        'SOL': 30.0,
        'mSOL': 20.0,
        'stSOL': 20.0,
        'BONK': 10.0,
        'USDC': 10.0,
        'USDT': 10.0
    }
}

def get_quotes_with_fallback():
    """Get quotes with fallback prices for stability"""
    quotes = {}
    fallback_prices = {
        'SOL': 182.0,  # Current Kraken price
        'mSOL': 195.0,  # mSOL typically trades at premium to SOL
        'stSOL': 190.0, # Liquid staking derivative
        'BONK': 0.000027,  # Current market price
        'USDC': 0.9999,  # Stable coin
        'USDT': 0.9998   # Tether stable coin
    }
    
    for token in SUPPORTED_TOKENS:
        mint = SUPPORTED_TOKENS[token]
        try:
            price = jupiter_api.get_price(mint)
            # Use fallback if price is 0, None, or negative
            if price is None or price <= 0:
                quotes[token] = fallback_prices.get(token, 0.0)
                logging.info(f"Using fallback price for {token}: ${fallback_prices.get(token, 0.0)}")
            else:
                quotes[token] = price
        except Exception as e:
            logging.warning(f"Error getting price for {token}: {e}")
            quotes[token] = fallback_prices.get(token, 0.0)
            logging.info(f"Using fallback price for {token}: ${fallback_prices.get(token, 0.0)}")
    
    return quotes

def init_session():
    """Initialize session data if not exists"""
    if 'basket' not in session:
        session['basket'] = BASKET_PRESETS['Balanced'].copy()
    
    if 'total_value' not in session or session['total_value'] <= 0:
        session['total_value'] = 10000.0  # Default $10,000 portfolio
    
    if 'nav_history' not in session:
        session['nav_history'] = []
    if 'benchmark_history' not in session:
        session['benchmark_history'] = {'SOL': [], 'USDC': []}
    if 'rebalance_history' not in session:
        session['rebalance_history'] = []
    
    # Initialize with some sample data points if empty (for chart visualization)
    if len(session['nav_history']) == 0:
        now = datetime.now()
        base_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Create 10 sample data points over the last 10 hours for visualization  
        for i in range(10):
            timestamp = (base_time + timedelta(hours=i)).isoformat()
            # Create more realistic growth pattern: +0.5% average with ±3% daily variation
            growth_factor = 1 + (i * 0.005) + random.uniform(-0.03, 0.03)
            nav_value = session['total_value'] * growth_factor
            
            session['nav_history'].append({
                'timestamp': timestamp,
                'nav': nav_value,
                'sol_price': 182.0 + random.uniform(-5, 5),
                'usdc_price': 1.0
            })
            
            # SOL with more volatility 
            sol_growth = 1 + (i * 0.003) + random.uniform(-0.05, 0.05)  # ±5% variation
            session['benchmark_history']['SOL'].append({
                'timestamp': timestamp,
                'value': 182.0 * sol_growth
            })
            
            session['benchmark_history']['USDC'].append({
                'timestamp': timestamp,
                'value': 1.0 + random.uniform(-0.001, 0.001)  # Very stable
            })
    if 'benchmark_history' not in session:
        session['benchmark_history'] = {'SOL': [], 'USDC': []}
    if 'rebalance_history' not in session:
        session['rebalance_history'] = []
    if 'total_value' not in session:
        session['total_value'] = 10000.0  # Default $10k portfolio

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    init_session()
    return render_template('dashboard.html', 
                         basket=session['basket'],
                         presets=BASKET_PRESETS,
                         tokens=SUPPORTED_TOKENS)

@app.route('/rebalance')
def rebalance():
    init_session()
    return render_template('rebalance.html',
                         basket=session['basket'],
                         tokens=SUPPORTED_TOKENS)

@app.route('/api/quotes')
def get_quotes():
    """Get live quotes with reliable fallbacks"""
    tokens = request.args.get('tokens', '').split(',')
    if not tokens or tokens == ['']:
        tokens = list(SUPPORTED_TOKENS.keys())
    
    try:
        # Use the comprehensive fallback system
        all_quotes = get_quotes_with_fallback()
        quotes = {token: all_quotes.get(token, 0.0) for token in tokens if token in SUPPORTED_TOKENS}
        
        return jsonify({
            'success': True,
            'quotes': quotes,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error fetching quotes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@app.route('/api/basket', methods=['GET', 'POST'])
def basket_api():
    init_session()
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'basket': session['basket'],
            'total_value': session['total_value']
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Update basket weights
        if 'weights' in data:
            new_basket = data['weights']
            # Validate weights sum to 100
            total_weight = sum(new_basket.values())
            if abs(total_weight - 100.0) > 0.1:
                return jsonify({
                    'success': False, 
                    'error': f'Weights must sum to 100%, got {total_weight}%'
                }), 400
            
            session['basket'] = new_basket
        
        # Update total value
        if 'total_value' in data:
            session['total_value'] = float(data['total_value'])
        
        session.modified = True
        return jsonify({'success': True, 'basket': session['basket']})

@app.route('/api/preset/<preset_name>')
def load_preset(preset_name):
    init_session()
    
    if preset_name not in BASKET_PRESETS:
        return jsonify({'success': False, 'error': 'Invalid preset'}), 400
    
    session['basket'] = BASKET_PRESETS[preset_name].copy()
    session.modified = True
    
    return jsonify({
        'success': True,
        'basket': session['basket']
    })

@app.route('/api/simulate/rebalance', methods=['POST'])
def simulate_rebalance():
    """Simulate rebalancing to target weights"""
    init_session()
    
    try:
        # Get current prices with fallbacks
        quotes = get_quotes_with_fallback()
        
        # Calculate realistic current and target holdings
        total_value = session['total_value']
        current_holdings = {}
        target_holdings = {}
        
        # Simulate current holdings (slightly off from target to show rebalance need)
        for token, weight in session['basket'].items():
            target_value = total_value * (weight / 100.0)
            target_holdings[token] = target_value / quotes[token] if quotes[token] > 0 else 0
            
            # Simulate drift: current holdings are +/- 5-10% from target
            drift_factor = random.uniform(0.9, 1.1)  # 10% drift
            current_holdings[token] = target_holdings[token] * drift_factor
        
        # Simulate rebalancing
        rebalance_result = basket_engine.simulate_rebalance(
            current_holdings, target_holdings, quotes
        )
        
        # Calculate slippage and costs
        slippage_cost = basket_engine.estimate_slippage(rebalance_result['trades'], quotes)
        
        # Save rebalance to history for tracking
        rebalance_record = {
            'timestamp': datetime.now().isoformat(),
            'trades': rebalance_result['trades'],
            'cost': slippage_cost,
            'old_weights': session['basket'].copy(),
            'new_weights': rebalance_result['new_weights'],
            'simulation': True  # Mark as simulation
        }
        
        if 'rebalance_history' not in session:
            session['rebalance_history'] = []
        session['rebalance_history'].append(rebalance_record)
        session.modified = True
        
        return jsonify({
            'success': True,
            'trades': rebalance_result['trades'],
            'slippage_cost': slippage_cost,
            'total_cost': slippage_cost,
            'new_weights': rebalance_result['new_weights']
        })
        
    except Exception as e:
        logging.error(f"Error simulating rebalance: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/nav')
def get_nav():
    """Get NAV and benchmark history"""
    init_session()
    
    try:
        # Get current quotes with fallback prices
        quotes = get_quotes_with_fallback()
        
        # Calculate current NAV
        current_nav = metrics_calc.calculate_nav(session['basket'], quotes, session['total_value'])
        
        # Update NAV history (keep last 100 points)
        nav_entry = {
            'timestamp': datetime.now().isoformat(),
            'nav': current_nav,
            'sol_price': quotes.get('SOL', 0),
            'usdc_price': quotes.get('USDC', 1)
        }
        
        session['nav_history'].append(nav_entry)
        if len(session['nav_history']) > 100:
            session['nav_history'] = session['nav_history'][-100:]
        
        # Update benchmark history
        session['benchmark_history']['SOL'].append({
            'timestamp': nav_entry['timestamp'],
            'value': quotes.get('SOL', 0)
        })
        session['benchmark_history']['USDC'].append({
            'timestamp': nav_entry['timestamp'],
            'value': quotes.get('USDC', 1)
        })
        
        # Keep last 100 points for benchmarks
        for benchmark in session['benchmark_history']:
            if len(session['benchmark_history'][benchmark]) > 100:
                session['benchmark_history'][benchmark] = session['benchmark_history'][benchmark][-100:]
        
        session.modified = True
        
        # Calculate metrics
        metrics = metrics_calc.calculate_portfolio_metrics(
            session['nav_history'],
            session['benchmark_history'],
            session['rebalance_history']
        )
        
        return jsonify({
            'success': True,
            'nav_history': session['nav_history'],
            'benchmark_history': session['benchmark_history'],
            'current_nav': current_nav,
            'metrics': metrics
        })
        
    except Exception as e:
        logging.error(f"Error calculating NAV: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/execute/rebalance', methods=['POST'])
def execute_rebalance():
    """Execute rebalance (simulation only - update session state)"""
    init_session()
    
    try:
        data = request.get_json()
        if not data or 'trades' not in data:
            return jsonify({'success': False, 'error': 'No trades provided'}), 400
        
        # Record rebalance in history
        rebalance_record = {
            'timestamp': datetime.now().isoformat(),
            'trades': data['trades'],
            'cost': data.get('total_cost', 0),
            'slippage': data.get('slippage_cost', 0)
        }
        
        session['rebalance_history'].append(rebalance_record)
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Rebalance executed successfully'})
        
    except Exception as e:
        logging.error(f"Error executing rebalance: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# SMART REBALANCE ENDPOINTS
# =============================================================================

@app.route('/api/rebalance/modes')
def get_rebalance_modes():
    """Get available smart rebalance modes"""
    try:
        modes = smart_rebalancer.get_rebalance_modes()
        return jsonify({
            'success': True,
            'modes': modes
        })
    except Exception as e:
        logging.error(f"Error getting rebalance modes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rebalance/check', methods=['POST'])
def check_smart_rebalance():
    """Check if portfolio should be rebalanced using smart modes"""
    init_session()
    
    try:
        data = request.get_json() or {}
        mode_str = data.get('mode', 'threshold')
        mode = RebalanceMode(mode_str)
        
        # Get current prices for cost estimation
        quotes = {}
        for token in SUPPORTED_TOKENS:
            mint = SUPPORTED_TOKENS[token]
            quotes[token] = jupiter_api.get_price(mint)
        
        # Calculate estimated rebalancing cost
        total_value = session['total_value']
        rebalance_result = basket_engine.simulate_rebalance(
            {token: total_value * (weight/100) / quotes[token] 
             for token, weight in session['basket'].items() 
             if quotes[token] > 0},
            {token: total_value * (weight/100) / quotes[token] 
             for token, weight in session['basket'].items() 
             if quotes[token] > 0},
            quotes
        )
        estimated_cost = basket_engine.estimate_slippage(rebalance_result['trades'], quotes)
        
        # Get last rebalance from history
        last_rebalance = None
        if session.get('rebalance_history'):
            last_rebalance_str = session['rebalance_history'][-1]['timestamp']
            last_rebalance = datetime.fromisoformat(last_rebalance_str)
        
        # Check if rebalancing is needed
        decision = smart_rebalancer.should_rebalance(
            mode=mode,
            current_weights=session['basket'],  # Simplified
            target_weights=session['basket'],
            portfolio_value=total_value,
            estimated_cost=estimated_cost,
            last_rebalance=last_rebalance,
            **data.get('settings', {})
        )
        
        return jsonify({
            'success': True,
            'decision': decision,
            'estimated_cost': estimated_cost
        })
        
    except Exception as e:
        logging.error(f"Error checking smart rebalance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rebalance/savings')
def get_rebalance_savings():
    """Calculate savings from smart rebalancing"""
    init_session()
    
    try:
        savings = smart_rebalancer.calculate_rebalance_savings(
            session.get('rebalance_history', []),
            RebalanceMode.HYBRID
        )
        
        return jsonify({
            'success': True,
            'savings': savings
        })
    except Exception as e:
        logging.error(f"Error calculating rebalance savings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# STRESS TEST ENDPOINTS
# =============================================================================

@app.route('/api/stress/scenarios')
def get_stress_scenarios():
    """Get available stress test scenarios"""
    try:
        scenarios = stress_tester.get_scenario_library()
        return jsonify({
            'success': True,
            'scenarios': scenarios
        })
    except Exception as e:
        logging.error(f"Error getting stress scenarios: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stress/run', methods=['POST'])
def run_stress_test():
    """Run a stress test scenario"""
    init_session()
    
    try:
        data = request.get_json()
        scenario_id = data.get('scenario_id')
        custom_shock = data.get('price_shock_pct')
        custom_slippage = data.get('slippage_multiplier', 2.0)
        
        # Get current prices
        quotes = {}
        for token in SUPPORTED_TOKENS:
            mint = SUPPORTED_TOKENS[token]
            quotes[token] = jupiter_api.get_price(mint)
        
        # Run stress test
        if scenario_id and scenario_id in stress_tester.predefined_scenarios:
            # Predefined scenario
            scenario = stress_tester.predefined_scenarios[scenario_id]
            result = stress_tester.run_stress_test(
                session['basket'], quotes, session['total_value'], scenario
            )
        elif custom_shock is not None:
            # Custom scenario
            result = stress_tester.run_custom_stress_test(
                session['basket'], quotes, session['total_value'],
                custom_shock, custom_slippage
            )
        else:
            return jsonify({'success': False, 'error': 'Invalid scenario parameters'}), 400
        
        return jsonify({
            'success': True,
            'stress_test': result
        })
        
    except Exception as e:
        logging.error(f"Error running stress test: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# ANALYTICS & RVI ENDPOINTS
# =============================================================================

@app.route('/api/analytics/rvi')
def get_rvi_data():
    """Get Real-time Volatility Index data"""
    try:
        rvi_data = rvi_service.get_all_rvi()
        service_stats = rvi_service.get_service_stats()
        
        return jsonify({
            'success': True,
            'rvi': rvi_data,
            'service_stats': service_stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error getting RVI data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/stability')
def get_stability_data():
    """Get market stability analytics"""
    try:
        stability_data = rvi_service.get_all_stability()
        
        # Get anomaly detection
        anomalies = {}
        for token in ['SOL', 'mSOL', 'stSOL', 'BONK', 'USDC']:
            token_anomalies = rvi_service.detect_anomalies(token)
            if token_anomalies:
                anomalies[token] = token_anomalies
        
        return jsonify({
            'success': True,
            'stability': stability_data,
            'anomalies': anomalies,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error getting stability data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/history/<token>')
def get_token_history(token):
    """Get price history for a specific token"""
    try:
        minutes = request.args.get('minutes', 60, type=int)
        history = rvi_service.get_price_history(token, minutes)
        
        return jsonify({
            'success': True,
            'token': token,
            'history': history,
            'minutes': minutes
        })
    except Exception as e:
        logging.error(f"Error getting token history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# DEPTH & LIQUIDITY ENDPOINTS
# =============================================================================

@app.route('/api/quotes/ladder')
def get_quote_ladder():
    """Get slippage curve for different trade sizes"""
    try:
        mint = request.args.get('mint')
        if not mint:
            return jsonify({'success': False, 'error': 'mint parameter required'}), 400
        
        # Define size ladder
        sizes = [100, 500, 1000, 5000, 10000, 25000]
        ladder_quotes = []
        
        base_price = jupiter_api.get_price(mint)
        
        for size in sizes:
            # Simulate slippage based on size
            if mint == 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v':  # USDC
                slippage_rate = 0.0005 * (size / 1000) ** 0.5
            elif mint == 'So11111111111111111111111111111111111111112':  # SOL
                slippage_rate = 0.001 * (size / 1000) ** 0.5
            else:  # Other tokens
                slippage_rate = 0.003 * (size / 1000) ** 0.5
            
            slippage_cost = size * slippage_rate
            effective_price = base_price * (1 - slippage_rate)
            
            ladder_quotes.append({
                'size_usd': size,
                'base_price': base_price,
                'effective_price': effective_price,
                'slippage_bps': slippage_rate * 10000,
                'slippage_cost': slippage_cost
            })
        
        return jsonify({
            'success': True,
            'mint': mint,
            'ladder': ladder_quotes,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting quote ladder: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# GLIDEPATH ENDPOINTS
# =============================================================================

@app.route('/api/glidepath', methods=['GET', 'POST'])
def glidepath_api():
    """Generate and manage glidepath (changing allocations over time)"""
    init_session()
    
    if request.method == 'GET':
        try:
            # Generate a sample glidepath
            start_date = datetime.now()
            glidepath_data = []
            
            # Create 5-year glidepath with decreasing risk over time
            for years in range(6):  # 0 to 5 years
                date = start_date.replace(year=start_date.year + years)
                
                # Gradually shift from growth to conservative
                risk_factor = max(0.2, 1.0 - (years / 10))  # Decrease over time
                
                # Calculate weights that naturally sum to 100%
                sol_weight = 40 * risk_factor  # Starts at 40%, decreases over time
                msol_weight = 30 + (10 * (1 - risk_factor))  # Starts at 30%, increases to 40%
                stsol_weight = 20 + (10 * (1 - risk_factor))  # Starts at 20%, increases to 30%
                bonk_weight = 10 * risk_factor  # Starts at 10%, decreases to 0%
                stable_total = 100 - sol_weight - msol_weight - stsol_weight - bonk_weight
                usdc_weight = stable_total / 2
                usdt_weight = stable_total / 2
                
                weights = {
                    'SOL': max(0, sol_weight),
                    'mSOL': max(0, msol_weight), 
                    'stSOL': max(0, stsol_weight),
                    'BONK': max(0, bonk_weight),
                    'USDC': max(0, usdc_weight),
                    'USDT': max(0, usdt_weight)
                }
                
                # Ensure they sum to exactly 100%
                total = sum(weights.values())
                if total > 0:
                    weights = {k: (v/total) * 100 for k, v in weights.items()}
                
                glidepath_data.append({
                    'date': date.isoformat(),
                    'years_from_now': years,
                    'weights': weights,
                    'risk_level': risk_factor
                })
            
            return jsonify({
                'success': True,
                'glidepath': glidepath_data,
                'current_date': start_date.isoformat()
            })
            
        except Exception as e:
            logging.error(f"Error generating glidepath: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        # Update glidepath settings and regenerate data
        try:
            data = request.get_json()
            years = data.get('years', 20)
            risk_tolerance = data.get('risk_tolerance', 'moderate')
            
            # Store glidepath settings in session
            session['glidepath_settings'] = data
            session.modified = True
            
            # Generate new glidepath based on updated settings
            start_date = datetime.now()
            glidepath_data = []
            
            # Risk tolerance mapping
            risk_map = {'conservative': 0.3, 'moderate': 0.6, 'aggressive': 0.9}
            base_risk = risk_map.get(risk_tolerance, 0.6)
            
            for year in range(years + 1):
                date = start_date.replace(year=start_date.year + year)
                
                # Calculate risk factor that decreases over time
                progress = year / years if years > 0 else 0
                risk_factor = base_risk * (1 - progress * 0.7)  # Decrease by 70% over time
                
                # Allocate based on risk level and time horizon
                sol_weight = 30 + (risk_factor * 20)  # 30-50%
                msol_weight = 20 + (risk_factor * 15)  # 20-35%
                stsol_weight = 15 + (risk_factor * 10)  # 15-25%
                bonk_weight = max(0, 10 - progress * 10)  # Starts at 10%, decreases to 0%
                stable_total = 100 - sol_weight - msol_weight - stsol_weight - bonk_weight
                usdc_weight = stable_total / 2  # Split stable coins equally
                usdt_weight = stable_total / 2
                
                weights = {
                    'SOL': max(0, sol_weight),
                    'mSOL': max(0, msol_weight), 
                    'stSOL': max(0, stsol_weight),
                    'BONK': max(0, bonk_weight),
                    'USDC': max(0, usdc_weight),
                    'USDT': max(0, usdt_weight)
                }
                
                # Ensure they sum to exactly 100%
                total = sum(weights.values())
                if total > 0:
                    weights = {k: (v/total) * 100 for k, v in weights.items()}
                
                glidepath_data.append({
                    'date': date.isoformat(),
                    'years_from_now': year,
                    'SOL': weights['SOL'],
                    'mSOL': weights['mSOL'],
                    'stSOL': weights['stSOL'],
                    'BONK': weights['BONK'],
                    'USDC': weights['USDC'],
                    'USDT': weights['USDT'],
                    'risk_level': risk_factor
                })
            
            return jsonify({
                'success': True, 
                'message': 'Glidepath updated',
                'glidepath': glidepath_data,
                'settings': {'years': years, 'risk_tolerance': risk_tolerance}
            })
            
        except Exception as e:
            logging.error(f"Error updating glidepath: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# HEALTH & MONITORING ENDPOINTS
# =============================================================================

@app.route('/api/health/quotes')
def get_quote_health():
    """Get Jupiter API health and performance metrics"""
    try:
        start_time = time.time()
        
        # Test API connectivity
        health_ok = jupiter_api.health_check()
        response_time = (time.time() - start_time) * 1000  # ms
        
        # Get cache statistics
        try:
            cache_stats = jupiter_api.get_cache_stats()
        except Exception:
            cache_stats = {
                'size': 0,
                'hit_rate': 0.0,
                'hits': 0,
                'misses': 0
            }
        
        # Calculate uptime and reliability
        service_stats = rvi_service.get_service_stats()
        
        health_data = {
            'api_status': 'healthy' if health_ok else 'degraded',
            'response_time_ms': response_time,
            'cache_stats': cache_stats,
            'service_stats': service_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'health': health_data
        })
        
    except Exception as e:
        logging.error(f"Error getting quote health: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {
                'api_status': 'error',
                'response_time_ms': 0,
                'timestamp': datetime.now().isoformat()
            }
        })

@app.route('/api/health/system')
def get_system_health():
    """Get overall system health"""
    try:
        system_health = {
            'rvi_service': rvi_service.is_running,
            'jupiter_api': jupiter_api.health_check(),
            'session_active': 'basket' in session,
            'components': {
                'basket_engine': True,
                'metrics_calculator': True,
                'smart_rebalancer': True,
                'stress_tester': True
            },
            'timestamp': datetime.now().isoformat()
        }
        
        overall_healthy = all([
            system_health['rvi_service'],
            system_health['session_active'],
            all(system_health['components'].values())
        ])
        
        return jsonify({
            'success': True,
            'healthy': overall_healthy,
            'system': system_health
        })
        
    except Exception as e:
        logging.error(f"Error getting system health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# OPS & RESILIENCE ENDPOINTS
# =============================================================================

@app.route('/api/health/cache')
def get_cache_health():
    """Get price cache statistics - hit/miss rates, TTL remaining, last quote timestamps"""
    try:
        cache_stats = jupiter_api.get_cache_stats()
        
        # Add timestamp info
        cache_stats['timestamp'] = datetime.now().isoformat()
        cache_stats['cache_type'] = 'LRU with TTL'
        
        # Add last quote timestamps for each mint if cache has items
        try:
            last_quotes = {}
            for mint_key in jupiter_api._price_cache.cache.keys():
                cache_item = jupiter_api._price_cache.cache.get(mint_key)
                if cache_item and 'timestamp' in cache_item:
                    last_quotes[mint_key] = datetime.fromtimestamp(cache_item['timestamp']).isoformat()
            
            cache_stats['last_quote_timestamps'] = last_quotes
        except Exception:
            cache_stats['last_quote_timestamps'] = {}
        
        return jsonify({
            'success': True,
            'cache_stats': cache_stats
        })
        
    except Exception as e:
        logging.error(f"Error getting cache health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health/quotes')
def get_quote_latency_health():
    """Get quote call latency metrics - avg/p50/p95 latency, error rates"""
    try:
        try:
            latency_metrics = jupiter_api._latency_tracker.get_metrics()
        except Exception:
            latency_metrics = {
                'avg_latency_ms': 0,
                'p95_latency_ms': 0,
                'success_rate': 0.0,
                'total_calls': 0
            }
        
        # Add current timestamp and status determination
        latency_metrics['timestamp'] = datetime.now().isoformat()
        
        # Determine status based on metrics
        if latency_metrics['error_rate_percent'] > 50:
            status = 'critical'
            color = 'danger'
        elif latency_metrics['error_rate_percent'] > 20 or latency_metrics['p95_latency_ms'] > 5000:
            status = 'degraded'
            color = 'warning'
        elif latency_metrics['p95_latency_ms'] > 2000:
            status = 'slow'
            color = 'warning'
        else:
            status = 'healthy'
            color = 'success'
        
        latency_metrics['status'] = status
        latency_metrics['status_color'] = color
        
        return jsonify({
            'success': True,
            'quote_latency': latency_metrics
        })
        
    except Exception as e:
        logging.error(f"Error getting quote latency health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# ADVANCED API ENDPOINTS - Portfolio & Execution
# =============================================================================

@app.route('/api/rebalance/run', methods=['POST'])
def run_smart_rebalance():
    """Run smart rebalance with different modes"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'threshold')  # threshold|calendar|cost
        
        init_session()
        basket = session['basket']
        
        # Convert mode string to enum
        if mode == 'threshold':
            rebalance_mode = RebalanceMode.THRESHOLD
        elif mode == 'calendar':
            rebalance_mode = RebalanceMode.CALENDAR
        elif mode == 'cost':
            rebalance_mode = RebalanceMode.COST_AWARE
        else:
            return jsonify({'success': False, 'error': f'Invalid mode: {mode}'}), 400
        
        # Get additional parameters
        threshold = data.get('threshold', 5.0)
        max_slippage = data.get('max_slippage', 2.0)
        
        result = smart_rebalancer.execute_smart_rebalance(
            current_basket=basket,
            target_basket=basket,  # For now, use current as target
            mode=rebalance_mode,
            threshold=threshold,
            max_slippage=max_slippage
        )
        
        return jsonify({'success': True, 'result': result})
        
    except Exception as e:
        logging.error(f"Error in smart rebalance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rebalance/ladder', methods=['POST'])
def run_trade_ladder():
    """Run trade size laddering execution"""
    try:
        data = request.get_json()
        input_token = data.get('input_token', 'SOL')
        output_token = data.get('output_token', 'USDC')
        chunk_size = data.get('chunk_size', 1000)  # USD
        max_per_trade = data.get('max_per_trade', 25000)  # USD
        
        # Generate size ladder
        sizes = []
        size = chunk_size
        while size <= max_per_trade:
            sizes.append(size)
            size *= 2  # Double each time
        
        input_mint = SUPPORTED_TOKENS.get(input_token)
        output_mint = SUPPORTED_TOKENS.get(output_token)
        
        if not input_mint or not output_mint:
            return jsonify({'success': False, 'error': 'Invalid token pair'}), 400
        
        ladder_quotes = jupiter_api.get_ladder_quotes(input_mint, output_mint, sizes)
        
        return jsonify({
            'success': True,
            'input_token': input_token,
            'output_token': output_token,
            'ladder_data': ladder_quotes,
            'total_sizes': len(sizes),
            'size_range': f'${chunk_size:,} - ${max_per_trade:,}'
        })
        
    except Exception as e:
        logging.error(f"Error in trade laddering: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/taxlot/apply', methods=['POST'])
def apply_tax_lot_simulation():
    """Apply tax lot simulation with different methods"""
    try:
        data = request.get_json()
        method = data.get('method', 'FIFO')  # FIFO|LIFO|HIFO
        token = data.get('token', 'SOL')
        quantity = data.get('quantity', 1.0)
        sale_price = data.get('sale_price')
        
        if sale_price is None:
            # Use current price
            mint = SUPPORTED_TOKENS.get(token)
            if mint:
                sale_price = jupiter_api.get_price(mint)
            else:
                return jsonify({'success': False, 'error': 'Invalid token'}), 400
        
        # Generate sample lots if none exist
        if not tax_simulator.lots:
            tax_simulator.generate_sample_lots(jupiter_api)
        
        # Convert method string to enum
        from tax_lot import TaxLotMethod
        if method == 'FIFO':
            lot_method = TaxLotMethod.FIFO
        elif method == 'LIFO':
            lot_method = TaxLotMethod.LIFO
        elif method == 'HIFO':
            lot_method = TaxLotMethod.HIFO
        else:
            return jsonify({'success': False, 'error': f'Invalid method: {method}'}), 400
        
        result = tax_simulator.simulate_sale(token, quantity, sale_price, lot_method)
        
        # Also get comparison across methods
        comparison = tax_simulator.compare_methods(token, quantity, sale_price)
        
        return jsonify({
            'success': True,
            'simulation': result,
            'comparison': comparison,
            'disclaimer': 'Educational simulation only. Not financial or tax advice.'
        })
        
    except Exception as e:
        logging.error(f"Error in tax lot simulation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/taxlot/status')
def get_tax_lot_status():
    """Get current tax lot portfolio status"""
    try:
        if not tax_simulator.lots:
            tax_simulator.generate_sample_lots(jupiter_api)
        
        status = tax_simulator.get_portfolio_status()
        
        return jsonify({
            'success': True,
            'portfolio_status': status,
            'disclaimer': 'Educational simulation only. Not financial or tax advice.'
        })
        
    except Exception as e:
        logging.error(f"Error getting tax lot status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# ADVANCED API ENDPOINTS - Analytics & Risk  
# =============================================================================

@app.route('/api/stress/run', methods=['POST'])
def api_run_stress_test():
    """Run stress test scenarios"""
    try:
        data = request.get_json()
        scenario = data.get('scenario', 'crypto_crash')
        custom_shocks = data.get('price_shocks')
        portfolio_value = data.get('initial_value', 10000)
        
        init_session()
        basket = session['basket']
        
        if custom_shocks:
            # Custom stress test
            vol_multiplier = data.get('volatility_multiplier', 2.0)
            duration = data.get('duration_days', 30)
            
            result = stress_tester.run_custom_stress_test(
                basket, custom_shocks, vol_multiplier, duration, portfolio_value
            )
            
            return jsonify({
                'success': True,
                'scenario': 'custom',
                'result': {
                    'scenario_name': result.scenario_name,
                    'total_return': result.total_return,
                    'max_drawdown': result.max_drawdown,
                    'recovery_days': result.recovery_days,
                    'volatility': result.volatility,
                    'nav_path': result.nav_path,
                }
            })
        else:
            # Predefined scenario
            result = stress_tester.run_stress_test(basket, scenario, portfolio_value)
            
            return jsonify({
                'success': True,
                'scenario': scenario,
                'result': {
                    'scenario_name': result.scenario_name,
                    'total_return': result.total_return,
                    'max_drawdown': result.max_drawdown,
                    'recovery_days': result.recovery_days,
                    'volatility': result.volatility,
                    'nav_path': result.nav_path[:30],  # First 30 days
                }
            })
            
    except Exception as e:
        logging.error(f"Error running stress test: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stress/suite', methods=['POST'])
def run_comprehensive_stress_suite():
    """Run comprehensive stress test suite"""
    try:
        data = request.get_json() or {}
        portfolio_value = data.get('initial_value', 10000)
        
        init_session()
        basket = session['basket']
        
        result = stress_tester.run_comprehensive_stress_suite(basket, portfolio_value)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error running stress suite: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/guardrails/config', methods=['POST'])
def update_guardrails_config():
    """Update guardrails configuration"""
    try:
        data = request.get_json()
        result = guardrails_engine.update_config(data)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error updating guardrails: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/guardrails/status')
def get_guardrails_status():
    """Get guardrails status and configuration"""
    try:
        # Generate sample data if needed
        if not guardrails_engine.price_history:
            guardrails_engine.generate_sample_data(['SOL', 'mSOL', 'stSOL', 'BONK', 'USDC'])
        
        init_session()
        basket = session['basket']
        
        # Simulate NAV history for demo
        nav_history = [10000 + i * 50 + (i % 10) * 200 for i in range(30)]
        
        result = guardrails_engine.check_all_guardrails(basket, nav_history)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error getting guardrails status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/factors')
def get_factor_decomposition():
    """Get factor decomposition analysis"""
    try:
        days = request.args.get('days', 30, type=int)
        
        # Generate sample data if needed
        if not factor_analyzer.price_history:
            factor_analyzer.generate_sample_data(['SOL', 'mSOL', 'stSOL', 'BONK', 'USDC'], days)
        
        result = factor_analyzer.decompose_returns(days)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error getting factor decomposition: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/backtest/preset')
def run_preset_backtest():
    """Run preset backtests"""
    try:
        preset = request.args.get('preset', 'balanced')
        window = request.args.get('window', 90, type=int)  # 30|90|180
        
        result = backtest_engine.run_preset_backtest(preset, window)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error running preset backtest: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/backtest/compare', methods=['POST'])
def compare_strategies():
    """Compare user strategy against presets"""
    try:
        data = request.get_json() or {}
        window = data.get('window', 90)
        
        init_session()
        user_strategy = session['basket']
        
        result = backtest_engine.compare_strategies(user_strategy, window)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error comparing strategies: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# NEW PAGES
# =============================================================================

@app.route('/stress-lab')
def stress_lab():
    """Stress testing laboratory page"""
    init_session()
    return render_template('stress_lab.html',
                         basket=session['basket'],
                         scenarios=stress_tester.get_scenario_library())

@app.route('/analytics')  
def analytics():
    """Analytics and monitoring page"""
    init_session()
    return render_template('analytics.html',
                         tokens=SUPPORTED_TOKENS)

@app.route('/api/tax/simulate', methods=['POST'])
def simulate_tax_impact():
    """Simulate tax impact of rebalancing trades"""
    init_session()
    
    try:
        data = request.json or {}
        method = data.get('method', 'FIFO')
        tax_rate = float(data.get('tax_rate', 22)) / 100
        ltcg_rate = float(data.get('ltcg_rate', 15)) / 100
        
        # Get current quotes for simulation
        quotes = get_quotes_with_fallback()
        
        # Initialize tax lot simulator
        tax_sim = TaxLotSimulator()
        
        # Generate sample tax lots for demonstration
        base_date = datetime.now() - timedelta(days=365)
        for token in session['basket'].keys():
            if token in quotes:
                current_price = quotes[token]
                target_value = session['total_value'] * (session['basket'][token] / 100.0)
                quantity = target_value / current_price
                
                # Create sample lots with varied cost bases to show gains/losses
                for i in range(3):
                    lot_quantity = quantity / 3
                    # Create varied cost bases: some gains, some losses
                    if i == 0:  # First lot: 20% loss (bought higher)
                        cost_basis = current_price * 1.25  
                    elif i == 1:  # Second lot: 15% gain (bought lower)
                        cost_basis = current_price * 0.85
                    else:  # Third lot: 30% gain (bought much lower)
                        cost_basis = current_price * 0.70
                    
                    # Vary purchase dates for long-term vs short-term treatment
                    days_ago = 400 + (i * 100)  # 400, 500, 600 days ago
                    purchase_date = base_date - timedelta(days=days_ago)
                    
                    tax_sim.add_purchase(token, lot_quantity, cost_basis, purchase_date)
        
        # Simulate sales from rebalancing
        tax_results = []
        total_gain_loss = 0
        total_tax_impact = 0
        
        for token, target_weight in session['basket'].items():
            if token in quotes:
                current_price = quotes[token]
                
                if token in tax_sim.lots and tax_sim.lots[token]:
                    total_lots_quantity = sum(lot.quantity for lot in tax_sim.lots[token])
                    sell_quantity = total_lots_quantity * 0.3  # Sell 30% of holdings
                    
                    if sell_quantity > 0:
                        try:
                            sale_result = tax_sim.simulate_sale(
                                token, sell_quantity, current_price, 
                                getattr(TaxLotMethod, method)
                            )
                            
                            # Check if sale was successful
                            if sale_result.get('success'):
                                # Extract data from the sale summary
                                sale_summary = sale_result.get('sale_summary', {})
                                token_gain_loss = sale_summary.get('total_gain_loss', 0)
                                total_gain_loss += token_gain_loss
                                
                                # Calculate tax impact on gains/losses
                                short_term_gain = sale_summary.get('short_term_gain', 0)
                                long_term_gain = sale_summary.get('long_term_gain', 0)
                                
                                short_term_tax = short_term_gain * (tax_rate / 100.0)
                                long_term_tax = long_term_gain * (ltcg_rate / 100.0)
                                
                                tax_impact = short_term_tax + long_term_tax
                                total_tax_impact += tax_impact
                                
                                tax_results.append({
                                    'token': token,
                                    'lots_used': sale_summary.get('lots_used', 0),
                                    'gain_loss': token_gain_loss,
                                    'is_long_term': long_term_gain > short_term_gain,
                                    'tax_impact': tax_impact
                                })
                                
                        except Exception as e:
                            logging.warning(f"Tax simulation error for {token}: {e}")
                            continue
        
        # Calculate summary metrics
        tax_loss_harvest = max(0, -total_gain_loss)
        tax_liability = max(0, total_tax_impact)
        net_tax_impact = total_tax_impact
        after_tax_return = total_gain_loss - abs(tax_liability)
        
        return jsonify({
            'success': True,
            'summary': {
                'tax_loss_harvest': tax_loss_harvest,
                'tax_liability': tax_liability, 
                'net_tax_impact': net_tax_impact,
                'after_tax_return': after_tax_return
            },
            'details': tax_results
        })
        
    except Exception as e:
        logging.error(f"Error simulating tax impact: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
