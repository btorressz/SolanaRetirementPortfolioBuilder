"""
Live Pricing Service with Jupiter API Primary + CoinGecko Fallback
Background polling every 10 seconds with intelligent retry logic
"""
import threading
import time
import logging
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
import json

class LivePricingService:
    """Background service for continuous live price updates"""
    
    def __init__(self):
        self.prices = {}
        self.last_update = {}
        self.is_running = False
        self.polling_thread = None
        self.update_interval = 10  # 10 seconds
        
        # Rate limiting and retry logic
        self.jupiter_rate_limit_reset = 0
        self.coingecko_rate_limit_reset = 0
        self.retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff
        
        # API endpoints
        self.jupiter_url = "https://price.jup.ag/v4/price"
        self.coingecko_url = "https://api.coingecko.com/api/v3/simple/price"
        
        # Token mappings
        self.tokens = {
            'SOL': {
                'jupiter_id': 'So11111111111111111111111111111111111111112',
                'coingecko_id': 'solana',
                'kraken_pair': 'SOLUSD'
            },
            'mSOL': {
                'jupiter_id': 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',
                'coingecko_id': 'marinade-staked-sol',
                'kraken_pair': None
            },
            'stSOL': {
                'jupiter_id': '7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj',
                'coingecko_id': 'lido-staked-sol',
                'kraken_pair': None
            },
            'BONK': {
                'jupiter_id': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
                'coingecko_id': 'bonk',
                'kraken_pair': None
            },
            'USDC': {
                'jupiter_id': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'coingecko_id': 'usd-coin',
                'kraken_pair': 'USDCUSD'
            },
            'USDT': {
                'jupiter_id': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',
                'coingecko_id': 'tether',
                'kraken_pair': 'USDTUSD'
            }
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Solana-Portfolio-Builder/2.0'
        })
        
    def start_polling(self):
        """Start background polling for live prices"""
        if self.is_running:
            return
            
        self.is_running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        logging.info("🚀 Live pricing service started with 10s polling")
        
    def stop_polling(self):
        """Stop background polling"""
        self.is_running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2)
        logging.info("🛑 Live pricing service stopped")
        
    def _polling_loop(self):
        """Main polling loop with intelligent retry logic"""
        while self.is_running:
            try:
                self._update_all_prices()
                time.sleep(self.update_interval)
            except Exception as e:
                logging.error(f"Polling error: {e}")
                time.sleep(5)  # Short delay on error
                
    def _update_all_prices(self):
        """Update all token prices with fallback chain"""
        updated_count = 0
        
        # Try Jupiter API first (batch request for efficiency)
        jupiter_prices = self._fetch_jupiter_batch()
        if jupiter_prices:
            for token, price in jupiter_prices.items():
                if price > 0:
                    self.prices[token] = price
                    self.last_update[token] = time.time()
                    updated_count += 1
                    
        # For tokens not updated by Jupiter, try ALL available sources
        missing_tokens = [token for token in self.tokens.keys() 
                         if token not in jupiter_prices or jupiter_prices.get(token, 0) <= 0]
        
        for token in missing_tokens:
            # Try Kraken first for supported tokens (faster & more reliable)
            kraken_price = self._fetch_kraken_price(token)
            if kraken_price > 0:
                self.prices[token] = kraken_price
                self.last_update[token] = time.time()
                updated_count += 1
                continue
                
            # Then try CoinGecko with multiple strategies
            price = self._fetch_coingecko_price(token)
            if price > 0:
                self.prices[token] = price
                self.last_update[token] = time.time()
                updated_count += 1
                continue
                
            # If still no price, try alternative data sources
            alt_price = self._fetch_alternative_price(token)
            if alt_price > 0:
                self.prices[token] = alt_price
                self.last_update[token] = time.time()
                updated_count += 1
                    
        if updated_count > 0:
            logging.info(f"📈 Updated {updated_count}/{len(self.tokens)} live prices")
            
    def _fetch_jupiter_batch(self) -> Dict[str, float]:
        """Fetch all prices from Jupiter API in one batch request"""
        if time.time() < self.jupiter_rate_limit_reset:
            return {}
            
        try:
            # Build batch request with all Jupiter IDs
            jupiter_ids = [info['jupiter_id'] for info in self.tokens.values()]
            ids_param = ','.join(jupiter_ids)
            
            response = self.session.get(
                self.jupiter_url,
                params={'ids': ids_param},
                timeout=8
            )
            
            if response.status_code == 429:
                # Rate limited - set backoff
                self.jupiter_rate_limit_reset = time.time() + 60
                logging.warning("⏱️ Jupiter API rate limited, waiting 60s")
                return {}
                
            response.raise_for_status()
            data = response.json()
            
            # Map Jupiter response back to token symbols
            prices = {}
            if 'data' in data:
                for token, info in self.tokens.items():
                    jupiter_id = info['jupiter_id']
                    if jupiter_id in data['data']:
                        price = float(data['data'][jupiter_id]['price'])
                        prices[token] = price
                        logging.debug(f"🟢 Jupiter: {token} = ${price:.6f}")
                        
            return prices
            
        except Exception as e:
            logging.warning(f"Jupiter batch fetch failed: {e}")
            return {}
            
    def _fetch_coingecko_price(self, token: str) -> float:
        """Fetch individual token price from CoinGecko with retry logic"""
        if time.time() < self.coingecko_rate_limit_reset:
            return 0.0
            
        token_info = self.tokens.get(token)
        if not token_info or not token_info['coingecko_id']:
            return 0.0
            
        # Try multiple CoinGecko strategies
        strategies = [
            # Strategy 1: Standard API
            {
                'url': self.coingecko_url,
                'params': {
                    'ids': token_info['coingecko_id'],
                    'vs_currencies': 'usd',
                    'include_24hr_change': 'false'
                }
            },
            # Strategy 2: Pro API endpoint (sometimes less rate-limited)
            {
                'url': "https://pro-api.coingecko.com/api/v3/simple/price",
                'params': {
                    'ids': token_info['coingecko_id'],
                    'vs_currencies': 'usd'
                }
            }
        ]
        
        for strategy in strategies:
            try:
                response = self.session.get(
                    strategy['url'],
                    params=strategy['params'],
                    timeout=6
                )
                
                if response.status_code == 429:
                    continue  # Try next strategy
                    
                response.raise_for_status()
                data = response.json()
                
                coingecko_id = token_info['coingecko_id']
                if coingecko_id in data and 'usd' in data[coingecko_id]:
                    price = float(data[coingecko_id]['usd'])
                    logging.info(f"🟡 CoinGecko: {token} = ${price:.6f}")
                    return price
                    
            except Exception as e:
                logging.debug(f"CoinGecko strategy failed for {token}: {e}")
                continue
        
        # All strategies failed - set rate limit if 429
        self.coingecko_rate_limit_reset = time.time() + 30  # Shorter backoff
        logging.warning(f"⏱️ CoinGecko all strategies failed for {token}")
        return 0.0
        
    def _fetch_kraken_price(self, token: str) -> float:
        """Fetch price from Kraken as final fallback"""
        token_info = self.tokens.get(token)
        if not token_info or not token_info['kraken_pair']:
            return 0.0
            
        try:
            response = self.session.get(
                "https://api.kraken.com/0/public/Ticker",
                params={'pair': token_info['kraken_pair']},
                timeout=8
            )
            response.raise_for_status()
            
            data = response.json()
            pair = token_info['kraken_pair']
            if 'result' in data and pair in data['result']:
                price = float(data['result'][pair]['c'][0])
                logging.info(f"🔵 Kraken: {token} = ${price:.6f}")
                return price
                
        except Exception as e:
            logging.warning(f"Kraken {token} fetch failed: {e}")
            
        return 0.0
        
    def _fetch_alternative_price(self, token: str) -> float:
        """Try alternative data sources for missing tokens"""
        # For Solana ecosystem tokens, try DexScreener API as backup
        token_info = self.tokens.get(token)
        if not token_info:
            return 0.0
            
        try:
            # DexScreener has good Solana coverage
            response = self.session.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_info['jupiter_id']}",
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            if 'pairs' in data and data['pairs']:
                # Find best liquidity pair
                best_pair = max(data['pairs'], key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))
                if 'priceUsd' in best_pair:
                    price = float(best_pair['priceUsd'])
                    logging.info(f"🟠 DexScreener: {token} = ${price:.6f}")
                    return price
                    
        except Exception as e:
            logging.debug(f"DexScreener {token} fetch failed: {e}")
            
        return 0.0
        
    def get_live_prices(self) -> Dict[str, float]:
        """Get current live prices"""
        return self.prices.copy()
        
    def get_price(self, token: str) -> float:
        """Get individual token price"""
        return self.prices.get(token, 0.0)
        
    def is_price_fresh(self, token: str, max_age_seconds: int = 30) -> bool:
        """Check if price is fresh (updated within max_age_seconds)"""
        last_update = self.last_update.get(token, 0)
        return (time.time() - last_update) <= max_age_seconds
        
    def get_status(self) -> Dict:
        """Get service status for monitoring"""
        now = time.time()
        fresh_count = sum(1 for token in self.tokens.keys() 
                         if self.is_price_fresh(token, 30))
        
        return {
            'running': self.is_running,
            'total_tokens': len(self.tokens),
            'fresh_prices': fresh_count,
            'last_updates': {token: now - ts for token, ts in self.last_update.items()},
            'jupiter_rate_limited': now < self.jupiter_rate_limit_reset,
            'coingecko_rate_limited': now < self.coingecko_rate_limit_reset
        }

# Global instance
live_pricing = LivePricingService()