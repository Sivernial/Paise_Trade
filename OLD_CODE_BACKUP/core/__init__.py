"""Core trading engine package initialization.

Exports primary backtesting engine for external use.
"""

from .backtesting import BacktestEngine

__all__ = ["BacktestEngine"]
