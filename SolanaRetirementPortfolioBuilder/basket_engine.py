import numpy as np
import logging
from typing import Dict, List, Tuple
from datetime import datetime

class BasketEngine:
    """Engine for portfolio basket management and rebalancing"""
    
    def __init__(self):
        self.min_trade_size = 1.0  # Minimum $1 trade
        self.slippage_rates = {
            'SOL': 0.001,    # 0.1% base slippage
            'mSOL': 0.002,   # 0.2% base slippage  
            'stSOL': 0.002,  # 0.2% base slippage
            'BONK': 0.005,   # 0.5% base slippage
            'USDC': 0.0005,  # 0.05% base slippage
        }
    
    def calculate_current_weights(self, holdings: Dict[str, float], prices: Dict[str, float]) -> Dict[str, float]:
        """Calculate current portfolio weights based on holdings and prices"""
        total_value = 0.0
        values = {}
        
        for token, quantity in holdings.items():
            if token in prices and prices[token] > 0:
                values[token] = quantity * prices[token]
                total_value += values[token]
            else:
                values[token] = 0.0
        
        if total_value == 0:
            return {token: 0.0 for token in holdings}
        
        weights = {}
        for token in holdings:
            weights[token] = (values[token] / total_value) * 100.0
        
        return weights
    
    def calculate_required_trades(self, current_holdings: Dict[str, float], 
                                target_weights: Dict[str, float], 
                                prices: Dict[str, float], 
                                total_value: float) -> List[Dict]:
        """Calculate trades required to reach target weights"""
        trades = []
        
        # Calculate current values
        current_values = {}
        current_total = 0.0
        for token, quantity in current_holdings.items():
            if token in prices and prices[token] > 0:
                current_values[token] = quantity * prices[token]
                current_total += current_values[token]
            else:
                current_values[token] = 0.0
        
        # Use provided total value or calculated total
        portfolio_value = total_value if total_value > 0 else current_total
        
        # Calculate target values and required trades
        for token, target_weight in target_weights.items():
            if token not in prices or prices[token] <= 0:
                continue
                
            target_value = portfolio_value * (target_weight / 100.0)
            current_value = current_values.get(token, 0.0)
            trade_value = target_value - current_value
            
            if abs(trade_value) > self.min_trade_size:
                trade_quantity = trade_value / prices[token]
                
                trades.append({
                    'token': token,
                    'side': 'buy' if trade_value > 0 else 'sell',
                    'quantity': abs(trade_quantity),
                    'value': abs(trade_value),
                    'price': prices[token]
                })
        
        return trades
    
    def simulate_rebalance(self, current_holdings: Dict[str, float], 
                          target_holdings: Dict[str, float], 
                          prices: Dict[str, float]) -> Dict:
        """Simulate rebalancing trades"""
        trades = []
        new_holdings = current_holdings.copy()
        
        # Calculate total current value
        total_value = sum(qty * prices.get(token, 0) for token, qty in current_holdings.items())
        
        # Calculate what we need to buy/sell
        for token in target_holdings:
            if token not in prices or prices[token] <= 0:
                continue
                
            current_qty = current_holdings.get(token, 0.0)
            target_qty = target_holdings[token]
            trade_qty = target_qty - current_qty
            
            if abs(trade_qty * prices[token]) > self.min_trade_size:
                trades.append({
                    'token': token,
                    'side': 'buy' if trade_qty > 0 else 'sell',
                    'quantity': abs(trade_qty),
                    'value': abs(trade_qty * prices[token]),
                    'price': prices[token]
                })
                
                new_holdings[token] = target_qty
        
        # Calculate new weights
        new_weights = self.calculate_current_weights(new_holdings, prices)
        
        return {
            'trades': trades,
            'new_holdings': new_holdings,
            'new_weights': new_weights
        }
    
    def estimate_slippage(self, trades: List[Dict], prices: Dict[str, float]) -> float:
        """Estimate total slippage cost for trades using size-ladder model"""
        total_slippage = 0.0
        
        for trade in trades:
            token = trade['token']
            value = trade['value']
            
            if token not in self.slippage_rates:
                continue
            
            base_slippage = self.slippage_rates[token]
            
            # Size-ladder slippage: increases with trade size
            # Small trades: base rate
            # Medium trades ($1k-$10k): 1.5x base rate
            # Large trades ($10k+): 2x base rate
            if value < 1000:
                slippage_rate = base_slippage
            elif value < 10000:
                slippage_rate = base_slippage * 1.5
            else:
                slippage_rate = base_slippage * 2.0
            
            trade_slippage = value * slippage_rate
            total_slippage += trade_slippage
        
        return total_slippage
    
    def calculate_tracking_error(self, portfolio_returns: List[float], 
                               benchmark_returns: List[float]) -> float:
        """Calculate tracking error vs benchmark"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0
        
        portfolio_arr = np.array(portfolio_returns)
        benchmark_arr = np.array(benchmark_returns)
        
        # Calculate excess returns
        excess_returns = portfolio_arr - benchmark_arr
        
        # Tracking error is standard deviation of excess returns
        return float(np.std(excess_returns))
    
    def calculate_rebalance_drag(self, rebalance_history: List[Dict]) -> float:
        """Calculate cumulative cost of rebalancing"""
        total_drag = 0.0
        
        for rebalance in rebalance_history:
            if 'cost' in rebalance:
                total_drag += rebalance['cost']
        
        return total_drag
    
    def calculate_weight_drift(self, current_weights: Dict[str, float], 
                             target_weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate how much each weight has drifted from target"""
        drift = {}
        
        for token in target_weights:
            current = current_weights.get(token, 0.0)
            target = target_weights[token]
            drift[token] = current - target
        
        return drift
    
    def should_rebalance(self, current_weights: Dict[str, float], 
                        target_weights: Dict[str, float], 
                        threshold: float = 5.0) -> bool:
        """Determine if portfolio needs rebalancing based on drift threshold"""
        for token in target_weights:
            current = current_weights.get(token, 0.0)
            target = target_weights[token]
            
            if abs(current - target) > threshold:
                return True
        
        return False
    
    def optimize_trade_order(self, trades: List[Dict]) -> List[Dict]:
        """Optimize the order of trades to minimize impact"""
        if not trades:
            return trades
        
        # Sort by trade size (smaller trades first to test market)
        # Then by token liquidity (more liquid tokens first)
        liquidity_order = ['USDC', 'SOL', 'mSOL', 'stSOL', 'BONK']
        
        def sort_key(trade):
            token = trade['token']
            liquidity_rank = liquidity_order.index(token) if token in liquidity_order else 999
            return (liquidity_rank, trade['value'])
        
        return sorted(trades, key=sort_key)
