"""
Portfolio Guardrails System
Implements volatility caps and max drawdown stops for risk management
"""

import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

class GuardrailsEngine:
    """Portfolio risk management guardrails"""
    
    def __init__(self):
        self.config = {
            "vol_cap_enabled": False,
            "vol_cap_threshold": 25.0,  # % annual volatility
            "max_drawdown_enabled": False,
            "max_drawdown_threshold": 15.0,  # % max drawdown
            "rebalance_pause_duration": 24,  # hours
            "volatility_lookback_days": 30
        }
        
        self.status = {
            "vol_cap_active": False,
            "drawdown_stop_active": False,
            "last_vol_check": None,
            "last_drawdown_check": None,
            "rebalance_paused_until": None,
            "current_volatility": 0.0,
            "current_drawdown": 0.0
        }
        
        self.price_history = {}  # token -> list of (timestamp, price)
        
    def update_config(self, new_config: Dict) -> Dict:
        """Update guardrails configuration"""
        try:
            for key, value in new_config.items():
                if key in self.config:
                    self.config[key] = value
            
            logging.info(f"Guardrails config updated: {new_config}")
            
            return {
                "success": True,
                "config": self.config,
                "message": "Guardrails configuration updated"
            }
            
        except Exception as e:
            logging.error(f"Error updating guardrails config: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_price_data(self, token: str, price: float, timestamp: Optional[datetime] = None):
        """Add price data for volatility calculations"""
        if timestamp is None:
            timestamp = datetime.now()
            
        if token not in self.price_history:
            self.price_history[token] = []
            
        self.price_history[token].append((timestamp, price))
        
        # Keep only recent data
        cutoff = datetime.now() - timedelta(days=self.config["volatility_lookback_days"] * 2)
        self.price_history[token] = [
            (ts, p) for ts, p in self.price_history[token] if ts > cutoff
        ]
    
    def calculate_volatility(self, token: str) -> float:
        """Calculate annualized volatility for a token"""
        if token not in self.price_history or len(self.price_history[token]) < 10:
            return 0.0
            
        prices = [price for _, price in self.price_history[token]]
        returns = np.diff(np.log(prices))
        
        # Annualized volatility (assuming daily data)
        daily_vol = np.std(returns)
        annualized_vol = daily_vol * np.sqrt(365) * 100  # Convert to percentage
        
        return annualized_vol
    
    def calculate_portfolio_volatility(self, basket: Dict[str, float]) -> float:
        """Calculate portfolio-level volatility"""
        if not basket:
            return 0.0
            
        token_volatilities = {}
        for token in basket.keys():
            token_volatilities[token] = self.calculate_volatility(token)
        
        # Simple weighted average (ignoring correlations for simplicity)
        portfolio_vol = sum(
            (weight / 100) * token_volatilities.get(token, 0)
            for token, weight in basket.items()
        )
        
        return portfolio_vol
    
    def calculate_drawdown(self, nav_history: List[float]) -> float:
        """Calculate maximum drawdown from NAV history"""
        if len(nav_history) < 2:
            return 0.0
            
        nav_array = np.array(nav_history)
        peak = np.maximum.accumulate(nav_array)
        drawdown = (nav_array - peak) / peak * 100
        
        return abs(min(drawdown))
    
    def check_vol_cap(self, basket: Dict[str, float]) -> Dict:
        """Check volatility cap guardrail"""
        if not self.config["vol_cap_enabled"]:
            return {"triggered": False, "action": None}
            
        portfolio_vol = self.calculate_portfolio_volatility(basket)
        self.status["current_volatility"] = portfolio_vol
        self.status["last_vol_check"] = datetime.now()
        
        if portfolio_vol > self.config["vol_cap_threshold"]:
            self.status["vol_cap_active"] = True
            
            # Calculate adjustment: reduce crypto weights, increase USDC
            adjusted_basket = self._apply_vol_cap_adjustment(basket, portfolio_vol)
            
            return {
                "triggered": True,
                "action": "reduce_crypto_exposure",
                "current_volatility": portfolio_vol,
                "threshold": self.config["vol_cap_threshold"],
                "adjusted_basket": adjusted_basket,
                "message": f"Portfolio volatility ({portfolio_vol:.1f}%) exceeds threshold ({self.config['vol_cap_threshold']}%)"
            }
        else:
            self.status["vol_cap_active"] = False
            return {"triggered": False, "action": None}
    
    def check_drawdown_stop(self, nav_history: List[float]) -> Dict:
        """Check maximum drawdown stop guardrail"""
        if not self.config["max_drawdown_enabled"] or len(nav_history) < 10:
            return {"triggered": False, "action": None}
            
        current_drawdown = self.calculate_drawdown(nav_history)
        self.status["current_drawdown"] = current_drawdown
        self.status["last_drawdown_check"] = datetime.now()
        
        if current_drawdown > self.config["max_drawdown_threshold"]:
            self.status["drawdown_stop_active"] = True
            
            # Pause rebalancing for specified duration
            pause_until = datetime.now() + timedelta(hours=self.config["rebalance_pause_duration"])
            self.status["rebalance_paused_until"] = pause_until
            
            return {
                "triggered": True,
                "action": "pause_rebalancing",
                "current_drawdown": current_drawdown,
                "threshold": self.config["max_drawdown_threshold"],
                "paused_until": pause_until.isoformat(),
                "message": f"Drawdown ({current_drawdown:.1f}%) exceeds threshold ({self.config['max_drawdown_threshold']}%)"
            }
        else:
            self.status["drawdown_stop_active"] = False
            return {"triggered": False, "action": None}
    
    def _apply_vol_cap_adjustment(self, basket: Dict[str, float], current_vol: float) -> Dict[str, float]:
        """Apply volatility cap by reducing crypto exposure"""
        # Calculate reduction factor
        target_vol = self.config["vol_cap_threshold"] * 0.9  # 10% buffer
        reduction_factor = target_vol / current_vol if current_vol > 0 else 1.0
        
        adjusted_basket = {}
        usdc_weight = basket.get("USDC", 0)
        
        for token, weight in basket.items():
            if token == "USDC":
                # USDC weight will be increased to compensate
                adjusted_basket[token] = weight
            else:
                # Reduce crypto weights
                adjusted_weight = weight * reduction_factor
                weight_reduction = weight - adjusted_weight
                adjusted_basket[token] = adjusted_weight
                usdc_weight += weight_reduction
        
        # Ensure USDC gets the reallocation
        adjusted_basket["USDC"] = min(usdc_weight, 100.0)
        
        # Normalize to 100%
        total_weight = sum(adjusted_basket.values())
        if total_weight > 0:
            for token in adjusted_basket:
                adjusted_basket[token] = (adjusted_basket[token] / total_weight) * 100
        
        return adjusted_basket
    
    def is_rebalancing_allowed(self) -> bool:
        """Check if rebalancing is currently allowed"""
        if self.status["rebalance_paused_until"]:
            return datetime.now() > self.status["rebalance_paused_until"]
        return True
    
    def check_all_guardrails(self, basket: Dict[str, float], nav_history: List[float]) -> Dict:
        """Check all guardrails and return comprehensive status"""
        vol_check = self.check_vol_cap(basket)
        drawdown_check = self.check_drawdown_stop(nav_history)
        
        alerts = []
        adjustments = {}
        
        if vol_check["triggered"]:
            alerts.append({
                "type": "volatility_cap",
                "severity": "warning",
                "message": vol_check["message"]
            })
            if vol_check.get("adjusted_basket"):
                adjustments["vol_cap_basket"] = vol_check["adjusted_basket"]
        
        if drawdown_check["triggered"]:
            alerts.append({
                "type": "drawdown_stop",
                "severity": "critical",
                "message": drawdown_check["message"]
            })
        
        return {
            "rebalancing_allowed": self.is_rebalancing_allowed(),
            "alerts": alerts,
            "adjustments": adjustments,
            "status": self.status,
            "config": self.config,
            "vol_check": vol_check,
            "drawdown_check": drawdown_check
        }
    
    def get_status(self) -> Dict:
        """Get current guardrails status"""
        return {
            "config": self.config,
            "status": self.status,
            "rebalancing_allowed": self.is_rebalancing_allowed()
        }
    
    def generate_sample_data(self, tokens: List[str], days: int = 30):
        """Generate sample price data for demonstration"""
        base_date = datetime.now() - timedelta(days=days)
        
        base_prices = {
            'SOL': 120.0,
            'mSOL': 132.0,
            'stSOL': 145.0,
            'BONK': 0.000025,
            'USDC': 1.0
        }
        
        for token in tokens:
            if token not in base_prices:
                continue
                
            base_price = base_prices[token]
            self.price_history[token] = []
            
            # Generate daily prices with realistic volatility
            for day in range(days):
                date = base_date + timedelta(days=day)
                
                # Add daily return with some volatility
                daily_return = np.random.normal(0, 0.03 if token != 'USDC' else 0.001)
                if day == 0:
                    price = base_price
                else:
                    price = self.price_history[token][-1][1] * (1 + daily_return)
                
                self.price_history[token].append((date, price))
        
        logging.info(f"Generated sample price data for {len(tokens)} tokens over {days} days")