# app.py - NIFTY 200 SWEET ZONE SCANNER + SELECT ANY STOCK FOR CHART
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf
from ta.momentum import RSIIndicator
import time
import requests

# PAGE CONFIG
st.set_page_config(page_title="Nifty 200 Sweet Zone + Chart Selector", layout="wide")
st.title("NIFTY 200 SWEET ZONE SCANNER + ANY STOCK CHART")
st.markdown("**Real-time • 200 stocks • Sweet Zone + RSI<40 • Select ANY stock for live chart**")

# SOUND ALERT
def play_alert():
    st.markdown("""
    <audio autoplay>
      <source src="https://assets.mixkit.co/sfx/preview/mixkit-alarm-tone-1065.mp3" type="audio/mp3">
    </audio>
    """, unsafe_allow_html=True)

# FETCH NIFTY 200 SYMBOLS
@st.cache_data(ttl=86400)
def get_nifty200_symbols():
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
        df = pd.read_csv(url)
        symbols = [s + ".NS" for s in df['Symbol'].tolist()]
        return sorted(symbols)
    except:
        st.warning("Using fallback Nifty 200 list")
        return sorted([
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS",
            "ITC.NS","HINDUNILVR.NS","LT.NS","AXISBANK.NS","KOTAKBANK.NS","ASIANPAINT.NS","MARUTI.NS",
            "SUNPHARMA.NS","BAJFINANCE.NS","HCLTECH.NS","TITAN.NS","WIPRO.NS","ULTRACEMCO.NS"
            # ... (full list truncated for brevity - include all 200 from previous code)
        ])

symbols = get_nifty200_symbols()

# FETCH LIVE DATA
def fetch_live_data():
    with st.spinner(f"Loading {len(symbols)} stocks..."):
        try:
            data = yf.download(symbols, period="3mo", progress=False, auto_adjust=True, threads=True)
            return data['Close'].ffill()
        except Exception as e:
            st.error(f"Error: {e}")
            return None

df = fetch_live_data()

# SCANNER
def run_sweet_zone_scan():
    if df is None or len(df) < 30:
        return pd.DataFrame(), None
    
    latest = df.iloc[-1]
    sma20 = df.rolling(20).mean().iloc[-1]
    rsi_val = pd.Series({col: RSIIndicator(df[col].dropna(), 14).rsi().iloc[-1] if len(df[col].dropna()) >= 14 else np.nan for col in df.columns})
    dist_pct = ((latest - sma20) / sma20) * 100
    
    sweet_zone = (dist_pct <= -5.3) & (dist_pct >= -6.5)
    oversold = rsi_val < 40
    mask = sweet_zone & oversold & rsi_val.notna()
    
    candidates = dist_pct[mask].nsmallest(10)
    
    if candidates.empty:
        return pd.DataFrame(), None
    
    result = pd.DataFrame({
        'Stock': candidates.index.str.replace('.NS', ''),
        'Price ₹': latest[candidates.index].round(0),
        '20-SMA ₹': sma20[candidates.index].round(0),
        'Dist%': dist_pct[candidates.index].round(2),
        'RSI': rsi_val[candidates.index].round(1),
        'Verdict': 'BUY NOW!'
    }).sort_values('Dist%')
    
    return result, candidates.index[0]

signals, best_stock = run_sweet_zone_scan()

# SIDEBAR
st.sidebar.header("Controls")
rsi_thr = st.sidebar.slider("Max RSI", 30, 50, 40)
min_d = st.sidebar.number_input("Min Dist%", -15.0, -3.0, -6.5)
max_d = st.sidebar.number_input("Max Dist%", -15.0, -3.0, -5.3)

# NEW: STOCK SELECTOR FOR CHART
st.sidebar.markdown("### 📊 Chart Any Stock")
selected_symbol = st.sidebar.selectbox(
    "Choose stock for live chart",
    options=symbols,
    format_func=lambda x: x.replace('.NS', ''),
    index=symbols.index(best_stock) if best_stock and best_stock in symbols else 0
)

st.sidebar.info(f"Time: {datetime.now().strftime('%I:%M %p')} IST")
if st.sidebar.button("Refresh All"):
    st.cache_data.clear()
    st.rerun()

# CHART FUNCTION
def plot_selected_stock(sym):
    if df is None or sym not in df.columns:
        return None
    data = df[sym].tail(60)
    sma = data.rolling(20).mean()
    rsi = RSIIndicator(data, 14).rsi()
    
    fig = make_subplots(rows=2, cols=1, subplot_titles=(f"{sym.replace('.NS','')} - Live Price vs 20-SMA", "RSI(14)"),
                        row_heights=[0.7, 0.3], shared_xaxes=True, vertical_spacing=0.08)
    
    fig.add_trace(go.Scatter(x=data.index, y=data, name="Price", line=dict(width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sma.index, y=sma, name="20-SMA", line=dict(color="orange", dash="dash")), row=1, col=1)
    
    # Highlight sweet zone
    latest_dist = ((data.iloc[-1] - sma.iloc[-1]) / sma.iloc[-1]) * 100
    if -6.5 <= latest_dist <= -5.3:
        fig.add_vrect(x0=data.index[-1], x1=data.index[-1], fillcolor="green", opacity=0.3, line_width=0)
    
    fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI", line=dict(color="#00ff00")), row=2, col=1)
    fig.add_hline(y=40, line_dash="dot", line_color="orange", row=2, col=1)
    fig.add_hrect(y0=0, y1=40, fillcolor="red", opacity=0.15, row=2, col=1)
    
    fig.update_layout(height=620, template="plotly_dark", showlegend=False)
    return fig

# MAIN LAYOUT
col1, col2 = st.columns([1.1, 1.9])

with col1:
    st.markdown("### 🚀 Sweet Zone Signals")
    if signals.empty:
        st.success("**NO SIGNALS RIGHT NOW**")
        st.info("Market is strong - waiting for -5.3% to -6.5% pullback + RSI<40")
    else:
        play_alert()
        st.error(f"**{len(signals)} SWEET ZONE BUY(S)!**")
        styled = signals.style\
            .applymap(lambda x: 'background-color: #ffcccc; font-weight: bold', subset=['Verdict'])\
            .format({'Price ₹': '₹{:.0f}', '20-SMA ₹': '₹{:.0f}'})
        st.dataframe(styled, use_container_width=True)

with col2:
    st.markdown("### 📈 Live Chart")
    fig = plot_selected_stock(selected_symbol)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        # Show current stats
        if selected_symbol in df.columns:
            price = df[selected_symbol].iloc[-1]
            sma = df[selected_symbol].rolling(20).mean().iloc[-1]
            dist = ((price - sma) / sma) * 100
            rsi_val = RSIIndicator(df[selected_symbol], 14).rsi().iloc[-1]
            st.metric(f"{selected_symbol.replace('.NS','')}", f"₹{price:.0f}", f"{dist:+.2f}% vs 20-SMA | RSI {rsi_val:.1f}")
    else:
        st.info("Chart loading...")

# FOOTER
st.markdown("---")
st.caption("Nifty 200 Sweet Zone + Any Stock Chart • Real-time • @cool_amitkr • Nov 07, 2025")