
import feedparser
import logging
from datetime import datetime, timedelta
import urllib.parse

logger = logging.getLogger(__name__)

class NewsFilter:
    """
    Fetches news for a symbol and determines if it's safe to trade.
    Uses Google News RSS.
    """
    
    BASE_URL = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    NEGATIVE_KEYWORDS = [
        "crash", "plunge", "fraud", "investigation", "raid", "scam", 
        "regulatory", "ban", "lawsuit", "default", "bankruptcy", 
        "profit warning", "downgrade", "hits lower circuit", "locked"
    ]
    
    EARNINGS_KEYWORDS = [
        "results", "earnings", "quarterly", "q1", "q2", "q3", "q4", "profit", "revenue"
    ]
    
    def __init__(self):
        pass
        
    def can_trade(self, symbol: str, strategy_type: str = "MEAN_REVERSION") -> bool:
        """
        Returns True if safe to trade, False if high risk news detected.
        """
        try:
            # Construct Query: "TATAMOTORS share news"
            query = urllib.parse.quote(f"{symbol} share news")
            url = self.BASE_URL.format(query=query)
            
            feed = feedparser.parse(url)
            
            if not feed.entries:
                logger.warning(f"No news found for {symbol}")
                return True # Fail open (allow trade)
            
            current_time = datetime.now()
            
            for entry in feed.entries[:5]: # Check top 5 news
                title = entry.title.lower()
                pub_date = entry.get('published_parsed')
                
                # Check timeframe (Last 24 hours)
                if pub_date:
                    article_time = datetime(*pub_date[:6])
                    if (current_time - article_time) > timedelta(hours=24):
                        continue
                
                # 1. Check Negative Keywords (Panic selling)
                for kw in self.NEGATIVE_KEYWORDS:
                    if kw in title:
                        logger.warning(f"🚨 NEWS FILTER: Blocking {symbol} due to negative news: '{entry.title}'")
                        return False
                
                # 2. Check Earnings (Volatility Risk)
                # If doing Mean Reversion, avoid earnings day as spread can widen permanently
                if strategy_type == "MEAN_REVERSION":
                    for kw in self.EARNINGS_KEYWORDS:
                        if kw in title:
                            logger.info(f"⚠️ NEWS FILTER: Caution {symbol} due to earnings news: '{entry.title}'")
                            # We might strict block or just warn. Returns False for safety.
                            return False
                            
            return True
            
        except Exception as e:
            logger.error(f"News Filter Error for {symbol}: {e}")
            return True # Fail open
