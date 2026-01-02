
import streamlit as st
import sqlite3
import pandas as pd
import time
import os
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page Config
st.set_page_config(
    page_title="PaiseTrade AI Dashboard",
    page_icon="📈",
    layout="wide",
)

# Database Connection
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'trading_data_v2.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_logs(pair, limit=100):
    conn = get_connection()
    query = f"""
        SELECT timestamp, z_score, beta, ai_confidence 
        FROM strategy_logs 
        WHERE pair = ? 
        ORDER BY id DESC LIMIT ?
    """
    df = pd.read_sql(query, conn, params=(pair, limit))
    conn.close()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    return df

def load_active_pairs():
    conn = get_connection()
    try:
        query = "SELECT DISTINCT pair FROM strategy_logs"
        df = pd.read_sql(query, conn)
        return df['pair'].tolist()
    except:
        return []
    finally:
        conn.close()

# HEADER
st.title("🤖 PaiseTrade: AI-Quant Monitor")
st.markdown("---")

# AUTO REFRESH
if st.checkbox('Auto Refresh (5s)', value=True):
    time.sleep(5)
    st.rerun()

# MAIN CONTENT
pairs = load_active_pairs()
if not pairs:
    st.warning("No strategy logs found. Is the Runner active?")
else:
    # Monitor Grid
    cols = st.columns(len(pairs))
    
    for i, pair in enumerate(pairs):
        df = load_logs(pair, limit=200)
        
        if df.empty:
            continue
            
        latest = df.iloc[-1]
        z_score = latest['z_score']
        ai_conf = latest['ai_confidence']
        beta = latest['beta']
        ts = latest['timestamp']
        
        with st.container():
            st.subheader(f"👥 {pair}")
            st.caption(f"Last Update: {ts.strftime('%H:%M:%S')}")
            
            # Key Metrics
            m1, m2 = st.columns(2)
            
            # Color logic
            z_color = "normal"
            if z_score > 2.0 or z_score < -2.0: z_color = "inverse"
            
            m1.metric("Z-Score", f"{z_score:.2f}", delta_color=z_color)
            m2.metric("Beta", f"{beta:.2f}")
            
            # Chart
            fig = go.Figure()
            
            # Z-Score Line
            fig.add_trace(go.Scatter(
                x=df['timestamp'], y=df['z_score'],
                mode='lines', name='Z-Score',
                line=dict(color='#00CC96', width=2)
            ))
            
            # Thresholds
            fig.add_hline(y=2.0, line_dash="dash", line_color="red")
            fig.add_hline(y=-2.0, line_dash="dash", line_color="green")
            fig.add_hline(y=0.0, line_color="gray", opacity=0.5)
            
            fig.update_layout(
                height=300, 
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.subheader("📝 Recent Trade Signals")
    
    # Trade Log
    conn = get_connection()
    try:
        trades_df = pd.read_sql("SELECT * FROM trades ORDER BY id DESC LIMIT 10", conn)
        if not trades_df.empty:
            st.dataframe(trades_df)
        else:
            st.info("No trades executed yet.")
    except Exception as e:
        st.error(f"Error loading trades: {e}")
    finally:
        conn.close()

    st.markdown("---")
    st.subheader("🧠 Portfolio Optimizer (Markowitz)")
    
    with st.expander("Run Portfolio Optimization", expanded=False):
        st.markdown("""
        **Modern Portfolio Theory (MPT):**
        Finds the optimal allocation of capital between your tracked assets to **Maximize Sharpe Ratio**.
        """)
        
        if st.button("Optimize Allocation"):
            try:
                # Lazy Import to avoid issues if Common not in path
                import sys
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                from Common.portfolio_optimizer import PortfolioOptimizer
                from Backtesting.config import PortfolioConfig
                
                with st.spinner("Fetching data and optimizing..."):
                    # 1. Fetch Price History from Candles Table
                    conn = get_connection()
                    # Get symbols first
                    syms = pd.read_sql("SELECT DISTINCT symbol FROM historical_candles", conn)['symbol'].tolist()
                    
                    if not syms:
                        st.error("No price data found in 'historical_candles' table. Run Backtest/PaperTrader first.")
                    else:
                        # Fetch all candles (Limit to last 90 days for relevance)
                        query_candles = """
                            SELECT symbol, timestamp, close 
                            FROM historical_candles 
                            WHERE timestamp >= date('now', '-90 days')
                        """
                        price_df_raw = pd.read_sql(query_candles, conn)
                        conn.close()
                        
                        if price_df_raw.empty:
                            st.error("Not enough history for optimization.")
                        else:
                            # Pivot: Index=Date, Cols=Symbol
                            price_df_raw['timestamp'] = pd.to_datetime(price_df_raw['timestamp'])
                            price_matrix = price_df_raw.pivot_table(index='timestamp', columns='symbol', values='close')
                            price_matrix = price_matrix.dropna()
                            
                            if price_matrix.shape[0] < 30:
                                st.warning(f"Warning: Only {price_matrix.shape[0]} data points available. Optimization may be unstable.")
                            
                            # 2. Run Optimizer
                            optimizer = PortfolioOptimizer(risk_free_rate=PortfolioConfig.RISK_FREE_RATE)
                            result = optimizer.optimize(
                                price_matrix, 
                                min_weight=PortfolioConfig.MIN_ASSET_WEIGHT,
                                max_weight=PortfolioConfig.MAX_ASSET_WEIGHT
                            )
                            
                            if result:
                                weights = result['weights']
                                metrics = result['metrics']
                                
                                # 3. Display Results
                                c1, c2 = st.columns([1, 1])
                                
                                with c1:
                                    st.success(f"**Optimal Sharpe Ratio: {metrics['sharpe_ratio']:.2f}**")
                                    st.write(f"Expected Annual Return: {metrics['expected_return']:.1%}")
                                    st.write(f"Annual Volatility: {metrics['volatility']:.1%}")
                                
                                with c2:
                                    # Pie Chart
                                    labels = list(weights.keys())
                                    values = list(weights.values())
                                    
                                    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
                                    fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
                                    st.plotly_chart(fig_pie, width="stretch")
                                    
                                st.caption("Note: This optimizes the underlying assets, not the pairs directly.")
                                
                            else:
                                st.error("Optimization failed.")
                                
            except Exception as e:
                st.error(f"Error during optimization: {e}")
