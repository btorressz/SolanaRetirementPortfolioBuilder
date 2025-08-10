import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import math

class MetricsCalculator:
    """Calculator for portfolio performance metrics"""
    
    def __init__(self):
        self.risk_free_rate = 0.05  # 5% annual risk-free rate
    
    def calculate_nav(self, basket_weights: Dict[str, float], 
                     prices: Dict[str, float], 
                     total_value: float) -> float:
        """Calculate Net Asset Value of the basket"""
        nav = 0.0
        
        for token, weight in basket_weights.items():
            if token in prices and prices[token] > 0:
                token_value = total_value * (weight / 100.0)
                nav += token_value
        
        return nav
    
    def calculate_returns(self, price_series: List[Dict]) -> List[float]:
        """Calculate returns from price series"""
        if len(price_series) < 2:
            return []
        
        returns = []
        for i in range(1, len(price_series)):
            prev_price = price_series[i-1].get('nav', price_series[i-1].get('value', 0))
            curr_price = price_series[i].get('nav', price_series[i].get('value', 0))
            
            if prev_price > 0:
                return_val = (curr_price - prev_price) / prev_price
                returns.append(return_val)
            else:
                returns.append(0.0)
        
        return returns
    
    def calculate_volatility(self, returns: List[float]) -> float:
        """Calculate annualized volatility"""
        if len(returns) < 2:
            return 0.0
        
        return float(np.std(returns) * np.sqrt(252))  # Annualize assuming daily returns
    
    def calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        volatility = np.std(returns)
        
        if volatility == 0:
            return 0.0
        
        # Annualize
        annual_return = mean_return * 252
        annual_vol = volatility * np.sqrt(252)
        
        return float((annual_return - self.risk_free_rate) / annual_vol)
    
    def calculate_max_drawdown(self, price_series: List[Dict]) -> float:
        """Calculate maximum drawdown"""
        if len(price_series) < 2:
            return 0.0
        
        values = [p.get('nav', p.get('value', 0)) for p in price_series]
        
        peak = values[0]
        max_drawdown = 0.0
        
        for value in values[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
        
        return float(max_drawdown)
    
    def calculate_beta(self, portfolio_returns: List[float], 
                      benchmark_returns: List[float]) -> float:
        """Calculate beta vs benchmark"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 1.0
        
        portfolio_arr = np.array(portfolio_returns)
        benchmark_arr = np.array(benchmark_returns)
        
        if np.var(benchmark_arr) == 0:
            return 1.0
        
        covariance = np.cov(portfolio_arr, benchmark_arr)[0][1]
        variance = np.var(benchmark_arr)
        
        return float(covariance / variance)
    
    def calculate_alpha(self, portfolio_returns: List[float], 
                       benchmark_returns: List[float]) -> float:
        """Calculate alpha vs benchmark"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0
        
        portfolio_mean = np.mean(portfolio_returns)
        benchmark_mean = np.mean(benchmark_returns)
        beta = self.calculate_beta(portfolio_returns, benchmark_returns)
        
        # Annualize
        annual_portfolio = portfolio_mean * 252
        annual_benchmark = benchmark_mean * 252
        
        alpha = annual_portfolio - (self.risk_free_rate + beta * (annual_benchmark - self.risk_free_rate))
        
        return float(alpha)
    
    def calculate_information_ratio(self, portfolio_returns: List[float], 
                                  benchmark_returns: List[float]) -> float:
        """Calculate information ratio (active return / tracking error)"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0
        
        portfolio_arr = np.array(portfolio_returns)
        benchmark_arr = np.array(benchmark_returns)
        
        excess_returns = portfolio_arr - benchmark_arr
        
        if len(excess_returns) < 2:
            return 0.0
        
        mean_excess = np.mean(excess_returns)
        tracking_error = np.std(excess_returns)
        
        if tracking_error == 0:
            return 0.0
        
        # Annualize
        annual_excess = mean_excess * 252
        annual_tracking = tracking_error * np.sqrt(252)
        
        return float(annual_excess / annual_tracking)
    
    def calculate_correlation_matrix(self, token_histories: Dict[str, List[Dict]]) -> Dict:
        """Calculate correlation matrix between tokens"""
        if not token_histories:
            return {}
        
        # Convert to returns
        token_returns = {}
        for token, history in token_histories.items():
            if len(history) >= 2:
                returns = self.calculate_returns(history)
                if returns:
                    token_returns[token] = returns
        
        if len(token_returns) < 2:
            return {}
        
        # Ensure all return series have the same length
        min_length = min(len(returns) for returns in token_returns.values())
        if min_length == 0:
            return {}
        
        # Truncate all series to same length
        for token in token_returns:
            token_returns[token] = token_returns[token][-min_length:]
        
        # Calculate correlation matrix
        tokens = list(token_returns.keys())
        correlations = {}
        
        for i, token1 in enumerate(tokens):
            correlations[token1] = {}
            for j, token2 in enumerate(tokens):
                if i == j:
                    correlations[token1][token2] = 1.0
                else:
                    try:
                        corr = float(np.corrcoef(token_returns[token1], token_returns[token2])[0][1])
                        if math.isnan(corr):
                            corr = 0.0
                        correlations[token1][token2] = corr
                    except:
                        correlations[token1][token2] = 0.0
        
        return correlations
    
    def calculate_portfolio_metrics(self, nav_history: List[Dict], 
                                  benchmark_history: Dict[str, List[Dict]], 
                                  rebalance_history: List[Dict]) -> Dict:
        """Calculate comprehensive portfolio metrics"""
        metrics = {}
        
        if not nav_history:
            return self._empty_metrics()
        
        # Portfolio returns
        portfolio_returns = self.calculate_returns(nav_history)
        
        if portfolio_returns:
            metrics['total_return'] = float((nav_history[-1].get('nav', 0) / nav_history[0].get('nav', 1) - 1) * 100)
            metrics['volatility'] = self.calculate_volatility(portfolio_returns) * 100
            metrics['sharpe_ratio'] = self.calculate_sharpe_ratio(portfolio_returns)
            metrics['max_drawdown'] = self.calculate_max_drawdown(nav_history) * 100
        else:
            metrics.update(self._empty_metrics())
        
        # Benchmark comparisons
        if 'SOL' in benchmark_history and benchmark_history['SOL']:
            sol_returns = self.calculate_returns(benchmark_history['SOL'])
            if sol_returns and len(sol_returns) == len(portfolio_returns):
                metrics['beta_sol'] = self.calculate_beta(portfolio_returns, sol_returns)
                metrics['alpha_sol'] = self.calculate_alpha(portfolio_returns, sol_returns) * 100
                metrics['correlation_sol'] = float(np.corrcoef(portfolio_returns, sol_returns)[0][1]) if len(portfolio_returns) > 1 else 0.0
        
        # Rebalancing metrics
        if rebalance_history:
            metrics['total_rebalances'] = len(rebalance_history)
            metrics['total_rebalance_cost'] = sum(r.get('cost', 0) for r in rebalance_history)
            metrics['avg_rebalance_cost'] = metrics['total_rebalance_cost'] / len(rebalance_history)
        else:
            metrics['total_rebalances'] = 0
            metrics['total_rebalance_cost'] = 0.0
            metrics['avg_rebalance_cost'] = 0.0
        
        # Additional metrics
        if len(nav_history) >= 2:
            days = len(nav_history)
            if days > 1:
                annual_factor = 365 / days
                metrics['annualized_return'] = (pow(nav_history[-1].get('nav', 1) / nav_history[0].get('nav', 1), annual_factor) - 1) * 100
            else:
                metrics['annualized_return'] = 0.0
        
        return metrics
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'beta_sol': 1.0,
            'alpha_sol': 0.0,
            'correlation_sol': 0.0,
            'total_rebalances': 0,
            'total_rebalance_cost': 0.0,
            'avg_rebalance_cost': 0.0
        }
    
    def calculate_efficient_frontier(self, expected_returns: Dict[str, float], 
                                   covariance_matrix: Dict, 
                                   num_portfolios: int = 100) -> List[Dict]:
        """Calculate efficient frontier points"""
        tokens = list(expected_returns.keys())
        n_assets = len(tokens)
        
        if n_assets < 2:
            return []
        
        try:
            # Convert to numpy arrays
            mu = np.array([expected_returns[token] for token in tokens])
            
            # Build covariance matrix
            cov_matrix = np.zeros((n_assets, n_assets))
            for i, token1 in enumerate(tokens):
                for j, token2 in enumerate(tokens):
                    if token1 in covariance_matrix and token2 in covariance_matrix[token1]:
                        cov_matrix[i][j] = covariance_matrix[token1][token2]
                    else:
                        cov_matrix[i][j] = 1.0 if i == j else 0.0
            
            # Generate target returns
            min_return = np.min(mu)
            max_return = np.max(mu)
            target_returns = np.linspace(min_return, max_return, num_portfolios)
            
            efficient_portfolios = []
            
            for target in target_returns:
                # Simple equal weight for demonstration
                # In production, would solve quadratic optimization
                weights = np.ones(n_assets) / n_assets
                portfolio_return = np.dot(weights, mu)
                portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                
                efficient_portfolios.append({
                    'return': float(portfolio_return),
                    'volatility': float(portfolio_vol),
                    'sharpe': float(portfolio_return / portfolio_vol) if portfolio_vol > 0 else 0.0,
                    'weights': {tokens[i]: float(weights[i]) for i in range(n_assets)}
                })
            
            return efficient_portfolios
            
        except Exception as e:
            logging.error(f"Error calculating efficient frontier: {e}")
            return []
