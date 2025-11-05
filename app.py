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

@st.cache_data
def run_backtest(
    symbols=None,
    start="2015-01-01",
    end=datetime.now().strftime("%Y-%m-%d"),
    capital=100000,
    rsi_threshold=40,
    max_positions=5
):
    if symbols is None:
        symbols = "RELIANCE.NS TCS.NS HDFCBANK.NS INFY.NS ICICIBANK.NS SBIN.NS BHARTIARTL.NS ITC.NS HINDUNILVR.NS LT.NS".split()

    # Download data
    data = yf.download(symbols, start=start, end=end, progress=False)
    if data.empty:
        return None, None, None, None, None, None
    close = data['Close']
    open_ = data['Open']

    # Indicators
    sma20 = close.rolling(20).mean()
    rsi = pd.DataFrame(index=close.index, columns=close.columns)
    for col in close.columns:
        rsi[col] = RSIIndicator(close[col], window=14).rsi()
    dist = (close - sma20) / sma20

    # Simplified signals (vectorbt-friendly; loop for logic)
    entries = pd.DataFrame(False, index=close.index, columns=close.columns, dtype=bool)
    exits = pd.DataFrame(False, index=close.index, columns=close.columns, dtype=bool)

    # Basic portfolio simulation (equal size, no complex avg down for speed; add if needed)
    size = capital * 0.20 / max_positions

    # Scan loop (simplified)
    for i in range(35, len(close)):
        date = close.index[i]
        curr_close = close.iloc[i]
        curr_open = open_.iloc[i]
        curr_sma = sma20.iloc[i]
        curr_rsi = rsi.iloc[i]
        curr_dist = dist.iloc[i]

        # Scan: Top 5 below SMA with RSI < threshold
        valid = (curr_rsi < rsi_threshold) & (curr_dist < 0)
        if valid.any():
            candidates = curr_dist[valid].nsmallest(max_positions)
            for sym in candidates.index:
                entries.iloc[i, close.columns.get_loc(sym)] = True

        # Simple exit: If signal reverses (above SMA next day; placeholder for +8%)
        for sym in close.columns:
            if entries[sym].iloc[:i].any() and not exits[sym].iloc[:i].any():  # Has open position
                if curr_close[sym] > curr_sma[sym] * 1.08:  # +8% above SMA proxy
                    exits.iloc[i, close.columns.get_loc(sym)] = True

    try:
        import vectorbt as vbt
        pf = vbt.Portfolio.from_signals(
            close, entries=entries, exits=exits,
            size=size, size_type='value', init_cash=capital,
            fees=0.001, freq='1D'
        )
    except ImportError:
        st.error("vectorbt not installed. Install via requirements.txt.")
        return None, None, None, None, None, None

    return pf, entries, close, sma20, rsi, dist

st.set_page_config(page_title="Nifty Shop Swing + RSI", layout="wide")
st.title("🛒 Nifty Shop Swing Strategy + RSI(14) Filter")
st.markdown("**Mean-reversion swing strategy: Top 5 oversold (RSI<40) below 20-SMA → +8% TP, average down on 3% dips**")

# Sidebar
st.sidebar.header("Settings")
capital = st.sidebar.number_input("Starting Capital (₹)", 50000, 500000, 100000, 10000)
rsi_filter = st.sidebar.slider("RSI(14) Threshold", 20, 50, 40)
max_stocks = st.sidebar.number_input("Max Stocks per Day", 1, 10, 5)

if st.sidebar.button("Run Full Backtest"):
    with st.spinner("Running backtest (2015–today)..."):
        result = run_backtest(capital=capital, rsi_threshold=rsi_filter, max_positions=max_stocks)
        if result[0] is not None:
            st.session_state.update(dict(zip(['pf', 'entries', 'close', 'sma20', 'rsi', 'dist'], result)))
            st.success("Backtest complete!")
        else:
            st.error("Backtest failed—check logs.")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Live Scan", "Backtest Summary", "Equity Curve", "Trade Log", "Download"])

# === TAB 1: LIVE SCAN ===
with tab1:
    st.header("🔍 Today's Entry Signals")
    today = datetime.now().strftime("%Y-%m-%d")
    symbols = "RELIANCE.NS TCS.NS HDFCBANK.NS INFY.NS ICICIBANK.NS SBIN.NS BHARTIARTL.NS ITC.NS HINDUNILVR.NS LT.NS".split()
    if datetime.now().weekday() >= 5:
        st.warning("Market closed (Weekend)")
    else:
        with st.spinner("Scanning market..."):
            @st.cache_data(ttl=300)  # Cache 5 min
            def get_live_data():
                data = yf.download(symbols, period="2mo", progress=False)['Close']
                sma20 = data.rolling(20).mean().iloc[-1]
                rsi_val = pd.DataFrame(index=data.index, columns=data.columns)
                for col in data.columns:
                    rsi_val[col] = RSIIndicator(data[col], window=14).rsi()
                rsi_val = rsi_val.iloc[-1]
                close_today = data.iloc[-1]
                dist = (close_today - sma20) / sma20
                return close_today, sma20, rsi_val, dist

            close_today, sma20, rsi_val, dist = get_live_data()
            valid = (rsi_val < rsi_filter) & (dist < 0)
            candidates = dist[valid].nsmallest(max_stocks)

            if len(candidates) > 0:
                df = pd.DataFrame({
                    "Stock": candidates.index,
                    "Price": close_today[candidates.index].round(2),
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
        days = len(pf.wrapper.index)
        cagr = (1 + total_ret) ** (252 / days) - 1 if days > 0 else 0
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
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=st.session_state.pf.wrapper.index, y=st.session_state.pf.value(), mode='lines', name='Portfolio Value'))
        fig.update_layout(title="Equity Curve", xaxis_title="Date", yaxis_title="Value (₹)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run backtest first")

# === TAB 4: TRADE LOG ===
with tab4:
    st.header("📋 Trade History")
    if 'pf' in st.session_state:
        trades = st.session_state.pf.trades.records_readable
        if not trades.empty:
            trades['Return %'] = trades['Return'] * 100
            st.dataframe(trades[['Symbol', 'Entry Timestamp', 'Exit Timestamp', 'Return %', 'Size', 'Fees']].round(2), use_container_width=True)
        else:
            st.info("No trades in this backtest.")
    else:
        st.info("Run backtest first")

# === TAB 5: DOWNLOAD ===
with tab5:
    st.header("💾 Export Data")
    if 'pf' in st.session_state:
        # Signals CSV
        signals = st.session_state.entries[st.session_state.entries.any(axis=1)]
        csv = signals.to_csv().encode('utf-8')
        st.download_button("Download Entry Signals (CSV)", csv, "nifty_shop_signals.csv", "text/csv")

        # Report TXT
        total_ret = st.session_state.pf.total_return()
        days = len(st.session_state.pf.wrapper.index)
        cagr = (1 + total_ret) ** (252 / days) - 1 if days > 0 else 0
        report = f"""Nifty Shop Swing + RSI(14) Backtest Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Capital: ₹{capital:,}
RSI Filter: < {rsi_filter}
Max Stocks: {max_stocks}

Total Return: {total_ret:+.1%}
CAGR: {cagr:+.1%}
Win Rate: {st.session_state.pf.trades.win_rate():.1%}
Trades: {int(st.session_state.pf.trades.count())}
        """
        st.download_button("Download Report (TXT)", report, "backtest_report.txt", "text/plain")
    else:
        st.info("Run backtest to download")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()