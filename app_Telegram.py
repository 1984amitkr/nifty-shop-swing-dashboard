# app.py - NIFTY 200 SWEET ZONE + FULL 1-YEAR HISTORICAL ALERTS BY DATE
# Pick ANY date in last 365 days → See all stocks that triggered Sweet Zone
# + Live alerts + Telegram + Chart + No matplotlib crash

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from ta.momentum import RSIIndicator
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import requests

st.set_page_config(page_title="Nifty 200 Sweet Zone + 1-Year History", layout="wide")
st.title("NIFTY 200 SWEET ZONE + FULL 1-YEAR BACKTEST BY DATE")
st.markdown("**Pick any date in last 1 year → See exactly which stocks hit -5.3% to -6.5% + RSI<40**")

# TELEGRAM
TELEGRAM_BOT_TOKEN = "8597010386:AAHuw6ArQq2ECJRjVqSDKQae4gkifCXdT7Q"
TELEGRAM_CHAT_ID = "@Cool_amitkr"

def send_telegram(msg):
    if "YOUR_BOT" in TELEGRAM_BOT_TOKEN:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except:
        pass

# === FULL NIFTY 200 SYMBOLS ===
@st.cache_data(ttl=86400)
def get_symbols():
    try:
        df = pd.read_csv("https://archives.nseindia.com/content/indices/ind_nifty200list.csv")
        return [s + ".NS" for s in df['Symbol']]
    except:
        return [f"{s}.NS" for s in [
            "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","SBIN","BHARTIARTL","ITC","HINDUNILVR","LT",
            "AXISBANK","KOTAKBANK","ASIANPAINT","MARUTI","SUNPHARMA","BAJFINANCE","HCLTECH","TITAN","WIPRO","ULTRACEMCO"
            # +180 more — full list auto-loaded above
        ]]

symbols = get_symbols()

# === FETCH 1 YEAR DATA ===
@st.cache_data(ttl=3600)
def get_1year_data():
    with st.spinner("Downloading 1 year data for 200 stocks..."):
        data = yf.download(symbols, period="1y", progress=False, auto_adjust=True, threads=True)
        return data['Close'].ffill()

df_full = get_1year_data()

# === SCANNER FUNCTION (FOR ANY DATE) ===
def scan_date(selected_date):
    if selected_date not in df_full.index:
        return pd.DataFrame()
    
    latest = df_full.loc[selected_date]
    sma20 = df_full.rolling(20).mean().loc[selected_date]
    rsi_val = pd.Series({
        col: RSIIndicator(df_full[col].loc[:selected_date].dropna(), 14).rsi().iloc[-1]
        if len(df_full[col].loc[:selected_date].dropna()) >= 14 else np.nan
        for col in df_full.columns
    })
    dist_pct = ((latest - sma20) / sma20) * 100
    
    mask = (dist_pct <= -5.3) & (dist_pct >= -6.5) & (rsi_val < 40) & rsi_val.notna()
    candidates = dist_pct[mask]
    
    if candidates.empty:
        return pd.DataFrame()
    
    result = pd.DataFrame({
        'Stock': candidates.index.str.replace('.NS', ''),
        'Price': latest[candidates.index].round(0),
        '20-SMA': sma20[candidates.index].round(0),
        'Dist%': dist_pct[candidates.index].round(2),
        'RSI': rsi_val[candidates.index].round(1),
    }).sort_values('Dist%')
    return result

# === LIVE SCAN (TODAY) ===
today_signals = scan_date(df_full.index[-1])

# === TABS ===
tab1, tab2, tab3 = st.tabs(["Live Today", "Historical Alerts (Pick Date)", "Chart"])

with tab1:
    st.markdown("### Today's Sweet Zone Alerts")
    if today_signals.empty:
        st.success("No signals today")
    else:
        st.error(f"{len(today_signals)} HIT(S) TODAY!")
        def color_dist(val):
            color = '#8B0000' if val <= -6 else '#FF4500' if val <= -5.5 else '#FFA500'
            return f'background-color: {color}; color: white; font-weight: bold'
        styled = today_signals.style.applymap(color_dist, subset=['Dist%']).format({'Price': '₹{:.0f}'})
        st.dataframe(styled, use_container_width=True)

with tab2:
    st.markdown("### Pick Any Date in Last 1 Year")
    min_date = df_full.index[-252]  # ~1 year trading days
    max_date = df_full.index[-1]
    
    selected_date = st.date_input(
        "Choose Date",
        value=max_date.date(),
        min_value=min_date.date(),
        max_value=max_date.date()
    )
    
    selected_dt = pd.to_datetime(selected_date)
    historical = scan_date(selected_dt)
    
    st.markdown(f"### Sweet Zone Hits on **{selected_date.strftime('%b %d, %Y')}**")
    if historical.empty:
        st.info("No Sweet Zone signals on this date")
    else:
        st.success(f"{len(historical)} STOCK(S) TRIGGERED!")
        styled = historical.style.applymap(
            lambda x: 'background-color: #8B0000; color: white' if x <= -6 else 
                     'background-color: #FF4500; color: white' if x <= -5.5 else '', 
            subset=['Dist%']
        ).format({'Price': '₹{:.0f}'})
        st.dataframe(styled, use_container_width=True)
        
        csv = historical.to_csv(index=False)
        st.download_button("Download CSV", csv, f"sweet_zone_{selected_date}.csv", "text/csv")

with tab3:
    stock = st.selectbox("Chart", [s.replace('.NS','') for s in symbols])
    data = df_full[stock + ".NS"].tail(120)
    sma = data.rolling(20).mean()
    rsi = RSIIndicator(data, 14).rsi()
    
    fig = make_subplots(rows=2, cols=1, subplot_titles=(stock, "RSI(14)"), row_heights=[0.7, 0.3])
    fig.add_trace(go.Scatter(x=data.index, y=data, name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sma.index, y=sma, name="20-SMA", line=dict(dash="dash", color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI"), row=2, col=1)
    fig.add_hline(y=40, line_dash="dot", line_color="red", row=2, col=1)
    fig.update_layout(height=600, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

st.success("FULL 1-YEAR BACKTEST • PICK ANY DATE • @cool_amitkr • Nov 10, 2025")