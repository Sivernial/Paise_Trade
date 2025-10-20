"""
Enhanced Trading Engine with Paper Trading, Live Trading, and Order Management
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
import logging
import time
from kiteconnect import KiteConnect

# Import dataclasses from data_structures
from data_structures.trading_dataclass import (
    Order, OrderType, OrderStatus, TransactionType, ProductType
)

class TradingEngine:
    """
    Enhanced trading engine supporting both paper and live trading
    
    Features:
    - Paper trading simulation
    - Live trading with Zerodha Kite
    - Order management and tracking
    - Risk controls
    - Transaction logging
    """
    
    def __init__(self, 
                 kite: Optional[KiteConnect] = None,
                 paper_trading: bool = True,
                 initial_capital: float = 100000,
                 max_orders_per_day: int = 100):
        
        self.kite = kite
        self.paper_trading = paper_trading
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_orders_per_day = max_orders_per_day
        
        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.daily_order_count = 0
        self.last_order_date = datetime.now().date()
        
        # Paper trading state
        self.paper_positions: Dict[str, Dict] = {}
        self.paper_trades: List[Dict] = []
        
        # Risk controls
        self.max_position_value = initial_capital * 0.2  # Max 20% per position
        self.max_loss_per_day = initial_capital * 0.05   # Max 5% loss per day
        self.daily_pnl = 0.0
        
        # Setup logging
        self.logger = logging.getLogger('TradingEngine')
        
        # Current market prices (for paper trading)
        self.current_prices: Dict[str, float] = {}
    
    def update_market_prices(self, prices: Dict[str, float]):
        """Update current market prices for paper trading"""
        self.current_prices.update(prices)
    
    def place_order(self, 
                   symbol: str,
                   exchange: str,
                   transaction_type: TransactionType,
                   quantity: int,
                   order_type: OrderType = OrderType.MARKET,
                   price: float = 0.0,
                   product_type: ProductType = ProductType.MIS,
                   tag: str = "") -> Optional[str]:
        """
        Place a trading order
        
        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE, BSE, etc.)
            transaction_type: BUY or SELL
            quantity: Number of shares
            order_type: Market, limit, stop loss, etc.
            price: Price for limit orders
            product_type: CNC, MIS, NRML
            tag: Optional tag for tracking
            
        Returns:
            Order ID if successful, None otherwise
        """
        
        # Reset daily counter if new day
        today = datetime.now().date()
        if today > self.last_order_date:
            self.daily_order_count = 0
            self.last_order_date = today
            self.daily_pnl = 0.0
        
        # Risk checks
        if not self._pre_order_risk_checks(symbol, transaction_type, quantity, price):
            return None
        
        # Create order
        order = Order(
            symbol=symbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            order_type=order_type,
            product_type=product_type,
            tag=tag
        )
        
        if self.paper_trading:
            return self._place_paper_order(order)
        else:
            return self._place_live_order(order)
    
    def _pre_order_risk_checks(self, symbol: str, transaction_type: TransactionType, 
                              quantity: int, price: float) -> bool:
        """Perform pre-order risk checks"""
        
        # Check daily order limit
        if self.daily_order_count >= self.max_orders_per_day:
            self.logger.warning("Daily order limit reached")
            return False
        
        # Check daily loss limit
        if self.daily_pnl <= -self.max_loss_per_day:
            self.logger.warning("Daily loss limit reached")
            return False
        
        # Check position size for buys
        if transaction_type == TransactionType.BUY:
            current_price = price if price > 0 else self.current_prices.get(symbol, 0)
            position_value = quantity * current_price
            
            if position_value > self.max_position_value:
                self.logger.warning(f"Position size too large: ${position_value:.2f}")
                return False
            
            if position_value > self.current_capital:
                self.logger.warning(f"Insufficient capital: ${position_value:.2f} required, ${self.current_capital:.2f} available")
                return False
        
        return True
    
    def _place_paper_order(self, order: Order) -> str:
        """Execute paper trading order"""
        
        # Generate order ID
        order_id = f"PAPER_{int(time.time())}_{len(self.orders)}"
        order.order_id = order_id
        
        # Get execution price
        if order.order_type == OrderType.MARKET:
            if order.symbol in self.current_prices:
                execution_price = self.current_prices[order.symbol]
                # Add slippage for market orders
                if order.transaction_type == TransactionType.BUY:
                    execution_price *= 1.001  # 0.1% slippage
                else:
                    execution_price *= 0.999
            else:
                execution_price = order.price
        else:
            execution_price = order.price
        
        # Execute the order
        order.status = OrderStatus.COMPLETE
        order.filled_quantity = order.quantity
        order.average_price = execution_price
        order.update_timestamp = datetime.now()
        
        # Update paper trading state
        self._update_paper_position(order)
        
        # Store order
        self.orders[order_id] = order
        self.order_history.append(order)
        self.daily_order_count += 1
        
        self.logger.info(f"Paper order executed: {order.transaction_type.value} {order.quantity} {order.symbol} @ ${execution_price:.2f}")
        
        return order_id
    
    def _place_live_order(self, order: Order) -> Optional[str]:
        """Execute live trading order via Zerodha Kite"""
        
        if not self.kite:
            self.logger.error("No Kite connection for live trading")
            return None
        
        try:
            # Map our enums to Kite API format
            kite_transaction_type = order.transaction_type.value
            kite_order_type = order.order_type.value
            kite_product = order.product_type.value
            
            # Place order with Kite
            order_response = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=order.exchange,
                tradingsymbol=order.symbol,
                transaction_type=kite_transaction_type,
                quantity=order.quantity,
                product=kite_product,
                order_type=kite_order_type,
                price=order.price if order.order_type != OrderType.MARKET else None,
                tag=order.tag
            )
            
            order_id = order_response['order_id']
            order.order_id = order_id
            order.status = OrderStatus.OPEN
            
            # Store order
            self.orders[order_id] = order
            self.order_history.append(order)
            self.daily_order_count += 1
            
            self.logger.info(f"Live order placed: {order_id}")
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"Error placing live order: {e}")
            order.status = OrderStatus.REJECTED
            return None
    
    def _update_paper_position(self, order: Order):
        """Update paper trading positions"""
        
        symbol = order.symbol
        
        if symbol not in self.paper_positions:
            self.paper_positions[symbol] = {
                'quantity': 0,
                'average_price': 0.0,
                'realized_pnl': 0.0
            }
        
        position = self.paper_positions[symbol]
        
        if order.transaction_type == TransactionType.BUY:
            # Add to position
            total_cost = (position['quantity'] * position['average_price'] + 
                         order.quantity * order.average_price)
            total_quantity = position['quantity'] + order.quantity
            
            if total_quantity > 0:
                position['average_price'] = total_cost / total_quantity
            position['quantity'] = total_quantity
            
            # Update capital
            self.current_capital -= order.quantity * order.average_price
            
        else:  # SELL
            # Reduce position
            if position['quantity'] >= order.quantity:
                # Calculate realized P&L
                pnl = (order.average_price - position['average_price']) * order.quantity
                position['realized_pnl'] += pnl
                position['quantity'] -= order.quantity
                
                # Update capital
                self.current_capital += order.quantity * order.average_price
                self.daily_pnl += pnl
                
                # Remove position if quantity becomes zero
                if position['quantity'] == 0:
                    del self.paper_positions[symbol]
            else:
                self.logger.warning(f"Insufficient quantity to sell for {symbol}")
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        
        if order_id not in self.orders:
            self.logger.warning(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        
        if order.status != OrderStatus.OPEN:
            self.logger.warning(f"Order {order_id} cannot be cancelled (status: {order.status})")
            return False
        
        if self.paper_trading:
            order.status = OrderStatus.CANCELLED
            order.update_timestamp = datetime.now()
            self.logger.info(f"Paper order {order_id} cancelled")
            return True
        
        else:
            try:
                self.kite.cancel_order(order.order_id)
                order.status = OrderStatus.CANCELLED
                order.update_timestamp = datetime.now()
                self.logger.info(f"Live order {order_id} cancelled")
                return True
            except Exception as e:
                self.logger.error(f"Error cancelling order {order_id}: {e}")
                return False
    
    def update_order_status(self):
        """Update status of live orders"""
        
        if self.paper_trading:
            return  # No need to update paper orders
        
        if not self.kite:
            return
        
        try:
            # Get all orders for today
            orders = self.kite.orders()
            
            for kite_order in orders:
                order_id = kite_order['order_id']
                
                if order_id in self.orders:
                    order = self.orders[order_id]
                    
                    # Update order status
                    status_map = {
                        'OPEN': OrderStatus.OPEN,
                        'COMPLETE': OrderStatus.COMPLETE,
                        'CANCELLED': OrderStatus.CANCELLED,
                        'REJECTED': OrderStatus.REJECTED
                    }
                    
                    new_status = status_map.get(kite_order['status'], OrderStatus.PENDING)
                    
                    if new_status != order.status:
                        order.status = new_status
                        order.filled_quantity = kite_order.get('filled_quantity', 0)
                        order.average_price = kite_order.get('average_price', 0)
                        order.update_timestamp = datetime.now()
                        
                        if new_status == OrderStatus.COMPLETE:
                            self._process_filled_order(order)
        
        except Exception as e:
            self.logger.error(f"Error updating order status: {e}")
    
    def _process_filled_order(self, order: Order):
        """Process a filled live order"""
        
        if order.transaction_type == TransactionType.SELL:
            # Update capital for sells (buys are already deducted)
            proceeds = order.filled_quantity * order.average_price
            self.current_capital += proceeds
        
        self.logger.info(f"Order filled: {order.order_id} - {order.transaction_type.value} "
                        f"{order.filled_quantity} {order.symbol} @ ${order.average_price:.2f}")
    
    def get_positions(self) -> pd.DataFrame:
        """Get current positions"""
        
        if self.paper_trading:
            if not self.paper_positions:
                return pd.DataFrame()
            
            data = []
            for symbol, pos in self.paper_positions.items():
                current_price = self.current_prices.get(symbol, pos['average_price'])
                unrealized_pnl = (current_price - pos['average_price']) * pos['quantity']
                
                data.append({
                    'Symbol': symbol,
                    'Quantity': pos['quantity'],
                    'Average Price': pos['average_price'],
                    'Current Price': current_price,
                    'Unrealized P&L': unrealized_pnl,
                    'Realized P&L': pos['realized_pnl']
                })
            
            return pd.DataFrame(data)
        
        else:
            if not self.kite:
                return pd.DataFrame()
            
            try:
                positions = self.kite.positions()
                return pd.DataFrame(positions['net'])
            except Exception as e:
                self.logger.error(f"Error fetching positions: {e}")
                return pd.DataFrame()
    
    def get_order_book(self) -> pd.DataFrame:
        """Get order book"""
        
        if not self.orders:
            return pd.DataFrame()
        
        data = []
        for order in self.order_history:
            data.append({
                'Order ID': order.order_id,
                'Symbol': order.symbol,
                'Type': order.transaction_type.value,
                'Quantity': order.quantity,
                'Price': order.price,
                'Order Type': order.order_type.value,
                'Status': order.status.value,
                'Filled Qty': order.filled_quantity,
                'Avg Price': order.average_price,
                'Timestamp': order.timestamp,
                'Tag': order.tag
            })
        
        return pd.DataFrame(data)
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """Get trading summary statistics"""
        
        total_orders = len(self.order_history)
        completed_orders = len([o for o in self.order_history if o.status == OrderStatus.COMPLETE])
        
        if self.paper_trading:
            total_pnl = sum(pos['realized_pnl'] for pos in self.paper_positions.values())
            total_pnl += self.daily_pnl
        else:
            total_pnl = self.initial_capital - self.current_capital  # Simplified
        
        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'success_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            'daily_order_count': self.daily_order_count,
            'total_pnl': total_pnl,
            'daily_pnl': self.daily_pnl,
            'current_capital': self.current_capital,
            'trading_mode': 'Paper' if self.paper_trading else 'Live'
        }
    
    # Convenience methods for easy order placement
    def buy(self, symbol: str, quantity: int, price: float = 0, 
           exchange: str = "NSE", order_type: OrderType = OrderType.MARKET) -> Optional[str]:
        """Convenience method to place buy order"""
        return self.place_order(
            symbol=symbol,
            exchange=exchange,
            transaction_type=TransactionType.BUY,
            quantity=quantity,
            order_type=order_type,
            price=price
        )
    
    def sell(self, symbol: str, quantity: int, price: float = 0,
            exchange: str = "NSE", order_type: OrderType = OrderType.MARKET) -> Optional[str]:
        """Convenience method to place sell order"""
        return self.place_order(
            symbol=symbol,
            exchange=exchange,
            transaction_type=TransactionType.SELL,
            quantity=quantity,
            order_type=order_type,
            price=price
        )
    
    def print_trading_summary(self):
        """Print formatted trading summary"""
        summary = self.get_trading_summary()
        
        print("\n" + "="*50)
        print(f"📊 TRADING SUMMARY ({summary['trading_mode']} Mode)")
        print("="*50)
        
        print(f"📋 Total Orders: {summary['total_orders']}")
        print(f"✅ Completed Orders: {summary['completed_orders']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"📅 Today's Orders: {summary['daily_order_count']}")
        print(f"💰 Total P&L: ${summary['total_pnl']:.2f}")
        print(f"📊 Daily P&L: ${summary['daily_pnl']:.2f}")
        print(f"💵 Current Capital: ${summary['current_capital']:.2f}")
        
        print("="*50)
