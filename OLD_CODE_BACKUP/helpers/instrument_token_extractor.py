#!/usr/bin/env python3
"""
Instrument Token Extractor for Zerodha Kite API
Helps find instrument tokens for stocks/symbols for trading and data fetching
"""

import csv
import json
import os
import sys
import urllib.request
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class InstrumentTokenExtractor:
    """
    Extract instrument tokens for trading symbols from Zerodha Kite
    
    Features:
    - Download latest instruments list from Zerodha
    - Search by symbol name (fuzzy matching)
    - Filter by exchange (NSE, BSE, MCX, etc.)
    - Cache instruments data locally
    - Support for equity, futures, options
    """
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize the extractor
        
        Args:
            cache_dir: Directory to store cached instruments data
        """
        self.cache_dir = os.path.join(os.path.dirname(__file__), cache_dir)
        self.instruments_file = os.path.join(self.cache_dir, "instruments.csv")
        self.instruments_data: List[Dict] = []
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Zerodha instruments download URL
        self.instruments_url = "https://api.kite.trade/instruments"
    
    def download_instruments(self, force_refresh: bool = False) -> bool:
        """
        Download latest instruments list from Zerodha
        
        Args:
            force_refresh: Force download even if cache exists
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            # Check if cache exists and is recent (less than 1 day old)
            if not force_refresh and os.path.exists(self.instruments_file):
                file_age = datetime.now().timestamp() - os.path.getmtime(self.instruments_file)
                if file_age < 86400:  # 24 hours
                    print(f"📋 Using cached instruments (age: {file_age/3600:.1f} hours)")
                    return True
            
            print("📡 Downloading latest instruments from Zerodha...")
            
            # Download instruments CSV
            with urllib.request.urlopen(self.instruments_url) as response:
                if response.status == 200:
                    with open(self.instruments_file, 'wb') as f:
                        f.write(response.read())
                    print(f"✅ Downloaded instruments to {self.instruments_file}")
                    return True
                else:
                    print(f"❌ Failed to download instruments: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error downloading instruments: {e}")
            return False
    
    def load_instruments(self) -> bool:
        """
        Load instruments data from CSV file
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.instruments_file):
                print("📋 Instruments file not found, downloading...")
                if not self.download_instruments():
                    return False
            
            self.instruments_data = []
            
            with open(self.instruments_file, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    self.instruments_data.append(row)
            
            print(f"📊 Loaded {len(self.instruments_data)} instruments")
            return True
            
        except Exception as e:
            print(f"❌ Error loading instruments: {e}")
            return False
    
    def search_symbol(self, 
                     symbol: str, 
                     exchange: Optional[str] = None,
                     segment: Optional[str] = None,
                     instrument_type: Optional[str] = None) -> List[Dict]:
        """
        Search for instruments by symbol name
        
        Args:
            symbol: Symbol to search for (e.g., 'TITAN', 'RELIANCE')
            exchange: Filter by exchange (NSE, BSE, MCX, etc.)
            segment: Filter by segment (EQ, FO, etc.)
            instrument_type: Filter by type (EQ, FUT, CE, PE, etc.)
            
        Returns:
            List of matching instruments
        """
        if not self.instruments_data:
            if not self.load_instruments():
                return []
        
        symbol = symbol.upper().strip()
        matches = []
        
        for instrument in self.instruments_data:
            # Check symbol match (exact or fuzzy)
            trading_symbol = instrument.get('tradingsymbol', '').upper()
            name = instrument.get('name', '').upper()
            
            symbol_match = (
                symbol == trading_symbol or
                symbol in trading_symbol or
                symbol in name or
                trading_symbol.startswith(symbol)
            )
            
            if not symbol_match:
                continue
            
            # Apply filters
            if exchange and instrument.get('exchange', '').upper() != exchange.upper():
                continue
                
            if segment and instrument.get('segment', '').upper() != segment.upper():
                continue
                
            if instrument_type and instrument.get('instrument_type', '').upper() != instrument_type.upper():
                continue
            
            matches.append(instrument)
        
        # Sort by relevance (exact matches first)
        matches.sort(key=lambda x: (
            x.get('tradingsymbol', '').upper() != symbol,  # Exact matches first
            x.get('exchange', '') != 'NSE',  # Prefer NSE
            x.get('instrument_type', '') != 'EQ',  # Prefer equity
            x.get('tradingsymbol', '')
        ))
        
        return matches
    
    def get_token(self, 
                  symbol: str,
                  exchange: str = "NSE",
                  instrument_type: str = "EQ") -> Optional[str]:
        """
        Get instrument token for a specific symbol
        
        Args:
            symbol: Trading symbol (e.g., 'TITAN')
            exchange: Exchange name (default: NSE)
            instrument_type: Instrument type (default: EQ)
            
        Returns:
            Instrument token as string, None if not found
        """
        matches = self.search_symbol(
            symbol=symbol,
            exchange=exchange,
            instrument_type=instrument_type
        )
        
        if matches:
            return matches[0].get('instrument_token')
        return None
    
    def get_instrument_details(self, symbol: str) -> Optional[Dict]:
        """
        Get complete instrument details for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Complete instrument details or None
        """
        matches = self.search_symbol(symbol)
        return matches[0] if matches else None
    
    def print_search_results(self, matches: List[Dict], limit: int = 10):
        """
        Print search results in a formatted table
        
        Args:
            matches: List of instrument matches
            limit: Maximum results to display
        """
        if not matches:
            print("❌ No instruments found")
            return
        
        print(f"\n📊 Found {len(matches)} instruments:")
        print("-" * 100)
        print(f"{'Symbol':<15} {'Token':<12} {'Exchange':<8} {'Type':<6} {'Name':<45}")
        print("-" * 100)
        
        for i, instrument in enumerate(matches[:limit]):
            symbol = instrument.get('tradingsymbol', '')[:14]
            token = instrument.get('instrument_token', '')
            exchange = instrument.get('exchange', '')
            inst_type = instrument.get('instrument_type', '')
            name = instrument.get('name', '')[:44]
            
            print(f"{symbol:<15} {token:<12} {exchange:<8} {inst_type:<6} {name:<45}")
        
        if len(matches) > limit:
            print(f"... and {len(matches) - limit} more results")
    
    def save_favorites(self, symbols: List[str], filename: str = "favorites.json"):
        """
        Save favorite symbols with their tokens
        
        Args:
            symbols: List of symbols to save
            filename: File to save favorites
        """
        favorites = {}
        
        for symbol in symbols:
            details = self.get_instrument_details(symbol)
            if details:
                favorites[symbol] = {
                    'token': details.get('instrument_token'),
                    'exchange': details.get('exchange'),
                    'name': details.get('name'),
                    'type': details.get('instrument_type')
                }
        
        favorites_file = os.path.join(self.cache_dir, filename)
        with open(favorites_file, 'w') as f:
            json.dump(favorites, f, indent=2)
        
        print(f"💾 Saved {len(favorites)} favorites to {favorites_file}")


def main():
    """Interactive command-line interface"""
    print("🔍 ZERODHA INSTRUMENT TOKEN EXTRACTOR")
    print("=" * 50)
    
    extractor = InstrumentTokenExtractor()
    
    # Download/load instruments
    if not extractor.load_instruments():
        print("❌ Failed to load instruments data")
        return
    
    print("\nCommands:")
    print("  search <symbol>     - Search for instruments")
    print("  token <symbol>      - Get token for symbol")
    print("  refresh             - Refresh instruments data")
    print("  favorites           - Manage favorite symbols")
    print("  quit                - Exit")
    
    while True:
        try:
            command = input("\n🔍 Enter command: ").strip().lower()
            
            if command == 'quit' or command == 'exit':
                break
            
            elif command == 'refresh':
                extractor.download_instruments(force_refresh=True)
                extractor.load_instruments()
            
            elif command == 'favorites':
                symbols_input = input("Enter symbols (comma-separated): ")
                symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
                if symbols:
                    extractor.save_favorites(symbols)
            
            elif command.startswith('search '):
                symbol = command[7:].strip().upper()
                if symbol:
                    matches = extractor.search_symbol(symbol)
                    extractor.print_search_results(matches)
            
            elif command.startswith('token '):
                symbol = command[6:].strip().upper()
                if symbol:
                    token = extractor.get_token(symbol)
                    if token:
                        details = extractor.get_instrument_details(symbol)
                        print(f"\n✅ {symbol} Token: {token}")
                        if details:
                            print(f"   Exchange: {details.get('exchange')}")
                            print(f"   Name: {details.get('name')}")
                            print(f"   Type: {details.get('instrument_type')}")
                    else:
                        print(f"❌ Token not found for {symbol}")
                        # Show similar matches
                        matches = extractor.search_symbol(symbol)
                        if matches:
                            print(f"\n💡 Did you mean one of these?")
                            extractor.print_search_results(matches, limit=5)
            
            else:
                # Direct symbol search
                if command:
                    symbol = command.upper()
                    token = extractor.get_token(symbol)
                    if token:
                        print(f"✅ {symbol} Token: {token}")
                    else:
                        matches = extractor.search_symbol(symbol)
                        extractor.print_search_results(matches, limit=5)
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


# Example usage functions
def get_popular_stocks_tokens():
    """Get tokens for popular Indian stocks"""
    extractor = InstrumentTokenExtractor()
    extractor.load_instruments()
    
    popular_stocks = [
        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
        'ICICIBANK', 'SBIN', 'BHARTIARTL', 'ITC', 'LT',
        'ASIANPAINT', 'MARUTI', 'TITAN', 'WIPRO', 'HCLTECH'
    ]
    
    print("📈 POPULAR STOCKS TOKENS")
    print("-" * 40)
    
    tokens = {}
    for symbol in popular_stocks:
        token = extractor.get_token(symbol)
        tokens[symbol] = token
        status = "✅" if token else "❌"
        print(f"{status} {symbol:<12} : {token or 'NOT FOUND'}")
    
    return tokens


if __name__ == "__main__":
    # Run interactive mode if called directly
    if len(sys.argv) > 1:
        # Command line usage
        symbol = sys.argv[1].upper()
        extractor = InstrumentTokenExtractor()
        extractor.load_instruments()
        
        token = extractor.get_token(symbol)
        if token:
            print(f"{symbol}: {token}")
        else:
            print(f"Token not found for {symbol}")
            matches = extractor.search_symbol(symbol)
            if matches:
                print("Similar symbols found:")
                extractor.print_search_results(matches, limit=3)
    else:
        # Interactive mode
        main()