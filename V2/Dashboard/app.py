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
            m1, m2, m3 = st.columns(3)
            
            # Color logic
            z_color = "normal"
            if z_score > 2.0 or z_score < -2.0: z_color = "inverse"
            
            m1.metric("Z-Score", f"{z_score:.2f}", delta_color=z_color)
            m2.metric("Beta", f"{beta:.2f}")
            m3.metric("AI Confidence", f"{ai_conf:.1%}", 
                     delta=f"{ai_conf*100:.0f}%", 
                     delta_color="normal" if ai_conf > 0.6 else "off")
            
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
            
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📝 Recent Trade Signals")
    
    # Trade Log
    conn = get_connection()
    trades_df = pd.read_sql("SELECT * FROM trades ORDER BY id DESC LIMIT 10", conn)
    conn.close()
    
    if not trades_df.empty:
        st.dataframe(trades_df)
    else:
        st.info("No trades executed yet.")
