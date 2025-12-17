
import feedparser
import logging
from datetime import datetime, timedelta
import urllib.parse
import re

logger = logging.getLogger(__name__)

class MarketIntelligence:
    """
    Analyzes Public Data (News, RSS) to determine Market Regime and Asset Sentiment.
    """
    
    RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    # Sentiment Keywords (Expanded for better capture)
    BEARISH_KEYWORDS = [
        "crash", "plunge", "collapse", "crisis", "bear", "sell-off", "down", 
        "losses", "fear", "recession", "inflation", "war", "ban", "fraud", 
        "investigation", "scam", "default", "bankruptcy", "downgrade", "lower circuit",
        "weak", "miss", "disappoint", "hit", "fall", "drops", "sink"
    ]
    
    BULLISH_KEYWORDS = [
        "surge", "rally", "record", "bull", "growth", "profit", "gain", 
        "optimism", "upgrade", "breakout", "high", "positive", "strong", 
        "beat", "jump", "soar", "climb", "recover", "buy", "deal"
    ]
    
    def __init__(self):
        pass
        
    def get_sentiment(self, query: str) -> dict:
        """
        Returns {'score': float, 'summary': str}
        Score: -1.0 (Bearish) to 1.0 (Bullish). 0 is Neutral.
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = self.RSS_URL.format(query=encoded_query)
            feed = feedparser.parse(url)
            
            if not feed.entries:
                return {'score': 0.0, 'summary': 'No News'}
            
            sentiment_score = 0
            article_count = 0
            start_time = datetime.now()
            
            # Analyze last 24h news
            for entry in feed.entries[:10]: # Top 10 articles
                title = entry.title.lower()
                pub_date = entry.get('published_parsed')
                
                if pub_date:
                    article_time = datetime(*pub_date[:6])
                    if (start_time - article_time) > timedelta(hours=24):
                        continue
                
                # Keyword Counting
                bear_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in title)
                bull_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in title)
                
                if bear_count > bull_count:
                    sentiment_score -= 1
                elif bull_count > bear_count:
                    sentiment_score += 1
                    
                article_count += 1
            
            if article_count == 0:
                return {
                    'score': 0.0, 
                    'regime': 'NEUTRAL',
                    'article_count': 0,
                    'summary': 'No Recent News'
                }
            
            # Normalize Score (-1 to 1)
            final_score = max(-1.0, min(1.0, sentiment_score / max(1, article_count)))
            
            regime = "NEUTRAL"
            if final_score > 0.3: regime = "BULLISH"
            if final_score < -0.3: regime = "BEARISH"
            
            return {
                'score': final_score,
                'regime': regime,
                'article_count': article_count
            }
            
        except Exception as e:
            logger.error(f"Sentiment Analysis Failed: {e}")
            return {'score': 0.0, 'regime': 'NEUTRAL', 'error': str(e)}

    def can_trade(self, symbol: str) -> bool:
        """
        Checks if the asset is safe to trade (Not Extremely Bearish).
        """
        # Specific Query for the stock
        sentiment = self.get_sentiment(f"{symbol} share news")
        
        # Block if sentiment is strongly negative (< -0.5)
        # This catches things like "Stock crashes 10% after fraud allegation"
        if sentiment['score'] <= -0.5:
            logger.warning(f"🚫 BLOCKED {symbol}: Extreme Negative Sentiment ({sentiment['score']:.2f})")
            return False
            
        logger.info(f"✅ {symbol} Sentiment OK ({sentiment['score']:.2f})")
        return True
