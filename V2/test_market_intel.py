
import sys
import os
import logging

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Market_Intelligence.sentiment_analyzer import MarketIntelligence

# Configure Logging
logging.basicConfig(level=logging.INFO)

def test_intel():
    print("Testing Market Intelligence...")
    
    mi = MarketIntelligence()
    
    symbols = ["TCS", "INFY", "ADANIENT", "ZOMATO"]
    
    for sym in symbols:
        print(f"\n--- Analyzing {sym} ---")
        sentiment = mi.get_sentiment(f"{sym} share news")
        print(f"Score: {sentiment['score']}")
        print(f"Regime: {sentiment['regime']}")
        print(f"Summary: {sentiment.get('article_count', 0)} articles")
        
        can_trade = mi.can_trade(sym)
        print(f"Can Trade? {can_trade}")

if __name__ == "__main__":
    test_intel()
