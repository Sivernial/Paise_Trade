import sys
import os
import logging

# Add V2 to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from Market_Intelligence.engine import IntelligenceEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mi():
    print("🚀 Testing Market Intelligence Layer...")
    
    eng = IntelligenceEngine()
    fake_symbol = "TATASTEEL"
    
    print(f"1. Fetching News for {fake_symbol}...")
    sig = eng.fetch_signals_sync(fake_symbol)
    
    if sig:
        print(f"✅ Signal Received:\n {sig.model_dump_json(indent=2)}")
    else:
        print("⚠️ No signal fetched (Network issue? No news?)")
        
    print("\n2. Testing Fast Retrieval (Cache/DB)...")
    cached_sig = eng.get_signal(fake_symbol)
    print(f"✅ Cached Signal Score: {cached_sig.sentiment_score}")
    print(f"✅ Cached Signal Summary: {cached_sig.summary}")

if __name__ == "__main__":
    test_mi()
