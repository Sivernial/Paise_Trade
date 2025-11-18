#!/usr/bin/env python3
"""
Quick Start Script for Paise Trade Algorithmic Trading System
Run this script to get started with the trading system
"""

import os
import sys
from datetime import datetime

def print_banner():
    """Print welcome banner"""
    print("="*80)
    print("🚀 PAISE TRADE - ALGORITHMIC TRADING SYSTEM")
    print("="*80)
    print("Welcome to your personal algorithmic trading platform!")
    print("This system provides comprehensive tools for:")
    print("• Backtesting trading strategies")
    print("• Paper trading for risk-free testing")
    print("• Live trading with Zerodha Kite API")
    print("• Technical analysis and indicators")
    print("• Portfolio management and risk controls")
    print("="*80)

def check_requirements():
    """Check if required packages are installed"""
    print("\n🔍 Checking System Requirements...")
    
    missing_packages = []
    required_packages = [
        'pandas', 'numpy', 'kiteconnect', 'flask', 'python-dotenv'
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("📦 Install them with: pip install -r requirements.txt")
        return False
    
    print("\n✅ All required packages are installed!")
    return True

def check_configuration():
    """Check if configuration files exist"""
    print("\n⚙️ Checking Configuration...")
    
    config_items = [
        ('.env', 'Environment variables file'),
        ('core/', 'Core modules directory'),
    ]
    
    all_good = True
    for item, description in config_items:
        if os.path.exists(item):
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - Missing")
            all_good = False
    
    # Check .env file contents
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_content = f.read()
            
        if 'API_KEY=' in env_content:
            print("✅ API_KEY configured")
        else:
            print("⚠️ API_KEY not configured in .env")
            all_good = False
        
        if 'API_SECRET=' in env_content:
            print("✅ API_SECRET configured")
        else:
            print("⚠️ API_SECRET not configured in .env")
            all_good = False
    
    return all_good

def setup_environment():
    """Setup the trading environment"""
    print("\n🛠️ Setting Up Environment...")
    
    # Create config directory if it doesn't exist
    if not os.path.exists('config'):
        os.makedirs('config')
        print("✅ Created config directory")
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        env_template = '''# Zerodha API Credentials
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
REDIRECT_URL=http://127.0.0.1:8000

# Trading Settings
INITIAL_CAPITAL=100000
PAPER_TRADING=true
LOG_LEVEL=INFO

# Optional Settings
MAX_POSITIONS=10
MAX_DAILY_LOSS_PCT=0.05
'''
        with open('.env', 'w') as f:
            f.write(env_template)
        
        print("✅ Created .env template file")
        print("⚠️ Please update .env file with your Zerodha API credentials")
    
    print("✅ Environment setup complete!")

def run_demo():
    """Run the trading system demo"""
    print("\n🎯 Running Trading System Demo...")
    
    try:
        # Import demo after checking requirements
        from demo_trading_system import main as demo_main
        
        print("Starting comprehensive demo...")
        results = demo_main()
        
        if results:
            print("\n✅ Demo completed successfully!")
            return True
        else:
            print("\n⚠️ Demo completed with warnings")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all required packages are installed")
        return False
    except Exception as e:
        print(f"❌ Demo error: {e}")
        return False

def show_next_steps():
    """Show next steps for the user"""
    print("\n📚 NEXT STEPS:")
    print("="*50)
    print("1. 🔐 Setup Zerodha API:")
    print("   • Visit https://kite.trade/")
    print("   • Create a developer account")
    print("   • Get API key and secret")
    print("   • Update .env file with credentials")
    
    print("\n2. 🔑 Get Access Token:")
    print("   • Run: python login.py")
    print("   • Complete the authentication flow")
    
    print("\n3. 🧪 Test with Paper Trading:")
    print("   • Keep PAPER_TRADING=true in .env")
    print("   • Run strategies safely without real money")
    
    print("\n4. 📈 Develop Your Strategy:")
    print("   • Study existing strategies in core/strategy.py")
    print("   • Create your own strategy class")
    print("   • Backtest thoroughly before live trading")
    
    print("\n5. 📊 Analyze Performance:")
    print("   • Use backtesting engine for historical analysis")
    print("   • Monitor portfolio performance")
    print("   • Adjust risk parameters as needed")
    
    print("\n6. 🚀 Go Live (When Ready):")
    print("   • Set PAPER_TRADING=false in .env")
    print("   • Start with small position sizes")
    print("   • Monitor closely and adjust as needed")
    
    print("\n📖 RESOURCES:")
    print("• README.md - Complete documentation")
    print("• demo_trading_system.py - Working examples")
    print("• core/ - All trading modules with detailed comments")
    print("• Zerodha Kite API docs: https://kite.trade/docs/")

def main():
    """Main function to run the quick start"""
    print_banner()
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Please install missing packages and try again")
        sys.exit(1)
    
    # Check configuration
    config_ok = check_configuration()
    
    # Setup environment if needed
    if not config_ok:
        setup_environment()
    
    # Ask user if they want to run demo
    print("\n🎯 Would you like to run the trading system demo?")
    print("This will show all features with synthetic data (no real trading)")
    
    response = input("Run demo? (y/n): ").lower().strip()
    
    if response == 'y' or response == 'yes':
        demo_success = run_demo()
        
        if demo_success:
            print("\n🎉 Great! The demo shows the system is working correctly.")
        else:
            print("\n⚠️ Demo had some issues, but the system should still work.")
    else:
        print("\n⏭️ Skipping demo")
    
    # Show next steps
    show_next_steps()
    
    print(f"\n🎯 Quick Start completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Happy Trading! 🚀📈")

if __name__ == "__main__":
    main()