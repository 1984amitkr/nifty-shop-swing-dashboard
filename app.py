# app.py - NIFTY SHOP SWING PRO + CHARTS + NO MATPLOTLIB
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf
from ta.momentum import RSIIndicator
import time

# CONFIG
st.set_page_config(page_title="Nifty Shop Swing PRO", layout="wide")
st.title("Nifty Shop Swing + RSI(14) < 40")
st.markdown("**Real-time • Top 5 Oversold • Charts • Sound Alert • No Errors**")

# SOUND ALERT
def alert():
    st.markdown(
        """
        <audio autoplay>
          <source src="https://assets.mixkit.co/sfx/preview/mixkit-alarm-tone-1065.mp3" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True
    )

# LIVE DATA
@st.cache_data(ttl=300)
def get_data():
    symbols = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
               "SBIN.NS","BHARTIARTL.NS","ITC.NS","HINDUNILVR.NS","LT.NS",
               "AXISBANK.NS","KOTAKBANK.NS","ASIANPAINT.NS","MARUTI.NS","SUNPHARMA.NS"]
    end = datetime.now()
    start = end - timedelta(days=120)
    data = yf.download(symbols, start=start, end=end, progress=False, auto_adjust=True)
    return data['Close'].ffill() if 'Close' in data else None

# SCANNER
def scan_signals(df, rsi_thr=40, top_n=5):
    if df is None or len(df) < 30:
        return pd.DataFrame()
    
    latest = df.iloc[-1]
    sma20 = df.rolling(20).mean().iloc[-1]
    
    rsi_val = pd.Series(index=df.columns, dtype=float)
    for col in df.columns:
        rsi_val[col] = RSIIndicator(df[col], 14).rsi().iloc[-1]
    
    dist = (latest - sma20) / sma20 * 100
    
    mask = (dist < 0) & (rsi_val < rsi_thr)
    candidates = dist[mask].nsmallest(top_n)
    
    if candidates.empty:
        return pd.DataFrame()
    
    result = pd.DataFrame({
        'Symbol': candidates.index.str.replace('.NS',''),
        'Price': latest[candidates.index].round(0),
        'SMA20': sma20[candidates.index].round(0),
        'Dist%': dist[candidates.index].round(2),
        'RSI': rsi_val[candidates.index].round(1)
    }).sort_values('Dist%')
    
    return result

# CHART
def plot_stock(symbol_ns, df):
    symbol = symbol_ns.replace('.NS', '')
    data = df[symbol_ns].tail(60)
    sma20 = data.rolling(20).mean()
    rsi = RSIIndicator(data, 14).rsi()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f"{symbol} - Price vs 20-SMA", "RSI(14)"),
        row_heights=[0.7, 0.3],
        shared_xaxes=True,
        vertical_spacing=0.08
    )
    
    # Price
    fig.add_trace(go.Scatter(x=data.index, y=data, name="Price", line=dict(width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sma20.index, y=sma20, name="20-SMA", line=dict(color="orange", dash="dash")), row=1, col=1)
    
    # Highlight pullback
    if data.iloc[-1] < sma20.iloc[-1]:
        fig.add_vrect(x0=data.index[-30], x1=data.index[-1], fillcolor="red", opacity=0.2, line_width=0, row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI", line=dict(color="#00CC96")), row=2, col=1)
    fig.add_hline(y=40, line_dash="dot", line_color="orange", annotation_text="RSI 40", row=2, col=1)
    fig.add_hrect(y0=0, y1=40, fillcolor="red", opacity=0.1, row=2, col=1)
    
    fig.update_layout(height=600, showlegend=False, template="plotly_dark")
    fig.update_xaxes(rangeslider_visible=False)
    return fig

# MAIN
df = get_data()

# Sidebar
st.sidebar.header("Scanner Settings")
rsi_max = st.sidebar.slider("Max RSI", 30, 50, 40)
top_n = st.sidebar.slider("Max Signals", 1, 10, 5)
st.sidebar.info(f"Updated: {datetime.now().strftime('%H:%M:%S')} IST")

if st.sidebar.button("Refresh Now"):
    st.cache_data.clear()
    time.sleep(1)
    st.rerun()

# SCAN
signals = scan_signals(df, rsi_max, top_n)

# DISPLAY
col1, col2 = st.columns([1.1, 1.9])

with col1:
    st.markdown("### Live Signals")
    if signals.empty:
        st.success("No signals right now")
        st.info("Market is strong. Waiting for pullback...")
    else:
        alert()
        st.error(f"**{len(signals)} BUY SIGNAL(S) DETECTED!**")
        
        # CSS Styling without matplotlib
        def color_dist(val):
            color = 'red' if val < -5 else 'orange' if val < -3 else 'lightgray'
            return f'background-color: {color}; color: white; font-weight: bold'
        
        styled = signals.style\
            .applymap(color_dist, subset=['Dist%'])\
            .format({'Price': '₹{:.0f}', 'SMA20': '₹{:.0f}', 'Dist%': '{:.2f}%'})
        
        st.dataframe(styled, use_container_width=True)

with col2:
    if not signals.empty:
        selected = st.selectbox("Chart", signals['Symbol'])
        symbol_ns = selected + ".NS"
        fig = plot_stock(symbol_ns, df)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("<h4 style='text-align: center; color: #666;'>Charts appear when signals arrive</h4>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Nifty Shop Swing Strategy • Real-time NSE Data • @cool_amitkr • Nov 07, 2025")