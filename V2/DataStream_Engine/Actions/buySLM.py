from .base_action import BaseAction
from Common import TransactionType, OrderType
from Common.quant_utils import round_to_tick
import logging

logger = logging.getLogger(__name__)

class BuySLM(BaseAction):
    
    def execute(self, symbol: str, quantity: int, trigger_price: float,
               exchange: str = "NSE", product: str = "MIS", **kwargs) -> str:
        
        # Safety rounding for tick size
        trigger_price = round_to_tick(trigger_price)
        self.validate_order(symbol, quantity, trigger_price)
        
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=TransactionType.BUY.value,
                quantity=quantity,
                product=product,
                order_type="SL-M",
                trigger_price=trigger_price
            )
            
            logger.info(f"Buy SL-M order placed: {order_id} for {quantity} {symbol} @ Trigger: {trigger_price}")
            return order_id
            
        except Exception as e:
            logger.error(f"Error placing Buy SL-M order: {e}")
            raise
