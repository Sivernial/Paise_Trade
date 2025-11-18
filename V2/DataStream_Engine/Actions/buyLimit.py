from .base_action import BaseAction
from Common import TransactionType, OrderType
import logging

logger = logging.getLogger(__name__)

class BuyLimit(BaseAction):
    
    def execute(self, symbol: str, quantity: int, price: float,
               exchange: str = "NSE", product: str = "MIS", **kwargs) -> str:
        
        self.validate_order(symbol, quantity, price)
        
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=TransactionType.BUY.value,
                quantity=quantity,
                product=product,
                order_type=OrderType.LIMIT.value,
                price=price
            )
            
            logger.info(f"Buy limit order placed: {order_id} for {quantity} {symbol} @ {price}")
            return order_id
            
        except Exception as e:
            logger.error(f"Error placing buy limit order: {e}")
            raise

