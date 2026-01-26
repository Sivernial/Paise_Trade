import yfinance as yf
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SYMBOLS = [
    "SILVERBEES.NS", "GOLDBEES.NS", "NIFTYBEES.NS",
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "HINDUNILVR.NS", 
    "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", 
    "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS", 
    "ADANIENT.NS", "ADANIPORTS.NS", "HCLTECH.NS", "ONGC.NS", "NTPC.NS", "TATASTEEL.NS", 
    "POWERGRID.NS", "M&M.NS", "WIPRO.NS", "TATACOMM.NS", "JSWSTEEL.NS", "GRASIM.NS", 
    "HDFCLIFE.NS", "SBILIFE.NS", "INDUSINDBK.NS", "ADANIPOWER.NS", "TMPV.NS", 
    "COALINDIA.NS", "BPCL.NS", "EICHERMOT.NS", "DRREDDY.NS", "BAJAJ-AUTO.NS", "TECHM.NS", 
    "CIPLA.NS", "BRITANNIA.NS", "HINDALCO.NS", "NESTLEIND.NS", "BAJAJFINSV.NS", "VBL.NS", 
    "ADANIGREEN.NS", "ADANIENSOL.NS", "DLF.NS", "HAL.NS", "BEL.NS", "SIEMENS.NS", "ABB.NS", 
    "TRENT.NS", "JIOFIN.NS", "DIVISLAB.NS", "TATACONSUM.NS", "APOLLOHOSP.NS", 
    "LTIM.NS", "SHREECEM.NS", "BAJAJHLDNG.NS", "PIDILITIND.NS", "MARICO.NS", "GODREJCP.NS", 
    "GAIL.NS", "TATAELXSI.NS", "POLYCAB.NS", "CHOLAFIN.NS", "SRF.NS", "HAVELLS.NS", 
    "HEROMOTOCO.NS", "COLPAL.NS", "MUTHOOTFIN.NS", "AUBANK.NS", "IDFCFIRSTB.NS", "PNB.NS", 
    "BANKBARODA.NS", "UNIONBANK.NS", "CANBK.NS", "FEDERALBNK.NS", "MAXHEALTH.NS", 
    "LUPIN.NS", "AUROPHARMA.NS", "TVSMOTOR.NS", "ASHOKLEY.NS", "CUMMINSIND.NS", "VOLTAS.NS",
    "INDIGO.NS", "IDEA.NS", "YESBANK.NS", "PAYTM.NS", "RVNL.NS", "IRFC.NS", "MAZDOCK.NS","TMCV.NS","ETERNAL.NS","ABLBL.NS",
    "KAYNES.NS","SUZLON.NS"
]

def calculate_technical_factors(df, period=14):
    if len(df) < period + 5: return 0, 0
    
    df = df.copy()
    
    # 1. ATR (Volatility %)
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()
    atr_percent = (df['ATR'].iloc[-1] / df['Close'].iloc[-1]) * 100
    
    # 2. ADX (Trend Strength)
    df['up'] = df['High'] - df['High'].shift(1)
    df['down'] = df['Low'].shift(1) - df['Low']
    df['+DM'] = np.where((df['up'] > df['down']) & (df['up'] > 0), df['up'], 0)
    df['-DM'] = np.where((df['down'] > df['up']) & (df['down'] > 0), df['down'], 0)
    
    def wilder_smooth(series, n):
        return series.ewm(alpha=1/n, adjust=False).mean()
        
    tr_smooth = wilder_smooth(df['TR'], period)
    plus_dm_smooth = wilder_smooth(df['+DM'], period)
    minus_dm_smooth = wilder_smooth(df['-DM'], period)
    
    # Avoid division by zero
    tr_smooth = tr_smooth.replace(0, np.nan)
    
    plus_di = 100 * (plus_dm_smooth / tr_smooth)
    minus_di = 100 * (minus_dm_smooth / tr_smooth)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)
    adx = wilder_smooth(dx, period).iloc[-1]
    
    return adx, atr_percent

def get_v3_performance(symbols, lookback_days=126):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days + 60)
    
    all_tickers = symbols
    logger.info(f"Downloading data for {len(all_tickers)} tickers...")
    data = yf.download(all_tickers, start=start_date, end=end_date, interval="1d", group_by='ticker', progress=False)
    
    performance_list = []
    
    for symbol in symbols:
        if symbol not in data: continue
        
        try:
            df = data[symbol].dropna()
            if len(df) < 22: continue
            
            close = df['Close']
            volume = df['Volume']
            
            # --- V3 METRICS ---
            
            # 1. 1-Week Momentum (Recency)
            # Use last 5 trading days
            one_week_return = (close.iloc[-1] / close.iloc[-5]) - 1
            
            # 2. Relative Volume (RVol) - Institutional Interest
            # Are people trading this NOW?
            avg_vol_20 = volume.rolling(20).mean().iloc[-1]
            if avg_vol_20 == 0: continue
            rvol = volume.iloc[-1] / avg_vol_20
            
            # 3. Technicals
            adx, atr_pct = calculate_technical_factors(df)
            
            # 4. Liquidity Filter (> 5 Crore Turnover)
            turnover = volume.iloc[-1] * close.iloc[-1]
            if turnover < 50000000: continue

            performance_list.append({
                'Symbol': symbol.replace('.NS', ''),
                '1W_Return': round(one_week_return * 100, 2),
                'RVol': round(rvol, 2),
                'ADX': round(adx, 2),
                'ATR%': round(atr_pct, 2),
                'Price': round(close.iloc[-1], 2)
            })
            
        except Exception as e:
            continue
            
    return pd.DataFrame(performance_list)

def screen_alpha_v3():
    logger.info("Starting Alpha V3 Screener (Recency + Volume + Volatility)...")
    df = get_v3_performance(SYMBOLS)
    
    if df.empty:
        logger.error("No data found.")
        return

    # --- V3 FILTER LOGIC ---
    # 1. Strong Trend: ADX > 25 (Mandatory)
    # 2. Good Volatility: ATR% > 2.0 (Mandatory for profit targets)
    # 3. Volume Support: RVol > 0.8 (Not dead money)
    
    # Split ETFs
    etfs = df[df['Symbol'].str.contains('BEES')]
    stocks = df[~df['Symbol'].str.contains('BEES')]
    
    valid_stocks = stocks[(stocks['ADX'] > 25) & (stocks['ATR%'] > 2.0) & (stocks['RVol'] > 0.8)].copy()
    
    # Ranking:
    # 70% Weight to 1-Week Return (Fresh Momentum)
    # 30% Weight to Relative Volume (Conviction)
    valid_stocks['Score'] = (valid_stocks['1W_Return'] * 0.7) + (valid_stocks['RVol'] * 5) # Scale RVol (~1.0 to ~5.0)
    
    bulls = valid_stocks.sort_values(by='Score', ascending=False).head(5)
    bears = valid_stocks.sort_values(by='Score', ascending=True).head(5)
    
    print("\n" + "="*80)
    print("       ALPHA V3 BULLS (High 1W Momentum + Volume)")
    print("="*80)
    print(bulls[['Symbol', '1W_Return', 'RVol', 'ADX', 'ATR%', 'Price']].to_string(index=False))
    
    print("\n" + "="*80)
    print("       ALPHA V3 BEARS (High 1W Drop + Volume)")
    print("="*80)
    print(bears[['Symbol', '1W_Return', 'RVol', 'ADX', 'ATR%', 'Price']].to_string(index=False))
    
    print("\n" + "="*80)
    print("       ETF WATCHLIST")
    print("="*80)
    print(etfs[['Symbol', '1W_Return', 'RVol', 'ADX', 'ATR%', 'Price']].to_string(index=False))

if __name__ == "__main__":
    screen_alpha_v3()
