import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from login import get_kite_instance
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_index_symbols(search_term="NIFTY"):
    kite = get_kite_instance()
    if not kite:
        logger.error("Failed to initialize Kite connection")
        return
    
    print(f"\n{'='*80}")
    print(f"Searching for symbols containing: '{search_term}'")
    print(f"{'='*80}\n")
    
    # Try different exchanges
    exchanges = ["NSE", "NFO", "BSE", "BFO"]
    
    all_matches = []
    
    for exchange in exchanges:
        try:
            print(f"📊 Checking {exchange}...")
            instruments = kite.instruments(exchange)
            
            matches = [
                inst for inst in instruments 
                if search_term.upper() in inst.get('tradingsymbol', '').upper()
            ]
            
            if matches:
                print(f"✅ Found {len(matches)} matches in {exchange}:")
                for match in matches[:10]:  # Show first 10
                    print(f"   Symbol: {match['tradingsymbol']:<20} | "
                          f"Name: {match.get('name', 'N/A'):<30} | "
                          f"Token: {match['instrument_token']}")
                    all_matches.append({
                        'exchange': exchange,
                        'symbol': match['tradingsymbol'],
                        'name': match.get('name', 'N/A'),
                        'token': match['instrument_token'],
                        'instrument_type': match.get('instrument_type', 'N/A')
                    })
                
                if len(matches) > 10:
                    print(f"   ... and {len(matches) - 10} more")
                print()
        except Exception as e:
            print(f"❌ Error checking {exchange}: {e}\n")
    
    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY - Recommended symbols for market filter:")
    print(f"{'='*80}\n")
    
    # Look for spot indices (not futures/options)
    spot_indices = [m for m in all_matches if 'EQ' in m.get('instrument_type', '') or m['instrument_type'] == 'N/A']
    
    if not spot_indices:
        spot_indices = all_matches
    
    for match in spot_indices[:5]:
        print(f"Symbol: '{match['symbol']}' on {match['exchange']}")
        print(f"  → Use this in config: SYMBOLS = [..., '{match['symbol']}']")
        print(f"  → Token: {match['token']}\n")
    
    return all_matches


if __name__ == "__main__":
    import sys
    
    search_term = "NIFTY"
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
    
    matches = find_index_symbols(search_term)
    
    print(f"\n💡 TIP: Run this script with different search terms:")
    print(f"   python find_index_symbol.py NIFTY")
    print(f"   python find_index_symbol.py SENSEX")
    print(f"   python find_index_symbol.py BANKNIFTY")
    print()

