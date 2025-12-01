from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd
from datetime import datetime
from Common import Signal
from Technical_Indicators import StaticIndicators, DynamicIndicators

class BaseStrategy(ABC):
    
    def __init__(self, params: dict = None):
        self.params = params or {}
        self.static_ind = StaticIndicators()
        self.static_ind = StaticIndicators()
        self.dynamic_ind = DynamicIndicators()
        self.positions = {}
    
    def update_positions(self, positions: dict):
        self.positions = positions
    
    @abstractmethod
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime) -> List[Signal]:
        pass
    
    def get_latest_value(self, series: pd.Series) -> float:
        if len(series) > 0:
            return series.iloc[-1]
        return 0.0
    
    def is_bullish_crossover(self, fast: pd.Series, slow: pd.Series) -> bool:
        if len(fast) < 2 or len(slow) < 2:
            return False
        return fast.iloc[-1] > slow.iloc[-1] and fast.iloc[-2] <= slow.iloc[-2]
    
    def is_bearish_crossover(self, fast: pd.Series, slow: pd.Series) -> bool:
        if len(fast) < 2 or len(slow) < 2:
            return False
        return fast.iloc[-1] < slow.iloc[-1] and fast.iloc[-2] >= slow.iloc[-2]

