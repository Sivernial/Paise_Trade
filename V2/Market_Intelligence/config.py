class MIConfig:
    # Sources
    RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    # Timeouts
    REQUEST_TIMEOUT = 10
    CACHE_EXPIRY = 900 # 15 minutes
    
    # Event Keywords
    KEYWORDS = {
        'EARNINGS': ['earnings', 'quarterly results', 'profit', 'revenue', 'q1', 'q2', 'q3', 'q4', 'dividend'],
        'SCANDAL': ['fraud', 'scam', 'raid', 'investigation', 'ed', 'cbi', 'sebi', 'default', 'arrest'],
        'MERGER': ['merger', 'acquisition', 'stake', 'buyout', 'takeover'],
        'MACRO': ['inflation', 'rbi', 'rate hike', 'repo rate', 'gdp', 'budget', 'fiscal'],
        'REGULATORY': ['tax', 'duty', 'gst', 'levy', 'cess', 'ban', 'fine', 'penalty', 'court', 'verdict']
    }
    
    # Sentiment Lexicon (Simple)
    BEARISH = [
        "crash", "plunge", "collapse", "crisis", "bear", "sell-off", "down", 
        "losses", "fear", "recession", "war", "ban", "downgrade", "lower circuit",
        "weak", "miss", "disappoint", "hit", "fall", "drops", "sink",
        "tax", "duty", "hike", "fine", "penalty" # Added tax terms as generally negative for price
    ]
    
    BULLISH = [
        "surge", "rally", "record", "bull", "growth", "profit", "gain", 
        "optimism", "upgrade", "breakout", "high", "positive", "strong", 
        "beat", "jump", "soar", "climb", "recover", "buy", "deal"
    ]
