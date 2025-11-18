from .base_action import BaseAction
from Common import TransactionType, OrderType, ProductType
import logging

logger = logging.getLogger(__name__)

class BuyInstant(BaseAction):
    
    def execute(self, symbol: str, quantity: int, exchange: str = "NSE",
               product: str = "MIS", **kwargs) -> str:
        
        self.validate_order(symbol, quantity)
        
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=TransactionType.BUY.value,
                quantity=quantity,
                product=product,
                order_type=OrderType.MARKET.value
            )
            
            logger.info(f"Buy market order placed: {order_id} for {quantity} {symbol}")
            return order_id
            
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
            raise

