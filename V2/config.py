import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    
    DB_PATH = "trading_data_v2.db"
    
    BACKTEST_INITIAL_CAPITAL = 100000
    BACKTEST_COMMISSION_RATE = 0.001
    
    PAPER_INITIAL_CAPITAL = 100000
    
    MAX_POSITION_SIZE_PCT = 0.1
    MAX_DAILY_LOSS_PCT = 0.05
    
    DEFAULT_EXCHANGE = "NSE"
    DEFAULT_PRODUCT = "MIS"
    
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

config = Config()

