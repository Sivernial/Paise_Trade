from typing import Dict
from kiteconnect import KiteConnect
from Common import Position
import logging

logger = logging.getLogger(__name__)

class LivePortfolio:
    
    def __init__(self, kite: KiteConnect):
        self.kite = kite
    
    def get_positions(self) -> Dict[str, Position]:
        try:
            positions_data = self.kite.positions()
            positions = {}
            
            for pos_data in positions_data.get('net', []):
                if pos_data['quantity'] != 0:
                    symbol = pos_data['tradingsymbol']
                    positions[symbol] = Position(
                        symbol=symbol,
                        quantity=pos_data['quantity'],
                        entry_price=pos_data['average_price'],
                        entry_date=None,
                        current_price=pos_data['last_price'],
                        unrealized_pnl=pos_data['pnl']
                    )
            
            return positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return {}
    
    def get_holdings(self) -> list:
        try:
            return self.kite.holdings()
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return []
    
    def get_margins(self) -> dict:
        try:
            return self.kite.margins()
        except Exception as e:
            logger.error(f"Error fetching margins: {e}")
            return {}

