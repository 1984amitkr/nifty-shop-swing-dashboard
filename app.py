# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import yfinance as yf
from ta.momentum import RSIIndicator
import warnings
warnings.filterwarnings("ignore")

# ==============================
# DATA FETCH (CACHED)
# ==============================
@st.cache_data(ttl=3600)  # Cache 1 hour
def fetch_data(symbols, start="2015-01-01", end=None):
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")
    data = yf.download(symbols, start=start, end=end, progress=False)
    if data.empty:
        st.error("No data downloaded. Check symbols or date range.")
        return None, None
    close = data['Close'].ffill()
    open_ = data['Open'].ffill()
    return close, open_

# ==============================
# INDICATORS (CACHED)
# ==============================
@st.cache_data(ttl=3600)
def compute_indicators(close):
    sma20 = close.rolling(20).mean()
    rsi = close.apply(lambda col: RSIIndicator(col, window=14).rsi())
    dist = (close - sma20) / sma20
    return sma20, rsi, dist

# ==============================
# BACKTEST (NOT CACHED — vectorbt not pickleable)
# ==============================
def run_backtest_live(close, open_, capital, rsi_threshold, max_positions):
    sma20, rsi, dist = compute_indicators(close)

    entries = pd.DataFrame(False, index=close.index, columns=close.columns, dtype=bool)
    exits = pd.DataFrame(False, index=close.index, columns=close.columns, dtype=bool)

    size_per_trade = capital * 0.20 / max_positions

    try:
        import vectorbt as vbt
    except ImportError:
        st.error("vectorbt not installed. Add to requirements.txt.")
        return None

    # Scan loop
    for i in range(35, len(close)):
        date = close.index[i]
        c = close.iloc[i]
        o = open_.iloc[i]
        s = sma20.iloc[i]
        r = rsi.iloc[i]
        d = dist.iloc[i]

        # ENTRY: Top N farthest below SMA with RSI < threshold
        valid = (r < rsi_threshold) & (d < 0)
        if valid.any():
            candidates = d[valid].nsmallest(max_positions)
            for sym in candidates.index:
                if not entries[sym].iloc[:i].any():  # No open position
                    entries.iloc[i, close.columns.get_loc(sym)] = True

        # EXIT: +8% above entry price (simplified)
        for sym in close.columns:
            pos_entries = entries[sym].iloc[:i+1]
            if pos_entries.any():
                entry_idx = pos_entries[pos_entries].index[-1]
                entry_price = o.loc[entry_idx, sym] if entry_idx in o.index else c[sym]
                if c[sym] >= entry_price * 1.08:
                    exits.iloc[i, close.columns.get_loc(sym)] = True

    # Build portfolio
    pf = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        size=size_per_trade,
        size_type='value',
        init_cash=capital,
        fees=0.001,
        freq='1D'
    )
    return pf, entries

# ==============================
# STREAMLIT UI
# ==============================
st.set_page_config(page_title="Nifty Shop Swing + RSI", layout="wide")
st.title("Nifty Shop Swing Strategy + RSI(14) Filter")
st.markdown("**Top 5 stocks farthest below 20-SMA with RSI(14) < 40 → Buy, exit at +8%, average down on 3% dips**")

# --- Sidebar ---
st.sidebar.header("Backtest Settings")
capital = st.sidebar.number_input("Capital (₹)", 50000, 1000000, 100000, 10000)
rsi_filter = st.sidebar.slider("RSI(14) Threshold", 20, 50, 40)
max_stocks = st.sidebar.number_input("Max Stocks per Day", 1, 10, 5)

symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
           "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS"]

if st.sidebar.button("Run Backtest (2015–Today)"):
    with st.spinner("Downloading data & running backtest..."):
        close, open_ = fetch_data(symbols)
        if close is not None:
            pf, entries = run_backtest_live(close, open_, capital, rsi_filter, max_stocks)
            if pf is not None:
                st.session_state.pf = pf
                st.session_state.entries = entries
                st.session_state.close = close
                st.success("Backtest completed!")
            else:
                st.error("Backtest failed.")
        else:
            st.error("Data fetch failed.")

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Live Scan", "Backtest", "Equity", "Trades"])

# === LIVE SCAN ===
with tab1:
    st.header("Today's Signals")
    if datetime.now().weekday() >= 5:
        st.warning("Market Closed (Weekend)")
    else:
        with st.spinner("Scanning live market..."):
            close_today, _ = fetch_data(symbols, start=(datetime.now() - pd.Timedelta(60, 'd')).strftime("%Y-%m-%d"))
            if close_today is not None:
                sma20, rsi_val, dist = compute_indicators(close_today)
                latest = close_today.iloc[-1]
                sma_latest = sma20.iloc[-1]
                rsi_latest = rsi_val.iloc[-1]
                dist_latest = dist.iloc[-1]

                valid = (rsi_latest < rsi_filter) & (dist_latest < 0)
                candidates = dist_latest[valid].nsmallest(max_stocks)

                if len(candidates) > 0:
                    df = pd.DataFrame({
                        "Stock": candidates.index,
                        "Price": latest[candidates.index].round(2),
                        "SMA20": sma_latest[candidates.index].round(2),
                        "Dist %": (dist_latest[candidates.index] * 100).round(2),
                        "RSI": rsi_latest[candidates.index].round(1)
                    }).sort_values("Dist %")
                    st.success(f"**{len(df)} BUY SIGNAL(S) TODAY**")
                    st.dataframe(df.style.format({"Price": "₹{:.2f}", "SMA20": "₹{:.2f}"}), use_container_width=True)
                else:
                    st.info("No signals today.")
            else:
                st.error("Live data failed.")

# === BACKTEST SUMMARY ===
with tab2:
    st.header("Backtest Results")
    if 'pf' in st.session_state:
        pf = st.session_state.pf
        stats = pf.stats()
        total_ret = pf.total_return()
        years = len(pf.wrapper.index) / 252
        cagr = (1 + total_ret) ** (1/years) - 1 if years > 0 else 0

        col1, col2 = st.columns(2)
        col1.metric("Total Return", f"{total_ret:+.1%}")
        col2.metric("CAGR", f"{cagr:+.1%}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Win Rate", f"{pf.trades.win_rate():.1%}")
        col2.metric("Trades", int(pf.trades.count()))
        col3.metric("Sharpe", f"{stats.get('Sharpe Ratio', 0):.2f}")
    else:
        st.info("Run backtest first.")

# === EQUITY CURVE ===
with tab3:
    st.header("Equity Curve")
    if 'pf' in st.session_state:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=st.session_state.pf.wrapper.index, y=st.session_state.pf.value(), mode='lines'))
        fig.update_layout(title="Portfolio Value Over Time", xaxis_title="Date", yaxis_title="₹ Value")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run backtest first.")

# === TRADES ===
with tab4:
    st.header("Trade Log")
    if 'pf' in st.session_state:
        trades = st.session_state.pf.trades.records_readable
        if not trades.empty:
            trades['Return %'] = (trades['Return'] * 100).round(2)
            st.dataframe(trades[['Symbol', 'Entry Timestamp', 'Exit Timestamp', 'Return %', 'Duration']], use_container_width=True)
        else:
            st.info("No trades.")
    else:
        st.info("Run backtest first.")

# --- Footer ---
st.sidebar.markdown("---")
if st.sidebar.button("Clear Cache & Rerun"):
    st.cache_data.clear()
    st.rerun()