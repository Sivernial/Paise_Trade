from datetime import datetime
from typing import Dict, List, Callable
import pandas as pd
import numpy as np
from Common import Order, Position, OrderType, TransactionType, OrderStatus
import logging

logger = logging.getLogger(__name__)

class BacktestEngine:
    
    def __init__(self, initial_capital: float = 100000, 
                 commission_rate: float = 0.001):
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
    
    def place_order(self, symbol: str, transaction_type: TransactionType,
                   quantity: int, price: float) -> str:
        
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
        self._update_position(order)
        
        return order.order_id
    
    def _update_position(self, order: Order):
        symbol = order.symbol
        
        if order.transaction_type == TransactionType.BUY:
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_cost = pos.quantity * pos.entry_price + order.quantity * order.price
                total_qty = pos.quantity + order.quantity
                pos.entry_price = total_cost / total_qty
                pos.quantity = total_qty
            else:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order.quantity,
                    entry_price=order.price,
                    entry_date=self.current_date
                )
        
        elif order.transaction_type == TransactionType.SELL:
            if symbol in self.positions:
                pos = self.positions[symbol]
                pnl = (order.price - pos.entry_price) * order.quantity - order.commission
                
                self.trades.append({
                    'symbol': symbol,
                    'entry_date': pos.entry_date,
                    'exit_date': self.current_date,
                    'entry_price': pos.entry_price,
                    'exit_price': order.price,
                    'quantity': order.quantity,
                    'pnl': pnl,
                    'return': pnl / (pos.entry_price * order.quantity)
                })
                
                pos.quantity -= order.quantity
                if pos.quantity <= 0:
                    del self.positions[symbol]
    
    def get_portfolio_value(self) -> float:
        value = self.cash
        for symbol, pos in self.positions.items():
            current_price = self.current_prices.get(symbol, pos.entry_price)
            value += pos.quantity * current_price
        return value
    
    def run(self, data: Dict[str, pd.DataFrame], strategy_func: Callable,
           start_date: datetime = None, end_date: datetime = None) -> dict:
        
        all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
        
        if start_date:
            all_dates = [d for d in all_dates if d >= start_date]
        if end_date:
            all_dates = [d for d in all_dates if d <= end_date]
        
        logger.info(f"Running backtest: {all_dates[0]} to {all_dates[-1]}")
        
        for date in all_dates:
            self.current_date = date
            self.dates.append(date)
            
            for symbol, df in data.items():
                if date in df.index:
                    self.current_prices[symbol] = df.loc[date, 'close']
            
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
        
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
        
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

