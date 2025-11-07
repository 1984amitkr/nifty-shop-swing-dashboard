# app.py - NIFTY SHOP SWING + CHARTS + SOUND
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf
from ta.momentum import RSIIndicator
import time

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="Nifty Shop Swing PRO", layout="wide")
st.title("Nifty Shop Swing + RSI(14) < 40")
st.markdown("**Real-time scanner • Top 5 oversold • Price + RSI Charts • Sound Alert**")

# Sound alert
def play_sound():
    st.audio("https://assets.mixkit.co/sfx/preview/mixkit-alarm-tone-1065.mp3", format="audio/mp3", autoplay=True)

# ==============================
# LIVE DATA
# ==============================
@st.cache_data(ttl=300)
def get_data():
    symbols = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
               "SBIN.NS","BHARTIARTL.NS","ITC.NS","HINDUNILVR.NS","LT.NS",
               "AXISBANK.NS","KOTAKBANK.NS","ASIANPAINT.NS","MARUTI.NS","SUNPHARMA.NS"]
    
    end = datetime.now()
    start = end - timedelta(days=120)
    data = yf.download(symbols, start=start, end=end, progress=False)
    return data['Close'].ffill() if not data.empty else None

# ==============================
# SCANNER
# ==============================
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
        'Price': latest[candidates.index].round(2),
        'SMA20': sma20[candidates.index].round(2),
        'Dist%': dist[candidates.index].round(2),
        'RSI': rsi_val[candidates.index].round(1)
    }).sort_values('Dist%')
    
    return result

# ==============================
# CHART FUNCTION
# ==============================
def plot_stock(symbol_ns, df):
    symbol = symbol_ns.replace('.NS', '')
    data = df[symbol_ns].tail(60)
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f"{symbol} - Price vs 20-SMA", "RSI(14)"),
        row_heights=[0.7, 0.3],
        shared_xaxes=True,
        vertical_spacing=0.05
    )
    
    # Price + SMA
    fig.add_trace(go.Scatter(x=data.index, y=data, name="Price", line=dict(color="#636EFA")), row=1, col=1)
    sma20 = data.rolling(20).mean()
    fig.add_trace(go.Scatter(x=sma20.index, y=sma20, name="20-SMA", line=dict(color="#EF553B", dash="dash")), row=1, col=1)
    
    # Fill oversold
    latest_price = data.iloc[-1]
    latest_sma = sma20.iloc[-1]
    if latest_price < latest_sma:
        fig.add_vrect(x0=data.index[-20], x1=data.index[-1], fillcolor="red", opacity=0.15, row=1, col=1)
    
    # RSI
    rsi = RSIIndicator(data, 14).rsi()
    fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI", line=dict(color="#00CC96")), row=2, col=1)
    fig.add_hline(y=40, line_dash="dot", line_color="orange", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hrect(y0=0, y1=40, fillcolor="red", opacity=0.1, row=2, col=1)
    
    fig.update_layout(height=600, title_text=f"Live Chart - {symbol}", showlegend=False)
    fig.update_xaxes(rangeslider_visible=False)
    return fig

# ==============================
# MAIN
# ==============================
df = get_data()

# Sidebar
st.sidebar.header("Scanner Settings")
rsi_max = st.sidebar.slider("Max RSI", 30, 50, 40)
top_n = st.sidebar.slider("Max Signals", 1, 10, 5)
st.sidebar.info(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

if st.sidebar.button("Refresh Now"):
    st.cache_data.clear()
    time.sleep(1)
    st.rerun()

# Run scan
signals = scan_signals(df, rsi_max, top_n)

# ==============================
# DISPLAY
# ==============================
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### Live Signals")
    if signals.empty:
        st.success("No signals right now")
        st.info("Waiting for market pullback...")
    else:
        st.error(f"**{len(signals)} BUY SIGNAL(S)!**")
        play_sound()
        st.dataframe(
            signals.style
            .background_gradient(subset=['Dist%'], cmap='Reds')
            .format({'Price': '₹{:.0f}', 'SMA20': '₹{:.0f}'})
        )

with col2:
    if not signals.empty:
        selected = st.selectbox("View Chart", signals['Symbol'])
        symbol_ns = selected + ".NS"
        fig = plot_stock(symbol_ns, df)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("<h3 style='text-align: center; color: gray;'>Charts appear when signals arrive</h3>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Data: Yahoo Finance • Strategy: Mean Reversion • Made with ❤️ by @cool_amitkr")