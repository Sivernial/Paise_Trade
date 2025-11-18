from .base_action import BaseAction
import logging

logger = logging.getLogger(__name__)

class CancelOrder(BaseAction):
    
    def execute(self, order_id: str, variety: str = "regular", **kwargs) -> bool:
        
        if not order_id:
            raise ValueError("Invalid order_id")
        
        try:
            self.kite.cancel_order(
                variety=variety,
                order_id=order_id
            )
            
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise

