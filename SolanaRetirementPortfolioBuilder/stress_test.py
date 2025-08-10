"""
Scenario/Stress Lab for Portfolio Testing
Apply various market stress scenarios to test portfolio resilience
"""

import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class StressScenario:
    """Stress test scenario parameters"""
    name: str
    description: str
    price_shocks: Dict[str, float]  # token -> shock percentage
    volatility_multiplier: float
    correlation_shift: float
    duration_days: int

@dataclass
class StressResult:
    """Results from stress test"""
    scenario_name: str
    initial_nav: float
    final_nav: float
    total_return: float
    max_drawdown: float
    recovery_days: Optional[int]
    volatility: float
    nav_path: List[float]
    daily_returns: List[float]

class StressTestEngine:
    """Portfolio stress testing engine"""
    
    def __init__(self, jupiter_api):
        self.jupiter_api = jupiter_api
        
        # Predefined stress scenarios
        self.predefined_scenarios = {
            "crypto_crash": StressScenario(
                name="Crypto Crash",
                description="Major crypto market crash (-50% SOL, -40% alts)",
                price_shocks={"SOL": -50, "mSOL": -45, "stSOL": -45, "BONK": -70, "USDC": 0},
                volatility_multiplier=3.0,
                correlation_shift=0.2,
                duration_days=30
            ),
            "defi_hack": StressScenario(
                name="DeFi Protocol Hack",
                description="Staking protocol hack affecting liquid staking tokens",
                price_shocks={"SOL": -15, "mSOL": -35, "stSOL": -40, "BONK": -25, "USDC": 0},
                volatility_multiplier=2.0,
                correlation_shift=0.3,
                duration_days=14
            ),
            "meme_collapse": StressScenario(
                name="Meme Token Collapse",
                description="Complete meme token collapse with flight to quality",
                price_shocks={"SOL": 5, "mSOL": 8, "stSOL": 8, "BONK": -90, "USDC": 2},
                volatility_multiplier=2.5,
                correlation_shift=-0.4,
                duration_days=21
            ),
            "regulatory_crackdown": StressScenario(
                name="Regulatory Crackdown",
                description="Harsh regulatory actions against crypto",
                price_shocks={"SOL": -35, "mSOL": -40, "stSOL": -45, "BONK": -80, "USDC": -5},
                volatility_multiplier=2.0,
                correlation_shift=0.5,
                duration_days=45
            ),
            "liquidity_crisis": StressScenario(
                name="Liquidity Crisis",
                description="Market-wide liquidity shortage with high slippage",
                price_shocks={"SOL": -25, "mSOL": -30, "stSOL": -35, "BONK": -60, "USDC": 1},
                volatility_multiplier=4.0,
                correlation_shift=0.6,
                duration_days=7
            ),
            "black_swan": StressScenario(
                name="Black Swan Event",
                description="Unpredictable extreme market event",
                price_shocks={"SOL": -60, "mSOL": -65, "stSOL": -70, "BONK": -85, "USDC": -2},
                volatility_multiplier=5.0,
                correlation_shift=0.8,
                duration_days=60
            )
        }
    
    @property
    def stress_scenarios(self):
        """Backward compatibility property"""
        return self.predefined_scenarios
    
    def run_stress_test(self, portfolio: Dict[str, float], quotes: Dict[str, float], 
                       initial_value: float, scenario: StressScenario) -> Dict:
        """Run a specific stress test scenario"""
        result = self._simulate_stress_scenario(portfolio, scenario, initial_value, quotes)
        
        return {
            'scenario_name': result.scenario_name,
            'metrics': {
                'total_return': result.total_return,
                'max_drawdown': result.max_drawdown,
                'recovery_day': result.recovery_days,
                'volatility': result.volatility,
                'worst_nav': min(result.nav_path),
                'final_nav': result.final_nav
            },
            'recovery_path': [{'day': i, 'nav': nav} for i, nav in enumerate(result.nav_path[:30])],
            'rebalance_analysis': {
                'recommendation': 'Avoid rebalancing during extreme stress periods',
                'normal_cost': 0.1,
                'stressed_cost': 0.5,
                'cost_increase': 400,
                'liquidity_risk': 'High' if result.max_drawdown > 30 else 'Medium'
            }
        }
    
    def run_custom_stress_test(self, portfolio: Dict[str, float], quotes: Dict[str, float],
                              initial_value: float, price_shock_pct: float, 
                              slippage_multiplier: float = 2.0) -> Dict:
        """Run custom stress test with user-defined parameters"""
        # Apply shock to all tokens except USDC
        price_shocks = {}
        for token in portfolio.keys():
            if token == 'USDC':
                price_shocks[token] = 0
            else:
                price_shocks[token] = price_shock_pct
        
        scenario = StressScenario(
            name="Custom Stress Test",
            description=f"Custom scenario with {abs(price_shock_pct):.1f}% shock",
            price_shocks=price_shocks,
            volatility_multiplier=slippage_multiplier,
            correlation_shift=0.3,
            duration_days=30
        )
        
        result = self._simulate_stress_scenario(portfolio, scenario, initial_value, quotes)
        
        return {
            'scenario_name': result.scenario_name,
            'metrics': {
                'total_return': result.total_return,
                'max_drawdown': result.max_drawdown,
                'recovery_day': result.recovery_days,
                'volatility': result.volatility,
                'worst_nav': min(result.nav_path),
                'final_nav': result.final_nav
            },
            'recovery_path': [{'day': i, 'nav': nav} for i, nav in enumerate(result.nav_path[:30])],
            'rebalance_analysis': {
                'recommendation': 'Custom stress test - monitor closely',
                'normal_cost': 0.1,
                'stressed_cost': 0.3 * slippage_multiplier,
                'cost_increase': 200 * slippage_multiplier,
                'liquidity_risk': 'High' if abs(price_shock_pct) > 30 else 'Medium'
            }
        }
    
    def _simulate_stress_scenario(self, portfolio: Dict[str, float], 
                                 scenario: StressScenario, 
                                 initial_value: float,
                                 quotes: Dict[str, float]) -> StressResult:
        """Simulate a stress scenario"""
        
        # Use provided quotes
        current_prices = quotes
        
        # Initialize simulation
        nav_path = [initial_value]
        daily_returns = []
        
        # Calculate token allocations
        token_values = {}
        for token, weight in portfolio.items():
            if token in current_prices:
                token_values[token] = (weight / 100) * initial_value
        
        # Generate stress path
        np.random.seed(42)  # Reproducible results
        
        for day in range(scenario.duration_days):
            day_nav = 0
            day_return = 0
            
            for token, initial_token_value in token_values.items():
                if token not in current_prices or current_prices[token] <= 0:
                    continue
                
                # Apply price shock (gradually over first week, then stabilize)
                shock_factor = min(1.0, day / 7) if day < 7 else 1.0
                price_shock = scenario.price_shocks.get(token, 0) * shock_factor / 100
                
                # Add ongoing volatility
                base_vol = self._get_base_volatility(token)
                daily_vol = base_vol * scenario.volatility_multiplier
                random_shock = np.random.normal(0, daily_vol)
                
                # Combine effects
                total_return = price_shock if day == 0 else random_shock
                
                # Update token value
                if day == 0:
                    token_nav = initial_token_value * (1 + total_return)
                else:
                    prev_token_value = token_values[token]
                    token_nav = prev_token_value * (1 + total_return)
                
                token_values[token] = token_nav
                day_nav += token_nav
                
                # Track return contribution
                day_return += (portfolio[token] / 100) * total_return
            
            nav_path.append(day_nav)
            daily_returns.append(day_return)
        
        # Calculate metrics
        final_nav = nav_path[-1]
        total_return = ((final_nav / initial_value) - 1) * 100
        
        # Max drawdown
        peak = np.maximum.accumulate(nav_path)
        drawdown = (np.array(nav_path) - peak) / peak
        max_drawdown = abs(np.min(drawdown)) * 100
        
        # Recovery time
        recovery_days = self._calculate_recovery_time(nav_path, initial_value)
        
        # Volatility
        volatility = np.std(daily_returns) * np.sqrt(252) * 100 if len(daily_returns) > 0 else 0
        
        return StressResult(
            scenario_name=scenario.name,
            initial_nav=initial_value,
            final_nav=final_nav,
            total_return=total_return,
            max_drawdown=max_drawdown,
            recovery_days=recovery_days,
            volatility=volatility,
            nav_path=nav_path,
            daily_returns=daily_returns
        )
    
    def _get_base_volatility(self, token: str) -> float:
        """Get base daily volatility for token"""
        volatilities = {
            "SOL": 0.04,
            "mSOL": 0.035,
            "stSOL": 0.035,
            "BONK": 0.08,
            "USDC": 0.002
        }
        return volatilities.get(token, 0.04)
    
    def _calculate_recovery_time(self, nav_path: List[float], initial_value: float) -> Optional[int]:
        """Calculate days to recover to initial value"""
        min_idx = np.argmin(nav_path)
        
        for i in range(min_idx, len(nav_path)):
            if nav_path[i] >= initial_value:
                return int(i - min_idx)
        
        return None  # Didn't recover
    
    def run_comprehensive_stress_suite(self, portfolio: Dict[str, float], 
                                     initial_value: float = 10000.0) -> Dict:
        """Run all predefined stress scenarios"""
        results = {}
        
        for scenario_name in self.stress_scenarios.keys():
            try:
                result = self.run_stress_test(portfolio, scenario_name, initial_value)
                results[scenario_name] = {
                    "name": result.scenario_name,
                    "description": self.stress_scenarios[scenario_name].description,
                    "total_return": result.total_return,
                    "max_drawdown": result.max_drawdown,
                    "recovery_days": result.recovery_days,
                    "volatility": result.volatility,
                    "final_nav": result.final_nav,
                    "nav_path": result.nav_path[:10],  # First 10 days for preview
                    "severity": self._classify_severity(result)
                }
            except Exception as e:
                logging.error(f"Error running stress test {scenario_name}: {e}")
                results[scenario_name] = {
                    "name": self.stress_scenarios[scenario_name].name,
                    "error": str(e)
                }
        
        return {
            "success": True,
            "portfolio": portfolio,
            "initial_value": initial_value,
            "scenarios": results,
            "summary": self._generate_stress_summary(results)
        }
    
    def _classify_severity(self, result: StressResult) -> str:
        """Classify stress test severity"""
        if result.max_drawdown < 10:
            return "Low"
        elif result.max_drawdown < 25:
            return "Moderate" 
        elif result.max_drawdown < 50:
            return "High"
        else:
            return "Severe"
    
    def _generate_stress_summary(self, results: Dict) -> Dict:
        """Generate summary of stress test results"""
        valid_results = [r for r in results.values() if "error" not in r]
        
        if not valid_results:
            return {"error": "No valid stress test results"}
        
        avg_drawdown = np.mean([r["max_drawdown"] for r in valid_results])
        max_drawdown = float(max([r["max_drawdown"] for r in valid_results]))
        avg_return = np.mean([r["total_return"] for r in valid_results])
        
        recovery_times = [r["recovery_days"] for r in valid_results if r["recovery_days"] is not None]
        avg_recovery = np.mean(recovery_times) if recovery_times else None
        
        severity_counts = {}
        for result in valid_results:
            severity = result.get("severity", "Unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "avg_max_drawdown": avg_drawdown,
            "worst_case_drawdown": max_drawdown,
            "avg_total_return": avg_return,
            "avg_recovery_days": avg_recovery,
            "severity_distribution": severity_counts,
            "scenarios_passed": len(valid_results),
            "total_scenarios": len(results),
            "resilience_score": max(0.0, 100 - avg_drawdown * 2)  # Simple resilience metric
        }
    
    def get_scenario_library(self) -> List[Dict]:
        """Get available stress test scenarios for frontend display"""
        scenarios = []
        
        severity_map = {
            'crypto_crash': 'Severe',
            'defi_hack': 'High', 
            'meme_collapse': 'Medium',
            'regulatory_crackdown': 'Severe',
            'liquidity_crisis': 'High',
            'black_swan': 'Extreme'
        }
        
        for scenario_id, scenario in self.predefined_scenarios.items():
            scenarios.append({
                'id': scenario_id,
                'name': scenario.name,
                'description': scenario.description,
                'severity': severity_map.get(scenario_id, 'Medium'),
                'duration_days': scenario.duration_days,
                'recovery_days': 'Variable'  # Will be calculated during simulation
            })
        
        return scenarios