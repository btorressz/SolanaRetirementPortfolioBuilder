import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

class RebalanceMode(Enum):
    THRESHOLD = "threshold"
    CALENDAR = "calendar"
    COST_AWARE = "cost_aware"
    HYBRID = "hybrid"

class SmartRebalanceEngine:
    """Advanced rebalancing engine with multiple smart modes"""
    
    def __init__(self):
        self.default_threshold = 5.0  # 5% drift threshold
        self.calendar_intervals = {
            'daily': 1,
            'weekly': 7, 
            'monthly': 30,
            'quarterly': 90
        }
        self.cost_threshold_pct = 0.5  # 0.5% of portfolio value
        
    def should_rebalance(self, 
                        mode: RebalanceMode,
                        current_weights: Dict[str, float],
                        target_weights: Dict[str, float],
                        portfolio_value: float,
                        estimated_cost: float,
                        last_rebalance: Optional[datetime] = None,
                        **kwargs) -> Dict:
        """
        Determine if portfolio should be rebalanced based on selected mode
        
        Returns:
            Dict with 'should_rebalance', 'reason', 'savings', and 'next_check'
        """
        
        if mode == RebalanceMode.THRESHOLD:
            return self._threshold_check(current_weights, target_weights, **kwargs)
            
        elif mode == RebalanceMode.CALENDAR:
            return self._calendar_check(last_rebalance, **kwargs)
            
        elif mode == RebalanceMode.COST_AWARE:
            return self._cost_aware_check(
                current_weights, target_weights, 
                portfolio_value, estimated_cost, **kwargs
            )
            
        elif mode == RebalanceMode.HYBRID:
            return self._hybrid_check(
                current_weights, target_weights, 
                portfolio_value, estimated_cost, 
                last_rebalance, **kwargs
            )
        
        return {
            'should_rebalance': False,
            'reason': 'Unknown mode',
            'savings': 0.0,
            'next_check': None
        }
    
    def _threshold_check(self, current_weights: Dict[str, float], 
                        target_weights: Dict[str, float], 
                        threshold: Optional[float] = None) -> Dict:
        """Check if any weight has drifted beyond threshold"""
        
        threshold = threshold or self.default_threshold
        max_drift = 0.0
        drifted_tokens = []
        
        for token, target in target_weights.items():
            current = current_weights.get(token, 0.0)
            drift = abs(current - target)
            
            if drift > threshold:
                drifted_tokens.append({
                    'token': token,
                    'drift': drift,
                    'current': current,
                    'target': target
                })
            
            max_drift = max(max_drift, drift)
        
        should_rebalance = len(drifted_tokens) > 0
        
        if should_rebalance:
            reason = f"Drift threshold exceeded: {max_drift:.2f}% > {threshold}%"
            savings = 0.0  # No savings for threshold mode
        else:
            reason = f"All weights within {threshold}% threshold"
            # Calculate potential savings by waiting
            savings = self._estimate_waiting_savings(max_drift, threshold)
        
        return {
            'should_rebalance': should_rebalance,
            'reason': reason,
            'savings': savings,
            'next_check': None,
            'max_drift': max_drift,
            'drifted_tokens': drifted_tokens
        }
    
    def _calendar_check(self, last_rebalance: Optional[datetime], 
                       interval: str = 'monthly') -> Dict:
        """Check if it's time for scheduled rebalance"""
        
        if last_rebalance is None:
            return {
                'should_rebalance': True,
                'reason': 'No previous rebalance recorded',
                'savings': 0.0,
                'next_check': None
            }
        
        interval_days = self.calendar_intervals.get(interval, 30)
        next_rebalance = last_rebalance + timedelta(days=interval_days)
        now = datetime.now()
        
        should_rebalance = now >= next_rebalance
        days_until_next = (next_rebalance - now).days if not should_rebalance else 0
        
        if should_rebalance:
            reason = f"Scheduled {interval} rebalance due"
            savings = 0.0
        else:
            reason = f"Next {interval} rebalance in {days_until_next} days"
            savings = self._estimate_calendar_savings(days_until_next)
        
        return {
            'should_rebalance': should_rebalance,
            'reason': reason,
            'savings': savings,
            'next_check': next_rebalance,
            'days_until_next': days_until_next
        }
    
    def _cost_aware_check(self, current_weights: Dict[str, float],
                         target_weights: Dict[str, float],
                         portfolio_value: float,
                         estimated_cost: float,
                         cost_threshold_pct: Optional[float] = None) -> Dict:
        """Check if rebalancing cost is justified by drift"""
        
        cost_threshold_pct = cost_threshold_pct or self.cost_threshold_pct
        cost_threshold = portfolio_value * (cost_threshold_pct / 100)
        
        # Calculate drift severity
        total_drift = 0.0
        max_drift = 0.0
        
        for token, target in target_weights.items():
            current = current_weights.get(token, 0.0)
            drift = abs(current - target)
            total_drift += drift
            max_drift = max(max_drift, drift)
        
        # Cost-benefit analysis
        drift_score = (total_drift + max_drift * 2) / 3  # Weighted drift score
        cost_ratio = estimated_cost / portfolio_value * 100
        
        # Simple heuristic: rebalance if drift > cost ratio * multiplier
        cost_justified = drift_score > (cost_ratio * 2)
        cost_reasonable = estimated_cost <= cost_threshold
        
        should_rebalance = cost_justified and cost_reasonable
        
        if should_rebalance:
            reason = f"Cost justified: {drift_score:.2f}% drift vs {cost_ratio:.3f}% cost"
            savings = 0.0
        else:
            if not cost_justified:
                reason = f"Cost not justified: {drift_score:.2f}% drift vs {cost_ratio:.3f}% cost"
            else:
                reason = f"Cost too high: ${estimated_cost:.2f} > ${cost_threshold:.2f}"
            
            # Savings by avoiding premature rebalance
            savings = estimated_cost if not cost_justified else 0.0
        
        return {
            'should_rebalance': should_rebalance,
            'reason': reason,
            'savings': savings,
            'next_check': None,
            'drift_score': drift_score,
            'cost_ratio': cost_ratio,
            'cost_justified': cost_justified,
            'cost_reasonable': cost_reasonable
        }
    
    def _hybrid_check(self, current_weights: Dict[str, float],
                     target_weights: Dict[str, float],
                     portfolio_value: float,
                     estimated_cost: float,
                     last_rebalance: Optional[datetime],
                     threshold: Optional[float] = None,
                     interval: str = 'monthly',
                     cost_threshold_pct: Optional[float] = None) -> Dict:
        """Hybrid mode combining threshold, calendar, and cost-aware logic"""
        
        # Run all checks
        threshold_result = self._threshold_check(current_weights, target_weights, threshold)
        calendar_result = self._calendar_check(last_rebalance, interval)
        cost_result = self._cost_aware_check(
            current_weights, target_weights, 
            portfolio_value, estimated_cost, cost_threshold_pct
        )
        
        # Hybrid decision logic
        threshold_breach = threshold_result['should_rebalance']
        calendar_due = calendar_result['should_rebalance']
        cost_justified = cost_result['should_rebalance']
        
        # Priority: 1) Calendar due, 2) Threshold + Cost justified, 3) Emergency threshold
        emergency_threshold = (threshold or self.default_threshold) * 2
        emergency_breach = threshold_result.get('max_drift', 0) > emergency_threshold
        
        if calendar_due and cost_justified:
            should_rebalance = True
            reason = "Scheduled rebalance due and cost justified"
            savings = 0.0
        elif threshold_breach and cost_justified:
            should_rebalance = True
            reason = "Threshold breach and cost justified"
            savings = 0.0
        elif emergency_breach:
            should_rebalance = True
            reason = f"Emergency rebalance: {threshold_result.get('max_drift', 0):.2f}% drift"
            savings = 0.0
        else:
            should_rebalance = False
            # Determine primary reason for waiting
            if not cost_justified:
                reason = f"Waiting: {cost_result['reason']}"
                savings = cost_result['savings']
            elif not calendar_due:
                reason = f"Waiting: {calendar_result['reason']}"
                savings = calendar_result['savings']
            else:
                reason = f"Waiting: {threshold_result['reason']}"
                savings = threshold_result['savings']
        
        return {
            'should_rebalance': should_rebalance,
            'reason': reason,
            'savings': savings,
            'next_check': calendar_result.get('next_check'),
            'threshold_result': threshold_result,
            'calendar_result': calendar_result,
            'cost_result': cost_result,
            'emergency_breach': emergency_breach
        }
    
    def _estimate_waiting_savings(self, current_drift: float, threshold: float) -> float:
        """Estimate savings by waiting until threshold is reached"""
        if current_drift >= threshold:
            return 0.0
        
        # Simple heuristic: estimate cost savings based on drift remaining
        remaining_drift = threshold - current_drift
        savings_factor = remaining_drift / threshold
        
        # Assume average rebalance cost of $50 and scale by savings factor
        estimated_savings = 50.0 * savings_factor
        return max(0.0, estimated_savings)
    
    def _estimate_calendar_savings(self, days_until_next: int) -> float:
        """Estimate savings by waiting for calendar rebalance"""
        if days_until_next <= 0:
            return 0.0
        
        # Assume each premature rebalance costs extra due to frequency
        # Savings scale with time remaining
        max_savings = 25.0  # Base savings for waiting
        time_factor = min(1.0, days_until_next / 30.0)  # Scale by month
        
        return max_savings * time_factor
    
    def get_rebalance_modes(self) -> List[Dict]:
        """Get available rebalance modes with descriptions"""
        return [
            {
                'mode': RebalanceMode.THRESHOLD.value,
                'name': 'Threshold-Based',
                'description': 'Rebalance when any weight drifts beyond set threshold',
                'parameters': ['threshold'],
                'pros': ['Responsive to market moves', 'Maintains target allocation'],
                'cons': ['May rebalance frequently', 'Ignores transaction costs']
            },
            {
                'mode': RebalanceMode.CALENDAR.value,
                'name': 'Calendar-Based', 
                'description': 'Rebalance on fixed schedule (daily/weekly/monthly/quarterly)',
                'parameters': ['interval'],
                'pros': ['Predictable timing', 'Lower transaction frequency'],
                'cons': ['May miss optimal timing', 'Ignores market conditions']
            },
            {
                'mode': RebalanceMode.COST_AWARE.value,
                'name': 'Cost-Aware',
                'description': 'Rebalance only when benefits outweigh transaction costs',
                'parameters': ['cost_threshold_pct'],
                'pros': ['Maximizes net returns', 'Avoids costly small adjustments'],
                'cons': ['May allow significant drift', 'Complex optimization']
            },
            {
                'mode': RebalanceMode.HYBRID.value,
                'name': 'Hybrid Smart',
                'description': 'Combines threshold, calendar, and cost-aware logic',
                'parameters': ['threshold', 'interval', 'cost_threshold_pct'],
                'pros': ['Best of all approaches', 'Adapts to conditions'],
                'cons': ['More complex', 'Requires tuning']
            }
        ]
    
    def calculate_rebalance_savings(self, 
                                   rebalance_history: List[Dict],
                                   mode: RebalanceMode,
                                   **settings) -> Dict:
        """Calculate total savings from smart rebalancing vs naive approach"""
        
        if not rebalance_history:
            return {
                'total_savings': 0.0,
                'rebalances_avoided': 0,
                'cost_reduction': 0.0,
                'efficiency_gain': 0.0
            }
        
        # Simulate what would have happened with different modes
        naive_cost = len(rebalance_history) * 50.0  # Assume $50 average cost
        smart_cost = sum(r.get('cost', 0) for r in rebalance_history)
        
        total_savings = naive_cost - smart_cost
        rebalances_avoided = max(0, len(rebalance_history) // 2)  # Rough estimate
        cost_reduction = total_savings / max(1, naive_cost) * 100
        efficiency_gain = total_savings / len(rebalance_history) if rebalance_history else 0
        
        return {
            'total_savings': total_savings,
            'rebalances_avoided': rebalances_avoided,
            'cost_reduction': cost_reduction,
            'efficiency_gain': efficiency_gain,
            'naive_cost': naive_cost,
            'smart_cost': smart_cost
        }