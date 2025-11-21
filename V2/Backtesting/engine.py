from datetime import datetime, time
from typing import Dict, List, Callable, Optional
import pandas as pd
import numpy as np
from Common import Order, Position, OrderType, TransactionType, OrderStatus, Signal
from .config import BacktestConfig
import logging

logger = logging.getLogger(__name__)

class BacktestEngine:
    
    def __init__(self, initial_capital: float = None, 
                 commission_rate: float = None,
                 enable_position_management: bool = True,
                 time_stop: str = '15:20',
                 partial_exit_pct: float = 0.5,
                 trail_atr_mult: float = 2.0):
        if initial_capital is None:
            initial_capital = BacktestConfig.INITIAL_CAPITAL
        if commission_rate is None:
            commission_rate = BacktestConfig.COMMISSION_RATE
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[dict] = []
        
        self.equity_curve: List[float] = [initial_capital]
        self.dates: List[datetime] = []
        
        self.current_date: datetime = None
        self.current_prices: Dict[str, float] = {}
        self.current_atrs: Dict[str, float] = {}
        
        # Position management settings
        self.enable_position_management = enable_position_management
        self.partial_exit_pct = partial_exit_pct
        self.trail_atr_mult = trail_atr_mult
        
        # Parse time stop
        hour, minute = map(int, time_stop.split(':'))
        self.time_stop = time(hour, minute)
    
    def place_order(self, symbol: str, transaction_type: TransactionType,
                   quantity: int, price: float, signal: Optional[Signal] = None) -> str:
        
        if quantity <= 0:
            logger.warning(f"Invalid quantity {quantity} for {symbol}")
            return ""
        
        if price <= 0:
            logger.warning(f"Invalid price {price} for {symbol}")
            return ""
        
        commission = quantity * price * self.commission_rate
        
        if transaction_type == TransactionType.BUY:
            cost = quantity * price + commission
            if cost > self.cash:
                logger.warning(f"Insufficient funds for {symbol}")
                return ""
            self.cash -= cost
        else:
            if symbol not in self.positions or self.positions[symbol].quantity < quantity:
                logger.warning(f"Insufficient position for {symbol}")
                return ""
            self.cash += quantity * price - commission
        
        order = Order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            order_type=OrderType.MARKET,
            transaction_type=transaction_type,
            timestamp=self.current_date,
            order_id=f"ORD_{len(self.orders)+1}",
            status=OrderStatus.COMPLETE,
            filled_quantity=quantity,
            average_price=price,
            commission=commission
        )
        
        self.orders.append(order)
        self._update_position(order, signal)
        
        return order.order_id
    
    def _update_position(self, order: Order, signal: Optional[Signal] = None):
        symbol = order.symbol
        
        if order.transaction_type == TransactionType.BUY:
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_cost = pos.quantity * pos.entry_price + order.quantity * order.price
                total_qty = pos.quantity + order.quantity
                if total_qty > 0:
                    pos.entry_price = total_cost / total_qty
                    pos.quantity = total_qty
                else:
                    logger.warning(f"Invalid quantity for {symbol}: total_qty={total_qty}")
            else:
                # Create new position with position management from signal
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order.quantity,
                    entry_price=order.price,
                    entry_date=self.current_date,
                    current_price=order.price,
                    highest_price=order.price,
                    lowest_price=order.price,
                    stop_loss=signal.stop_loss if signal else None,
                    target=signal.target if signal else None,
                    trailing_stop=signal.trailing_stop if signal else None,
                    breakeven_trigger=signal.breakeven_trigger if signal else None,
                    partial_exit_trigger=signal.partial_exit_trigger if signal else None
                )
        
        elif order.transaction_type == TransactionType.SELL:
            if symbol in self.positions:
                pos = self.positions[symbol]
                pnl = (order.price - pos.entry_price) * order.quantity - order.commission
                
                trade_return = 0.0
                denominator = pos.entry_price * order.quantity
                if denominator != 0:
                    trade_return = pnl / denominator
                
                # Determine exit reason
                exit_reason = 'Manual'
                if pos.partial_exit_done and order.quantity < pos.quantity:
                    exit_reason = 'Partial Exit'
                elif self.current_date.time() >= self.time_stop:
                    exit_reason = 'Time Stop'
                elif pos.stop_loss and order.price <= pos.stop_loss:
                    exit_reason = 'Stop Loss'
                elif pos.target and order.price >= pos.target:
                    exit_reason = 'Target'
                
                self.trades.append({
                    'symbol': symbol,
                    'entry_date': pos.entry_date,
                    'exit_date': self.current_date,
                    'entry_price': pos.entry_price,
                    'exit_price': order.price,
                    'quantity': order.quantity,
                    'pnl': pnl,
                    'return': trade_return,
                    'exit_reason': exit_reason
                })
                
                pos.quantity -= order.quantity
                if pos.quantity <= 0:
                    logger.info(f"Position closed: {symbol}, Total PnL: {pos.realized_pnl:.2f}")
                    del self.positions[symbol]
    
    def update_position_management(self):
        """Update all positions - check stops, targets, partial exits, trailing stops"""
        if not self.enable_position_management:
            return
        
        # Check time stop first
        if self.current_date and self.current_date.time() >= self.time_stop:
            self._close_all_positions("Time stop")
            return
        
        positions_to_close = []
        positions_to_partial_exit = []
        
        for symbol, pos in list(self.positions.items()):
            # Update current price and track highest/lowest
            if symbol in self.current_prices:
                pos.current_price = self.current_prices[symbol]
                pos.highest_price = max(pos.highest_price, pos.current_price)
                pos.lowest_price = min(pos.lowest_price, pos.current_price)
                pos.unrealized_pnl = (pos.current_price - pos.entry_price) * pos.quantity
            
            # Get current ATR for trailing stop
            current_atr = self.current_atrs.get(symbol, 0)
            
            # 1. Check stop loss
            if self._check_stop_loss(symbol):
                positions_to_close.append((symbol, pos.quantity, "Stop loss"))
                continue
            
            # 2. Check partial exit trigger
            partial_qty = self._check_partial_exit(symbol)
            if partial_qty:
                positions_to_partial_exit.append((symbol, partial_qty, "Partial exit at +1R"))
            
            # 3. Check breakeven stop
            self._check_breakeven_stop(symbol)
            
            # 4. Update trailing stop
            if current_atr > 0:
                self._update_trailing_stop(symbol, current_atr)
            
            # 5. Check target (full exit)
            if self._check_target(symbol):
                positions_to_close.append((symbol, pos.quantity, "Target hit"))
                continue
        
        # Execute partial exits
        for symbol, quantity, reason in positions_to_partial_exit:
            if symbol in self.positions:
                price = self.current_prices.get(symbol)
                if price:
                    self.place_order(symbol, TransactionType.SELL, quantity, price)
                    logger.info(f"Partial exit: {quantity} {symbol} @ {price:.2f} - {reason}")
        
        # Execute full exits (use remaining quantity after partial exits)
        for symbol, quantity, reason in positions_to_close:
            if symbol in self.positions:
                pos = self.positions[symbol]
                actual_quantity = pos.quantity  # Use remaining quantity
                price = self.current_prices.get(symbol)
                if price and actual_quantity > 0:
                    self.place_order(symbol, TransactionType.SELL, actual_quantity, price)
                    logger.info(f"Position exit: {actual_quantity} {symbol} @ {price:.2f} - {reason}")
    
    def _close_all_positions(self, reason: str = "Market close"):
        """Close all open positions"""
        for symbol, pos in list(self.positions.items()):
            price = self.current_prices.get(symbol, pos.entry_price)
            self.place_order(symbol, TransactionType.SELL, pos.quantity, price)
            logger.info(f"Force exit: {pos.quantity} {symbol} @ {price:.2f} - {reason}")
    
    def _check_partial_exit(self, symbol: str) -> Optional[int]:
        """Check if partial exit should be triggered, return quantity to exit"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        
        if pos.partial_exit_done or pos.partial_exit_trigger is None:
            return None
        
        is_long = pos.quantity > 0
        
        if is_long and pos.current_price >= pos.partial_exit_trigger:
            exit_qty = int(pos.quantity * self.partial_exit_pct)
            pos.partial_exit_done = True
            return exit_qty
        elif not is_long and pos.current_price <= pos.partial_exit_trigger:
            exit_qty = int(abs(pos.quantity) * self.partial_exit_pct)
            pos.partial_exit_done = True
            return exit_qty
        
        return None
    
    def _check_breakeven_stop(self, symbol: str):
        """Move stop to breakeven if breakeven trigger is hit"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        
        if pos.breakeven_moved or pos.breakeven_trigger is None:
            return
        
        is_long = pos.quantity > 0
        
        if is_long and pos.current_price >= pos.breakeven_trigger:
            pos.stop_loss = pos.entry_price
            pos.breakeven_moved = True
            logger.debug(f"Breakeven stop set for {symbol} at {pos.entry_price}")
        elif not is_long and pos.current_price <= pos.breakeven_trigger:
            pos.stop_loss = pos.entry_price
            pos.breakeven_moved = True
            logger.debug(f"Breakeven stop set for {symbol} at {pos.entry_price}")
    
    def _update_trailing_stop(self, symbol: str, current_atr: float):
        """Update trailing stop based on highest/lowest price"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        
        if pos.trailing_stop is None:
            return
        
        is_long = pos.quantity > 0
        
        if is_long:
            new_trail = pos.highest_price - (self.trail_atr_mult * current_atr)
            if pos.stop_loss is not None:
                pos.stop_loss = max(pos.stop_loss, new_trail)
            else:
                pos.stop_loss = new_trail
        else:
            new_trail = pos.lowest_price + (self.trail_atr_mult * current_atr)
            if pos.stop_loss is not None:
                pos.stop_loss = min(pos.stop_loss, new_trail)
            else:
                pos.stop_loss = new_trail
    
    def _check_stop_loss(self, symbol: str) -> bool:
        """Check if stop loss is hit"""
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        
        if pos.stop_loss is None:
            return False
        
        is_long = pos.quantity > 0
        
        if is_long and pos.current_price <= pos.stop_loss:
            return True
        elif not is_long and pos.current_price >= pos.stop_loss:
            return True
        
        return False
    
    def _check_target(self, symbol: str) -> bool:
        """Check if target is hit"""
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        
        if pos.target is None:
            return False
        
        is_long = pos.quantity > 0
        
        if is_long and pos.current_price >= pos.target:
            return True
        elif not is_long and pos.current_price <= pos.target:
            return True
        
        return False
    
    def set_atr(self, symbol: str, atr: float):
        """Set current ATR for symbol (used for trailing stops)"""
        self.current_atrs[symbol] = atr
    
    def get_portfolio_value(self) -> float:
        value = self.cash
        for symbol, pos in self.positions.items():
            current_price = self.current_prices.get(symbol, pos.entry_price)
            value += pos.quantity * current_price
        return value
    
    def run(self, data: Dict[str, pd.DataFrame], strategy_func: Callable,
           start_date: datetime = None, end_date: datetime = None) -> dict:
        
        # Convert all DataFrame indices to timezone-naive
        for symbol in data:
            if data[symbol].index.tzinfo is not None:
                data[symbol].index = data[symbol].index.tz_localize(None)
        
        all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
        
        if start_date:
            all_dates = [d for d in all_dates if d >= start_date]
        if end_date:
            all_dates = [d for d in all_dates if d <= end_date]
        
        logger.info(f"Running backtest: {all_dates[0]} to {all_dates[-1]}")
        
        for date in all_dates:
            self.current_date = date
            self.dates.append(date)
            
            # Update current prices and ATRs
            for symbol, df in data.items():
                if date in df.index:
                    self.current_prices[symbol] = df.loc[date, 'close']
                    
                    # Calculate ATR if we have enough data
                    if 'atr' in df.columns:
                        self.current_atrs[symbol] = df.loc[date, 'atr']
                    elif len(df[df.index <= date]) >= 14:
                        # Calculate ATR on the fly if not in data
                        recent_data = df[df.index <= date].tail(14)
                        if len(recent_data) >= 14:
                            from Technical_Indicators import StaticIndicators
                            atr = StaticIndicators.atr(
                                recent_data['high'], 
                                recent_data['low'], 
                                recent_data['close'], 
                                14
                            )
                            if not atr.empty:
                                self.current_atrs[symbol] = atr.iloc[-1]
            
            # Update position management (stops, targets, trailing stops)
            if self.enable_position_management:
                self.update_position_management()
            
            strategy_data = {}
            for symbol, df in data.items():
                strategy_data[symbol] = df[df.index <= date].tail(100)
            
            try:
                strategy_func(strategy_data, self, date)
            except Exception as e:
                logger.error(f"Strategy error on {date}: {e}")
            
            portfolio_value = self.get_portfolio_value()
            self.equity_curve.append(portfolio_value)
        
        return self._generate_results()
    
    def _generate_results(self) -> dict:
        equity = np.array(self.equity_curve)
        returns = np.diff(equity) / equity[:-1]
        
        total_return = (equity[-1] - equity[0]) / equity[0]
        
        # Calculate Sharpe ratio with protection against division by zero
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe = 0.0
        
        max_dd = 0
        peak = equity[0]
        for val in equity:
            if val > peak:
                peak = val
            dd = (val - peak) / peak
            if dd < max_dd:
                max_dd = dd
        
        trades_df = pd.DataFrame(self.trades)
        win_rate = len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) if len(trades_df) > 0 else 0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'final_value': equity[-1],
            'equity_curve': self.equity_curve,
            'trades': self.trades
        }

