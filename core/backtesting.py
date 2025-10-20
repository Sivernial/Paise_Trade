"""
Comprehensive Backtesting Engine for Algorithmic Trading Strategies
Features historical simulation, performance analysis, and risk metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable, Any
import warnings

# Import dataclasses from data_structures
from data_structures.backtesting_dataclass import (
    Order, Position, PerformanceMetrics, OrderType, OrderStatus
)

class BacktestEngine:
    """
    Comprehensive backtesting engine for trading strategies
    
    Features:
    - Historical data simulation
    - Portfolio tracking
    - Performance metrics calculation
    - Risk analysis
    - Transaction cost modeling
    - Slippage simulation
    """
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 commission_rate: float = 0.001,
                 slippage_rate: float = 0.0005,
                 max_positions: int = 10):
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.max_positions = max_positions
        
        # Portfolio tracking
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Dict] = []
        self.portfolio_values: List[Dict] = []
        
        # Performance tracking
        self.daily_returns: List[float] = []
        self.equity_curve: List[float] = [initial_capital]
        self.drawdown_curve: List[float] = [0.0]
        
        # Strategy callback
        self.strategy_func: Optional[Callable] = None
        
        # Current simulation state
        self.current_date: Optional[datetime] = None
        self.current_prices: Dict[str, float] = {}
        
    def set_strategy(self, strategy_func: Callable):
        """Set the trading strategy function"""
        self.strategy_func = strategy_func
    
    def place_order(self, symbol: str, order_type: OrderType, 
                   quantity: int, price: Optional[float] = None) -> str:
        """
        Place a trading order
        
        Args:
            symbol: Trading symbol
            order_type: BUY or SELL
            quantity: Number of shares
            price: Limit price (None for market order)
            
        Returns:
            Order ID
        """
        if not self.current_date:
            raise ValueError("No current date set for backtesting")
        
        # Use current market price if no price specified
        if price is None:
            price = self.current_prices.get(symbol, 0)
        
        if price <= 0:
            warnings.warn(f"Invalid price for {symbol}: {price}")
            return ""
        
        # Generate order ID
        order_id = f"{symbol}_{len(self.orders) + 1}_{int(self.current_date.timestamp())}"
        
        # Create order
        order = Order(
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            price=price,
            timestamp=self.current_date,
            order_id=order_id
        )
        
        # Execute order immediately (simplified execution)
        self._execute_order(order)
        
        self.orders.append(order)
        return order_id
    
    def _execute_order(self, order: Order):
        """Execute a trading order with slippage and commission"""
        
        # Apply slippage
        if order.order_type == OrderType.BUY:
            fill_price = order.price * (1 + self.slippage_rate)
        else:
            fill_price = order.price * (1 - self.slippage_rate)
        
        # Calculate commission
        commission = order.quantity * fill_price * self.commission_rate
        
        # Check if we have enough capital for buy orders
        if order.order_type == OrderType.BUY:
            total_cost = order.quantity * fill_price + commission
            if total_cost > self.current_capital:
                order.status = OrderStatus.CANCELLED
                return
        
        # Execute the trade
        order.fill_price = fill_price
        order.fill_timestamp = self.current_date
        order.commission = commission
        order.status = OrderStatus.FILLED
        
        # Update positions
        self._update_position(order)
        
        # Update capital
        if order.order_type == OrderType.BUY:
            self.current_capital -= (order.quantity * fill_price + commission)
        else:
            self.current_capital += (order.quantity * fill_price - commission)
        
        # Record trade
        self._record_trade(order)
    
    def _update_position(self, order: Order):
        """Update position based on executed order"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # New position
            if order.order_type == OrderType.BUY:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order.quantity,
                    entry_price=order.fill_price,
                    entry_timestamp=order.fill_timestamp,
                    current_price=order.fill_price
                )
        else:
            # Existing position
            pos = self.positions[symbol]
            
            if order.order_type == OrderType.BUY:
                # Add to position
                total_cost = pos.quantity * pos.entry_price + order.quantity * order.fill_price
                total_quantity = pos.quantity + order.quantity
                pos.entry_price = total_cost / total_quantity
                pos.quantity = total_quantity
            else:
                # Reduce position
                pos.quantity -= order.quantity
                
                # Close position if quantity reaches zero
                if pos.quantity <= 0:
                    del self.positions[symbol]
    
    def _record_trade(self, order: Order):
        """Record completed trade for analysis"""
        trade = {
            'symbol': order.symbol,
            'type': order.order_type.value,
            'quantity': order.quantity,
            'price': order.fill_price,
            'timestamp': order.fill_timestamp,
            'commission': order.commission,
            'portfolio_value': self.get_portfolio_value()
        }
        self.trades.append(trade)
    
    def get_portfolio_value(self) -> float:
        """Calculate current portfolio value"""
        value = self.current_capital
        
        for symbol, position in self.positions.items():
            current_price = self.current_prices.get(symbol, position.entry_price)
            position.current_price = current_price
            position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
            value += position.quantity * current_price
        
        return value
    
    def run_backtest(self, data: Dict[str, pd.DataFrame], 
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Run the backtest simulation
        
        Args:
            data: Dictionary mapping symbols to price DataFrames
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Dictionary with backtest results
        """
        if not self.strategy_func:
            raise ValueError("No strategy function set")
        
        # Align all data to common date range
        all_dates = set()
        for df in data.values():
            all_dates.update(df.index)
        
        all_dates = sorted(list(all_dates))
        
        if start_date:
            all_dates = [d for d in all_dates if d >= start_date]
        if end_date:
            all_dates = [d for d in all_dates if d <= end_date]
        
        print(f"🚀 Starting backtest from {all_dates[0]} to {all_dates[-1]}")
        print(f"📊 Total trading days: {len(all_dates)}")
        
        # Run simulation day by day
        for i, date in enumerate(all_dates):
            self.current_date = date
            
            # Update current prices
            for symbol, df in data.items():
                if date in df.index:
                    self.current_prices[symbol] = df.loc[date, 'close']
            
            # Calculate portfolio value
            portfolio_value = self.get_portfolio_value()
            
            # Calculate daily return
            if len(self.equity_curve) > 0:
                daily_return = (portfolio_value - self.equity_curve[-1]) / self.equity_curve[-1]
                self.daily_returns.append(daily_return)
            
            # Update equity curve
            self.equity_curve.append(portfolio_value)
            
            # Calculate drawdown
            peak = max(self.equity_curve)
            drawdown = (portfolio_value - peak) / peak
            self.drawdown_curve.append(drawdown)
            
            # Record portfolio state
            portfolio_state = {
                'date': date,
                'portfolio_value': portfolio_value,
                'cash': self.current_capital,
                'positions_value': portfolio_value - self.current_capital,
                'drawdown': drawdown
            }
            self.portfolio_values.append(portfolio_state)
            
            # Call strategy function
            try:
                # Prepare data for strategy (last N bars for each symbol)
                strategy_data = {}
                lookback = 100  # Last 100 bars
                
                for symbol, df in data.items():
                    symbol_data = df[df.index <= date].tail(lookback)
                    if not symbol_data.empty:
                        strategy_data[symbol] = symbol_data
                
                # Call strategy with current data and backtest engine
                self.strategy_func(strategy_data, self, date)
                
            except Exception as e:
                print(f"⚠️ Strategy error on {date}: {e}")
            
            # Progress update
            if (i + 1) % 50 == 0:
                progress = (i + 1) / len(all_dates) * 100
                print(f"📈 Progress: {progress:.1f}% - Portfolio Value: ${portfolio_value:,.2f}")
        
        # Calculate final performance metrics
        performance = self._calculate_performance()
        
        # Prepare results
        results = {
            'performance_metrics': performance,
            'equity_curve': self.equity_curve,
            'daily_returns': self.daily_returns,
            'drawdown_curve': self.drawdown_curve,
            'trades': self.trades,
            'portfolio_values': self.portfolio_values,
            'final_value': self.equity_curve[-1],
            'total_return': (self.equity_curve[-1] - self.initial_capital) / self.initial_capital
        }
        
        print(f"✅ Backtest completed!")
        print(f"💰 Final Portfolio Value: ${self.equity_curve[-1]:,.2f}")
        print(f"📈 Total Return: {results['total_return']:.2%}")
        
        return results
    
    def _calculate_performance(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        if len(self.daily_returns) == 0:
            return PerformanceMetrics()
        
        returns = np.array(self.daily_returns)
        equity = np.array(self.equity_curve)
        
        # Basic metrics
        total_return = (equity[-1] - equity[0]) / equity[0]
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        volatility = np.std(returns) * np.sqrt(252)
        
        # Risk metrics
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        max_drawdown = min(self.drawdown_curve)
        
        # Trade analysis
        profitable_trades = len([t for t in self.trades if self._is_profitable_trade(t)])
        total_trades = len(self.trades)
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # Calculate more detailed trade metrics
        trade_returns = self._calculate_trade_returns()
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0
        
        winning_trades = [r for r in trade_returns if r > 0]
        losing_trades = [r for r in trade_returns if r < 0]
        
        avg_winning_trade = np.mean(winning_trades) if winning_trades else 0
        avg_losing_trade = np.mean(losing_trades) if losing_trades else 0
        
        largest_win = max(winning_trades) if winning_trades else 0
        largest_loss = min(losing_trades) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Sortino ratio
        downside_returns = [r for r in returns if r < 0]
        downside_std = np.std(downside_returns) * np.sqrt(252) if downside_returns else 1
        sortino_ratio = annualized_return / downside_std if downside_std > 0 else 0
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            losing_trades=len(losing_trades),
            avg_trade_return=avg_trade_return,
            avg_winning_trade=avg_winning_trade,
            avg_losing_trade=avg_losing_trade,
            largest_win=largest_win,
            largest_loss=largest_loss,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio
        )
    
    def _is_profitable_trade(self, trade: Dict) -> bool:
        """Determine if a trade was profitable (simplified)"""
        # This is a simplified check - in practice, you'd match buy/sell pairs
        return trade['type'] == 'SELL'  # Assumes sells close profitable positions
    
    def _calculate_trade_returns(self) -> List[float]:
        """Calculate returns for individual trades"""
        # Simplified trade return calculation
        # In practice, you'd match buy/sell pairs and calculate P&L
        returns = []
        
        for i in range(1, len(self.equity_curve)):
            daily_return = (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
            returns.append(daily_return)
        
        return returns
    
    def get_positions_summary(self) -> pd.DataFrame:
        """Get summary of current positions"""
        if not self.positions:
            return pd.DataFrame()
        
        positions_data = []
        for symbol, pos in self.positions.items():
            current_price = self.current_prices.get(symbol, pos.entry_price)
            unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
            
            positions_data.append({
                'Symbol': symbol,
                'Quantity': pos.quantity,
                'Entry Price': pos.entry_price,
                'Current Price': current_price,
                'Unrealized P&L': unrealized_pnl,
                'Unrealized %': (unrealized_pnl / (pos.entry_price * pos.quantity)) * 100
            })
        
        return pd.DataFrame(positions_data)
    
    def get_trades_summary(self) -> pd.DataFrame:
        """Get summary of all trades"""
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trades)
    
    def print_performance_summary(self, performance: PerformanceMetrics):
        """Print a formatted performance summary"""
        print("\n" + "="*60)
        print("📊 BACKTEST PERFORMANCE SUMMARY")
        print("="*60)
        
        print(f"💰 Total Return: {performance.total_return:.2%}")
        print(f"📈 Annualized Return: {performance.annualized_return:.2%}")
        print(f"📉 Volatility: {performance.volatility:.2%}")
        print(f"⚡ Sharpe Ratio: {performance.sharpe_ratio:.3f}")
        print(f"📊 Calmar Ratio: {performance.calmar_ratio:.3f}")
        print(f"🎯 Sortino Ratio: {performance.sortino_ratio:.3f}")
        print(f"⬇️ Max Drawdown: {performance.max_drawdown:.2%}")
        
        print(f"\n🔢 TRADE STATISTICS")
        print(f"📊 Total Trades: {performance.total_trades}")
        print(f"✅ Win Rate: {performance.win_rate:.2%}")
        print(f"💵 Profit Factor: {performance.profit_factor:.3f}")
        print(f"📈 Avg Trade Return: {performance.avg_trade_return:.3%}")
        print(f"🏆 Largest Win: {performance.largest_win:.3%}")
        print(f"💔 Largest Loss: {performance.largest_loss:.3%}")
        
        print("="*60)