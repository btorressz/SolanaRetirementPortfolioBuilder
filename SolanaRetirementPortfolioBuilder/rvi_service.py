import time
import threading
import logging
from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime, timedelta
import numpy as np
from jupiter_api import JupiterAPI

class RVIService:
    """Real-time Volatility Index service for monitoring market stability"""
    
    def __init__(self):
        self.jupiter_api = JupiterAPI()
        self.is_running = False
        self.thread = None
        self.sample_interval = 10  # seconds
        
        # Store price samples for each token
        self.price_history = {}
        self.max_samples = 360  # Keep 1 hour of data at 10s intervals
        
        # RVI calculations
        self.rvi_window = 30  # Use last 30 samples for RVI
        self.stability_threshold = 0.02  # 2% threshold for stability
        
        # Performance metrics
        self.last_update = None
        self.update_count = 0
        self.error_count = 0
        
    def start_sampling(self):
        """Start the background sampling thread"""
        if self.is_running:
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._sampling_loop, daemon=True)
        self.thread.start()
        logging.info("RVI Service started")
        
    def stop_sampling(self):
        """Stop the background sampling"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logging.info("RVI Service stopped")
        
    def _sampling_loop(self):
        """Main sampling loop running in background thread"""
        tokens = ['SOL', 'mSOL', 'stSOL', 'BONK', 'USDC']
        token_mints = {
            'SOL': 'So11111111111111111111111111111111111111112',
            'mSOL': 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',
            'stSOL': '7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj',
            'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
        }
        
        while self.is_running:
            try:
                timestamp = datetime.now()
                
                # Sample prices for all tokens
                for token in tokens:
                    mint = token_mints[token]
                    try:
                        price = self.jupiter_api.get_price(mint)
                        if price > 0:
                            self._add_sample(token, timestamp, price)
                    except Exception as e:
                        logging.error(f"Error sampling {token}: {e}")
                        self.error_count += 1
                
                self.last_update = timestamp
                self.update_count += 1
                
                # Sleep until next sample
                time.sleep(self.sample_interval)
                
            except Exception as e:
                logging.error(f"Error in RVI sampling loop: {e}")
                self.error_count += 1
                time.sleep(self.sample_interval)
    
    def _add_sample(self, token: str, timestamp: datetime, price: float):
        """Add a price sample for a token"""
        if token not in self.price_history:
            self.price_history[token] = deque(maxlen=self.max_samples)
        
        sample = {
            'timestamp': timestamp,
            'price': price
        }
        
        self.price_history[token].append(sample)
    
    def calculate_rvi(self, token: str) -> Optional[float]:
        """Calculate Realized Volatility Index for a token"""
        if token not in self.price_history:
            return None
            
        history = list(self.price_history[token])
        if len(history) < self.rvi_window:
            return None
        
        # Use last N samples
        recent_samples = history[-self.rvi_window:]
        prices = [s['price'] for s in recent_samples]
        
        if len(prices) < 2:
            return None
        
        # Calculate log returns
        log_returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0 and prices[i] > 0:
                log_return = np.log(prices[i] / prices[i-1])
                log_returns.append(log_return)
        
        if len(log_returns) < 2:
            return None
        
        # RVI = standard deviation of log returns * sqrt(samples per day)
        samples_per_day = (24 * 3600) / self.sample_interval
        volatility = np.std(log_returns) * np.sqrt(samples_per_day)
        
        return float(volatility)
    
    def calculate_stability_metrics(self, token: str) -> Dict:
        """Calculate stability metrics for a token"""
        if token not in self.price_history:
            return {}
            
        history = list(self.price_history[token])
        if len(history) < 10:
            return {}
        
        prices = [s['price'] for s in history[-30:]]  # Last 30 samples
        
        if len(prices) < 2:
            return {}
        
        # Price change metrics
        price_changes = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = (prices[i] - prices[i-1]) / prices[i-1]
                price_changes.append(abs(change))
        
        if not price_changes:
            return {}
        
        # Calculate metrics
        avg_price = np.mean(prices)
        max_change = max(price_changes)
        avg_change = np.mean(price_changes)
        volatility = np.std(price_changes)
        
        # Stability score (0-100, higher is more stable)
        stability_score = max(0, 100 - (volatility * 1000))
        
        return {
            'average_price': float(avg_price),
            'max_change': float(max_change),
            'average_change': float(avg_change),
            'volatility': float(volatility),
            'stability_score': float(stability_score),
            'is_stable': max_change < self.stability_threshold,
            'sample_count': len(prices)
        }
    
    def get_all_rvi(self) -> Dict[str, float]:
        """Get RVI for all tokens"""
        tokens = ['SOL', 'mSOL', 'stSOL', 'BONK', 'USDC']
        rvi_data = {}
        
        for token in tokens:
            rvi = self.calculate_rvi(token)
            if rvi is not None:
                rvi_data[token] = rvi
        
        return rvi_data
    
    def get_all_stability(self) -> Dict[str, Dict]:
        """Get stability metrics for all tokens"""
        tokens = ['SOL', 'mSOL', 'stSOL', 'BONK', 'USDC']
        stability_data = {}
        
        for token in tokens:
            metrics = self.calculate_stability_metrics(token)
            if metrics:
                stability_data[token] = metrics
        
        return stability_data
    
    def get_price_history(self, token: str, minutes: int = 60) -> List[Dict]:
        """Get price history for a token"""
        if token not in self.price_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        history = list(self.price_history[token])
        
        # Filter by time
        recent_history = [
            s for s in history 
            if s['timestamp'] >= cutoff_time
        ]
        
        return recent_history
    
    def get_service_stats(self) -> Dict:
        """Get service performance statistics"""
        return {
            'is_running': self.is_running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'update_count': self.update_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, self.update_count),
            'tokens_tracked': len(self.price_history),
            'total_samples': sum(len(hist) for hist in self.price_history.values()),
            'sample_interval': self.sample_interval
        }
    
    def detect_anomalies(self, token: str) -> List[Dict]:
        """Detect price anomalies for a token"""
        if token not in self.price_history:
            return []
            
        history = list(self.price_history[token])
        if len(history) < 10:
            return []
        
        prices = [s['price'] for s in history[-50:]]  # Check last 50 samples
        timestamps = [s['timestamp'] for s in history[-50:]]
        
        anomalies = []
        
        # Calculate rolling statistics
        window_size = min(10, len(prices) // 2)
        
        for i in range(window_size, len(prices)):
            # Use previous window for baseline
            baseline = prices[i-window_size:i]
            current_price = prices[i]
            
            baseline_mean = np.mean(baseline)
            baseline_std = np.std(baseline)
            
            # Z-score anomaly detection
            if baseline_std > 0:
                z_score = abs(current_price - baseline_mean) / baseline_std
                
                if z_score > 3:  # 3 sigma threshold
                    anomalies.append({
                        'timestamp': timestamps[i].isoformat(),
                        'price': current_price,
                        'baseline_mean': baseline_mean,
                        'z_score': float(z_score),
                        'severity': 'high' if z_score > 5 else 'medium'
                    })
        
        return anomalies

# Global RVI service instance
rvi_service = RVIService()