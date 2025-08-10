"""
Tax-Lot Simulator for Educational Purposes Only
DISCLAIMER: This is for educational simulation only. Not financial or tax advice.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random

class TaxLotMethod(Enum):
    FIFO = "FIFO"  # First In, First Out
    LIFO = "LIFO"  # Last In, First Out
    HIFO = "HIFO"  # Highest Cost, First Out

@dataclass
class TaxLot:
    """Represents a tax lot (purchase) of a token"""
    token: str
    quantity: float
    cost_basis: float  # USD per token
    purchase_date: datetime
    lot_id: str

@dataclass
class Sale:
    """Represents a sale transaction"""
    token: str
    quantity: float
    sale_price: float  # USD per token
    sale_date: datetime
    lots_used: List[Tuple[TaxLot, float]]  # (lot, quantity_from_lot)

class TaxLotSimulator:
    """Educational tax lot simulator for portfolio management"""
    
    def __init__(self):
        self.lots: Dict[str, List[TaxLot]] = {}  # token -> list of lots
        self.sales: List[Sale] = []
        
    def add_purchase(self, token: str, quantity: float, cost_basis: float, 
                    purchase_date: Optional[datetime] = None) -> str:
        """Add a purchase (create a new tax lot)"""
        if purchase_date is None:
            purchase_date = datetime.now()
            
        lot_id = f"{token}_{purchase_date.strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}"
        
        lot = TaxLot(
            token=token,
            quantity=quantity,
            cost_basis=cost_basis,
            purchase_date=purchase_date,
            lot_id=lot_id
        )
        
        if token not in self.lots:
            self.lots[token] = []
        self.lots[token].append(lot)
        
        return lot_id
    
    def simulate_sale(self, token: str, quantity: float, sale_price: float,
                     method: TaxLotMethod = TaxLotMethod.FIFO,
                     sale_date: Optional[datetime] = None) -> Dict:
        """Simulate a sale and return tax implications"""
        if sale_date is None:
            sale_date = datetime.now()
            
        if token not in self.lots or not self.lots[token]:
            return {
                "success": False,
                "error": f"No lots available for {token}"
            }
        
        available_lots = [lot for lot in self.lots[token] if lot.quantity > 0]
        if not available_lots:
            return {
                "success": False,
                "error": f"No available quantity for {token}"
            }
        
        # Sort lots based on method
        if method == TaxLotMethod.FIFO:
            available_lots.sort(key=lambda x: x.purchase_date)
        elif method == TaxLotMethod.LIFO:
            available_lots.sort(key=lambda x: x.purchase_date, reverse=True)
        elif method == TaxLotMethod.HIFO:
            available_lots.sort(key=lambda x: x.cost_basis, reverse=True)
        
        # Execute sale
        remaining_quantity = quantity
        lots_used = []
        total_cost_basis = 0
        
        for lot in available_lots:
            if remaining_quantity <= 0:
                break
                
            quantity_from_lot = min(remaining_quantity, lot.quantity)
            lots_used.append((lot, quantity_from_lot))
            
            total_cost_basis += quantity_from_lot * lot.cost_basis
            remaining_quantity -= quantity_from_lot
            
            # Update lot quantity (for simulation only)
            lot.quantity -= quantity_from_lot
        
        if remaining_quantity > 0:
            return {
                "success": False,
                "error": f"Insufficient quantity. Need {quantity}, have {quantity - remaining_quantity}"
            }
        
        # Calculate gains/losses
        gross_proceeds = quantity * sale_price
        total_gain_loss = gross_proceeds - total_cost_basis
        
        # Categorize gains/losses by holding period
        short_term_gain = 0
        long_term_gain = 0
        
        for lot, qty_used in lots_used:
            holding_days = (sale_date - lot.purchase_date).days
            gain_loss = (sale_price - lot.cost_basis) * qty_used
            
            if holding_days > 365:  # Long-term
                long_term_gain += gain_loss
            else:  # Short-term
                short_term_gain += gain_loss
        
        sale = Sale(
            token=token,
            quantity=quantity,
            sale_price=sale_price,
            sale_date=sale_date,
            lots_used=lots_used
        )
        
        self.sales.append(sale)
        
        return {
            "success": True,
            "sale_summary": {
                "token": token,
                "quantity_sold": quantity,
                "sale_price": sale_price,
                "gross_proceeds": gross_proceeds,
                "total_cost_basis": total_cost_basis,
                "total_gain_loss": total_gain_loss,
                "short_term_gain": short_term_gain,
                "long_term_gain": long_term_gain,
                "method_used": method.value,
                "lots_used": len(lots_used)
            },
            "lot_details": [
                {
                    "lot_id": lot.lot_id,
                    "quantity_used": qty_used,
                    "cost_basis": lot.cost_basis,
                    "holding_days": (sale_date - lot.purchase_date).days,
                    "gain_loss": (sale_price - lot.cost_basis) * qty_used
                }
                for lot, qty_used in lots_used
            ]
        }
    
    def get_portfolio_status(self) -> Dict:
        """Get current portfolio status with unrealized gains/losses"""
        status = {}
        
        for token, lots in self.lots.items():
            active_lots = [lot for lot in lots if lot.quantity > 0]
            
            if not active_lots:
                continue
                
            total_quantity = sum(lot.quantity for lot in active_lots)
            total_cost_basis = sum(lot.quantity * lot.cost_basis for lot in active_lots)
            avg_cost_basis = total_cost_basis / total_quantity if total_quantity > 0 else 0
            
            status[token] = {
                "total_quantity": total_quantity,
                "total_cost_basis": total_cost_basis,
                "avg_cost_basis": avg_cost_basis,
                "num_lots": len(active_lots),
                "oldest_lot_date": min(lot.purchase_date for lot in active_lots).strftime('%Y-%m-%d'),
                "newest_lot_date": max(lot.purchase_date for lot in active_lots).strftime('%Y-%m-%d')
            }
        
        return status
    
    def generate_sample_lots(self, jupiter_api) -> None:
        """Generate sample tax lots for demonstration"""
        tokens = {
            'SOL': 'So11111111111111111111111111111111111111112',
            'mSOL': 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',
            'stSOL': '7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj',
            'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
        }
        
        base_date = datetime.now() - timedelta(days=365)
        
        for token, mint in tokens.items():
            current_price = jupiter_api.get_price(mint)
            
            # Create 3-5 sample lots over the past year
            for i in range(random.randint(3, 5)):
                days_ago = random.randint(30, 365)
                purchase_date = base_date + timedelta(days=days_ago)
                
                # Simulate price variations over time
                price_variation = random.uniform(0.7, 1.3)
                historical_price = current_price * price_variation
                
                quantity = random.uniform(0.5, 10) if token != 'BONK' else random.uniform(10000, 100000)
                
                self.add_purchase(token, quantity, historical_price, purchase_date)
                
        logging.info(f"Generated sample lots for {len(tokens)} tokens")
    
    def compare_methods(self, token: str, quantity: float, sale_price: float) -> Dict:
        """Compare tax implications across different lot selection methods"""
        results = {}
        
        # Save current state
        original_lots = {}
        for t, lots in self.lots.items():
            original_lots[t] = [TaxLot(lot.token, lot.quantity, lot.cost_basis, 
                                      lot.purchase_date, lot.lot_id) for lot in lots]
        
        for method in TaxLotMethod:
            # Restore original state
            self.lots = {}
            for t, lots in original_lots.items():
                self.lots[t] = [TaxLot(lot.token, lot.quantity, lot.cost_basis, 
                                      lot.purchase_date, lot.lot_id) for lot in lots]
            
            result = self.simulate_sale(token, quantity, sale_price, method)
            if result["success"]:
                results[method.value] = result["sale_summary"]
        
        # Restore final state
        self.lots = original_lots
        
        return results