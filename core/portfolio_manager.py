"""
Portfolio Management System for Algorithmic Trading
Handles position tracking, P&L calculation, and portfolio optimization
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

class PositionType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class Position:
    """Enhanced position tracking"""
    symbol: str
    position_type: PositionType
    quantity: int
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    commission_paid: float = 0.0
    
    def __post_init__(self):
        self.market_value = self.quantity * self.current_price
        self.cost_basis = self.quantity * self.entry_price
    
    def update_price(self, new_price: float):
        """Update current price and calculate unrealized P&L"""
        self.current_price = new_price
        self.market_value = self.quantity * new_price
        
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - new_price) * self.quantity
    
    def get_return_pct(self) -> float:
        """Get percentage return on position"""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100
    
    def days_held(self) -> int:
        """Number of days position has been held"""
        return (datetime.now() - self.entry_date).days

@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float = 0.0
    cash: float = 0.0
    invested_value: float = 0.0
    total_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    day_pnl: float = 0.0
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    open_positions: int = 0
    sector_allocation: Dict[str, float] = field(default_factory=dict)

class RiskManager:
    """Risk management utilities"""
    
    def __init__(self, max_position_size: float = 0.1, max_portfolio_risk: float = 0.02):
        self.max_position_size = max_position_size  # Max % of portfolio per position
        self.max_portfolio_risk = max_portfolio_risk  # Max % risk per trade
        
    def calculate_position_size(self, 
                              portfolio_value: float, 
                              entry_price: float, 
                              stop_loss: float) -> int:
        """Calculate position size based on risk management rules"""
        
        # Risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        # Maximum position value based on portfolio percentage
        max_position_value = portfolio_value * self.max_position_size
        
        # Maximum risk amount
        max_risk_amount = portfolio_value * self.max_portfolio_risk
        
        # Position size based on risk
        if risk_per_share > 0:
            risk_based_size = int(max_risk_amount / risk_per_share)
        else:
            risk_based_size = int(max_position_value / entry_price)
        
        # Position size based on max position value
        value_based_size = int(max_position_value / entry_price)
        
        # Take the smaller of the two
        position_size = min(risk_based_size, value_based_size)
        
        return max(1, position_size)  # Minimum 1 share
    
    def check_correlation_risk(self, positions: Dict[str, Position], 
                             new_symbol: str, correlation_limit: float = 0.7) -> bool:
        """Check if adding new position would create excessive correlation"""
        # Simplified correlation check - in practice, use historical correlation data
        # For now, just check if we're not overconcentrated in similar symbols
        
        similar_symbols = [pos.symbol for pos in positions.values() 
                         if pos.symbol.startswith(new_symbol[:3])]
        
        return len(similar_symbols) < 3  # Max 3 similar positions

class PortfolioManager:
    """
    Comprehensive portfolio management system
    
    Features:
    - Position tracking and management
    - P&L calculation and reporting
    - Risk management
    - Portfolio optimization
    - Performance analytics
    """
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 commission_rate: float = 0.001,
                 margin_requirement: float = 0.5):
        
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.margin_requirement = margin_requirement
        
        # Portfolio state
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.trades: List[Dict] = []
        
        # Performance tracking
        self.daily_values: List[Tuple[datetime, float]] = [(datetime.now(), initial_capital)]
        self.daily_returns: List[float] = []
        self.benchmark_returns: List[float] = []
        
        # Risk management
        self.risk_manager = RiskManager()
        
        # Setup logging
        self.logger = logging.getLogger('PortfolioManager')
        
    def add_position(self, 
                    symbol: str, 
                    quantity: int, 
                    entry_price: float, 
                    position_type: PositionType = PositionType.LONG,
                    stop_loss: Optional[float] = None,
                    take_profit: Optional[float] = None) -> bool:
        """
        Add a new position to the portfolio
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares
            entry_price: Entry price per share
            position_type: LONG or SHORT
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            True if position was added successfully
        """
        
        # Calculate total cost
        total_cost = quantity * entry_price
        commission = total_cost * self.commission_rate
        total_required = total_cost + commission
        
        # Check if we have enough cash
        if total_required > self.cash:
            self.logger.warning(f"Insufficient cash for {symbol}: ${total_required:.2f} required, ${self.cash:.2f} available")
            return False
        
        # Check position size limits
        portfolio_value = self.get_portfolio_value()
        if total_cost > portfolio_value * self.risk_manager.max_position_size:
            self.logger.warning(f"Position size too large for {symbol}")
            return False
        
        # Check correlation risk
        if not self.risk_manager.check_correlation_risk(self.positions, symbol):
            self.logger.warning(f"Correlation risk too high for {symbol}")
            return False
        
        # Create position
        position = Position(
            symbol=symbol,
            position_type=position_type,
            quantity=quantity,
            entry_price=entry_price,
            entry_date=datetime.now(),
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission_paid=commission
        )
        
        # Update portfolio
        if symbol in self.positions:
            # Add to existing position
            existing = self.positions[symbol]
            total_quantity = existing.quantity + quantity
            total_cost_basis = (existing.quantity * existing.entry_price + 
                              quantity * entry_price)
            existing.entry_price = total_cost_basis / total_quantity
            existing.quantity = total_quantity
            existing.commission_paid += commission
        else:
            # New position
            self.positions[symbol] = position
        
        # Update cash
        self.cash -= total_required
        
        # Record trade
        self._record_trade(symbol, 'BUY', quantity, entry_price, commission)
        
        self.logger.info(f"Added position: {symbol} x {quantity} @ ${entry_price:.2f}")
        return True
    
    def close_position(self, 
                      symbol: str, 
                      quantity: Optional[int] = None, 
                      exit_price: Optional[float] = None) -> bool:
        """
        Close a position (partially or fully)
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares to close (None for full position)
            exit_price: Exit price (None to use current market price)
            
        Returns:
            True if position was closed successfully
        """
        
        if symbol not in self.positions:
            self.logger.warning(f"No position found for {symbol}")
            return False
        
        position = self.positions[symbol]
        
        # Determine quantity to close
        if quantity is None:
            quantity = position.quantity
        else:
            quantity = min(quantity, position.quantity)
        
        # Use current price if no exit price provided
        if exit_price is None:
            exit_price = position.current_price
        
        # Calculate P&L
        if position.position_type == PositionType.LONG:
            pnl = (exit_price - position.entry_price) * quantity
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * quantity
        
        # Calculate commission
        commission = quantity * exit_price * self.commission_rate
        net_pnl = pnl - commission
        
        # Update cash
        proceeds = quantity * exit_price - commission
        self.cash += proceeds
        
        # Update position
        position.realized_pnl += net_pnl
        position.quantity -= quantity
        
        # Remove position if fully closed
        if position.quantity == 0:
            position.unrealized_pnl = 0
            self.closed_positions.append(position)
            del self.positions[symbol]
        
        # Record trade
        self._record_trade(symbol, 'SELL', quantity, exit_price, commission, net_pnl)
        
        self.logger.info(f"Closed position: {symbol} x {quantity} @ ${exit_price:.2f}, P&L: ${net_pnl:.2f}")
        return True
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for all positions"""
        for symbol, position in self.positions.items():
            if symbol in prices:
                position.update_price(prices[symbol])
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        total_value = self.cash
        
        for position in self.positions.values():
            total_value += position.market_value
        
        return total_value
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics"""
        
        total_value = self.get_portfolio_value()
        invested_value = sum(pos.market_value for pos in self.positions.values())
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        realized_pnl = sum(pos.realized_pnl for pos in self.closed_positions)
        total_pnl = unrealized_pnl + realized_pnl
        
        # Calculate returns
        total_return_pct = ((total_value - self.initial_capital) / self.initial_capital) * 100
        
        # Win rate
        profitable_trades = len([t for t in self.trades if t.get('pnl', 0) > 0])
        total_trades = len(self.trades)
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Daily P&L (simplified)
        day_pnl = 0
        if len(self.daily_values) > 1:
            day_pnl = self.daily_values[-1][1] - self.daily_values[-2][1]
        
        return PortfolioMetrics(
            total_value=total_value,
            cash=self.cash,
            invested_value=invested_value,
            total_pnl=total_pnl,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            day_pnl=day_pnl,
            total_return_pct=total_return_pct,
            win_rate=win_rate,
            total_trades=total_trades,
            open_positions=len(self.positions)
        )
    
    def get_positions_summary(self) -> pd.DataFrame:
        """Get summary of all open positions"""
        if not self.positions:
            return pd.DataFrame()
        
        data = []
        for symbol, pos in self.positions.items():
            data.append({
                'Symbol': symbol,
                'Type': pos.position_type.value,
                'Quantity': pos.quantity,
                'Entry Price': pos.entry_price,
                'Current Price': pos.current_price,
                'Market Value': pos.market_value,
                'Unrealized P&L': pos.unrealized_pnl,
                'Return %': pos.get_return_pct(),
                'Days Held': pos.days_held(),
                'Stop Loss': pos.stop_loss,
                'Take Profit': pos.take_profit
            })
        
        return pd.DataFrame(data)
    
    def get_sector_allocation(self) -> Dict[str, float]:
        """Get allocation by sector (simplified by symbol prefix)"""
        if not self.positions:
            return {}
        
        total_value = sum(pos.market_value for pos in self.positions.values())
        
        sectors = {}
        for pos in self.positions.values():
            # Simplified sector classification by symbol prefix
            sector = pos.symbol[:3] if len(pos.symbol) >= 3 else pos.symbol
            if sector not in sectors:
                sectors[sector] = 0
            sectors[sector] += pos.market_value
        
        # Convert to percentages
        for sector in sectors:
            sectors[sector] = (sectors[sector] / total_value) * 100
        
        return sectors
    
    def _record_trade(self, symbol: str, action: str, quantity: int, 
                     price: float, commission: float, pnl: float = 0):
        """Record a trade for analysis"""
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'pnl': pnl,
            'portfolio_value': self.get_portfolio_value()
        }
        self.trades.append(trade)
    
    def check_stop_losses(self, current_prices: Dict[str, float]) -> List[str]:
        """Check for stop loss triggers and return symbols to close"""
        symbols_to_close = []
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                
                # Check stop loss
                if position.stop_loss:
                    if position.position_type == PositionType.LONG:
                        if current_price <= position.stop_loss:
                            symbols_to_close.append(symbol)
                    else:  # SHORT
                        if current_price >= position.stop_loss:
                            symbols_to_close.append(symbol)
                
                # Check take profit
                if position.take_profit:
                    if position.position_type == PositionType.LONG:
                        if current_price >= position.take_profit:
                            symbols_to_close.append(symbol)
                    else:  # SHORT
                        if current_price <= position.take_profit:
                            symbols_to_close.append(symbol)
        
        return symbols_to_close
    
    def rebalance_portfolio(self, target_weights: Dict[str, float], 
                          current_prices: Dict[str, float]):
        """Rebalance portfolio to target weights"""
        total_value = self.get_portfolio_value()
        
        for symbol, target_weight in target_weights.items():
            target_value = total_value * target_weight
            
            if symbol in self.positions:
                current_value = self.positions[symbol].market_value
                difference = target_value - current_value
                
                if abs(difference) > 100:  # Only rebalance if difference > $100
                    current_price = current_prices.get(symbol, self.positions[symbol].current_price)
                    shares_to_trade = int(difference / current_price)
                    
                    if shares_to_trade > 0:
                        self.add_position(symbol, shares_to_trade, current_price)
                    elif shares_to_trade < 0:
                        self.close_position(symbol, abs(shares_to_trade), current_price)
            
            elif target_weight > 0 and symbol in current_prices:
                # New position
                shares_to_buy = int(target_value / current_prices[symbol])
                if shares_to_buy > 0:
                    self.add_position(symbol, shares_to_buy, current_prices[symbol])
    
    def export_trades(self) -> pd.DataFrame:
        """Export all trades to DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trades)
    
    def print_portfolio_summary(self):
        """Print a formatted portfolio summary"""
        metrics = self.get_portfolio_metrics()
        
        print("\n" + "="*60)
        print("💼 PORTFOLIO SUMMARY")
        print("="*60)
        
        print(f"💰 Total Value: ${metrics.total_value:,.2f}")
        print(f"💵 Cash: ${metrics.cash:,.2f}")
        print(f"📈 Invested: ${metrics.invested_value:,.2f}")
        print(f"📊 Total Return: {metrics.total_return_pct:.2f}%")
        print(f"💹 Unrealized P&L: ${metrics.unrealized_pnl:,.2f}")
        print(f"💸 Realized P&L: ${metrics.realized_pnl:,.2f}")
        print(f"📅 Day P&L: ${metrics.day_pnl:,.2f}")
        
        print(f"\n📋 POSITIONS")
        print(f"🔢 Open Positions: {metrics.open_positions}")
        print(f"📦 Total Trades: {metrics.total_trades}")
        print(f"🎯 Win Rate: {metrics.win_rate:.1f}%")
        
        if self.positions:
            positions_df = self.get_positions_summary()
            print(f"\n📊 POSITION DETAILS")
            print(positions_df.to_string(index=False, float_format='%.2f'))
        
        print("="*60)