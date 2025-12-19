
import yfinance as yf
import pandas as pd

def test_fundamentals():
    symbols = ["TCS.NS", "TATAMOTORS.NS", "INFY.NS"]
    print("Fetching fundamentals for:", symbols)
    
    for sym in symbols:
        ticker = yf.Ticker(sym)
        info = ticker.info
        
        mkt_cap = info.get('marketCap', 0)
        book_val = info.get('bookValue', 0)
        price = info.get('currentPrice', 0)
        
        bm_ratio = 0
        if price > 0 and book_val > 0:
            bm_ratio = book_val / price
            
        print(f"\n{sym}:")
        print(f"  Market Cap: {mkt_cap / 1e7:.2f} Cr")
        print(f"  Book Value: {book_val}")
        print(f"  B/M Ratio: {bm_ratio:.4f}")

if __name__ == "__main__":
    test_fundamentals()
