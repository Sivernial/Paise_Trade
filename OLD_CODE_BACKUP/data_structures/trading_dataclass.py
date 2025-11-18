"""
Dataclasses for Trading Engine
Contains all data structures used in the trading engine module
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .common import OrderType, OrderStatus, TransactionType, ProductType, Order

# Trading dataclass file now uses unified Order from common.py
# All order-related functionality has been consolidated