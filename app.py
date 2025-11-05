# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf
from backtest import run_backtest
import base64

st.set_page_config(page_title="Nifty Shop Swing + RSI", layout="wide")
st.title("🛒 Nifty Shop Swing Strategy + RSI(14) Filter")
st.markdown("**Mean-reversion swing strategy: Top 5 oversold (RSI<40) below 20-SMA → +8% TP, average down on 3% dips**")

# Sidebar
st.sidebar.header("Settings")
capital = st.sidebar.number_input("Starting Capital (₹)", 50000, 500000, 100000, 10000)
rsi_filter = st.sidebar.slider("RSI(14) Threshold", 20, 50, 40)
max_stocks = st.sidebar.number_input("Max Stocks per Day", 1, 10, 5)

if st.sidebar.button("Run Full Backtest"):
    with st.spinner("Running backtest (2015–2025)..."):
        pf, entries, close, sma20, rsi, dist = run_backtest(
            capital=capital, rsi_threshold=rsi_filter, max_positions=max_stocks
        )
        st.session_state.pf = pf
        st.session_state.entries = entries
        st.session_state.close = close
        st.session_state.sma20 = sma20
        st.session_state.rsi = rsi
        st.session_state.dist = dist
    st.success("Backtest complete!")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Live Scan", "Backtest Summary", "Equity Curve", "Trade Log", "Download"])

# === TAB 1: LIVE SCAN ===
with tab1:
    st.header("🔍 Today's Entry Signals")
    today = pd.Timestamp.today().normalize()
    if today.weekday() >= 5:
        st.warning("Market closed (Weekend)")
    else:
        with st.spinner("Scanning market..."):
            data = yf.download("RELIANCE.NS TCS.NS HDFCBANK.NS INFY.NS ICICIBANK.NS SBIN.NS BHARTIARTL.NS ITC.NS HINDUNILVR.NS LT.NS", period="5d")
            close = data['Close'].iloc[-1]
            sma20 = close.rolling(20).mean().iloc[-1]
            rsi_val = close.apply(lambda x: yf.Ticker(x.name).history(period="1mo")['Close'].iloc[-14:].pipe(
                lambda s: (s.pct_change().add(1).cumprod().iloc[-1] - 1) / (s.pct_change().abs().sum()) * 100
            ) if close.name in yf.Ticker(close.name).history(period="1mo").index else np.nan)
            # Simplified RSI approx
            try:
                rsi_val = close.copy()
                for sym in close.index:
                    hist = yf.Ticker(sym).history(period="60d")['Close']
                    rsi_val[sym] = RSIIndicator(hist, 14).rsi().iloc[-1]
            except:
                rsi_val = pd.Series([np.nan]*len(close), index=close.index)

            dist = (close - sma20) / sma20
            valid = (rsi_val < rsi_filter) & (dist < 0)
            candidates = dist[valid].nsmallest(max_stocks)

            if len(candidates) > 0:
                df = pd.DataFrame({
                    "Stock": candidates.index,
                    "Price": close[candidates.index].round(2),
                    "SMA20": sma20[candidates.index].round(2),
                    "Dist %": (dist[candidates.index] * 100).round(2),
                    "RSI(14)": rsi_val[candidates.index].round(1)
                }).sort_values("Dist %")
                st.success(f"**{len(df)} SIGNAL(S) TODAY**")
                st.dataframe(df.style.highlight_min(subset=["Dist %"], color='lightgreen'), use_container_width=True)
            else:
                st.info("No signals today. Waiting for pullback...")

# === TAB 2: BACKTEST SUMMARY ===
with tab2:
    st.header("📊 Backtest Performance")
    if 'pf' in st.session_state:
        pf = st.session_state.pf
        stats = pf.stats()
        total_ret = pf.total_return()
        cagr = (1 + total_ret) ** (252 / len(pf.wrapper.index)) - 1
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Return", f"{total_ret:+.1%}")
        col2.metric("CAGR", f"{cagr:+.1%}")
        col3.metric("Win Rate", f"{pf.trades.win_rate():.1%}")
        col4.metric("Total Trades", int(pf.trades.count()))
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Trade", f"{pf.trades.returns.mean():+.1%}")
        col2.metric("Max DD", f"{stats['Max Drawdown [%]']:.1f}%")
        col3.metric("Sharpe", f"{stats['Sharpe Ratio']:.2f}")
    else:
        st.info("Click 'Run Full Backtest' in sidebar")

# === TAB 3: EQUITY CURVE ===
with tab3:
    st.header("📈 Equity Curve")
    if 'pf' in st.session_state:
        fig = pf.value().vbt.plot(trace_kwargs=dict(name="Portfolio Value"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run backtest first")

# === TAB 4: TRADE LOG ===
with tab4:
    st.header("📋 Trade History")
    if 'pf' in st.session_state:
        trades = st.session_state.pf.trades.records_readable
        trades['Return %'] = trades['Return'] * 100
        st.dataframe(trades[['Symbol', 'Entry Timestamp', 'Exit Timestamp', 'Return %', 'Duration']].round(2), use_container_width=True)
    else:
        st.info("Run backtest first")

# === TAB 5: DOWNLOAD ===
with tab5:
    st.header("💾 Export Data")
    if 'pf' in st.session_state and 'entries' in st.session_state:
        # Signals CSV
        signals = st.session_state.entries.copy()
        signals = signals[signals.any(axis=1)]
        csv_signals = signals.to_csv().encode()
        b64_signals = base64.b64encode(csv_signals).decode()
        href_signals = f'<a href="data:file/csv;base64,{b64_signals}" download="nifty_shop_signals.csv">Download Entry Signals (CSV)</a>'
        st.markdown(href_signals, unsafe_allow_html=True)

        # Backtest report
        report = f"""
Nifty Shop Swing + RSI(14) Backtest Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Capital: ₹{capital:,}
RSI Filter: < {rsi_filter}
Max Stocks: {max_stocks}

Total Return: {st.session_state.pf.total_return():+.1%}
CAGR: {(1 + st.session_state.pf.total_return()) ** (252 / len(st.session_state.pf.wrapper.index)) - 1:+.1%}
Win Rate: {st.session_state.pf.trades.win_rate():.1%}
Trades: {int(st.session_state.pf.trades.count())}
        """
        b64_report = base64.b64encode(report.encode()).decode()
        href_report = f'<a href="data:file/txt;base64,{b64_report}" download="backtest_report.txt">Download Report (TXT)</a>'
        st.markdown(href_report, unsafe_allow_html=True)
    else:
        st.info("Run backtest to download")

# Auto-refresh
st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
if st.sidebar.button("Refresh Data"):
    st.experimental_rerun()