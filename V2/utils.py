import logging
from config import config

def setup_logging(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(config.LOG_LEVEL)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(config.LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def format_currency(value: float) -> str:
    return f"₹{value:,.2f}"

def format_percentage(value: float) -> str:
    return f"{value:.2%}"

def validate_symbol(symbol: str) -> bool:
    return symbol and symbol.isalnum() and len(symbol) <= 20

def calculate_position_size(capital: float, price: float, 
                           max_position_pct: float = 0.1) -> int:
    max_investment = capital * max_position_pct
    quantity = int(max_investment / price)
    return max(1, quantity)

