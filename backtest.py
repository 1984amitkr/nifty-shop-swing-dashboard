import yfinance as yf
import pandas as pd
import numpy as np
import vectorbt as vbt
from ta.momentum import RSIIndicator

def run_backtest(
    symbols=None,
    start="2015-01-01",
    end="2025-11-01",
    capital=100000,
    rsi_threshold=40,
    max_positions=5
):
    if symbols is None:
        symbols = "RELIANCE.NS TCS.NS HDFCBANK.NS INFY.NS ICICIBANK.NS SBIN.NS BHARTIARTL.NS ITC.NS HINDUNILVR.NS LT.NS".split()

    # Download
    data = yf.download(symbols, start=start, end=end)
    close = data['Close']
    open_ = data['Open']

    # Indicators
    sma20 = close.rolling(20).mean()
    rsi = close.apply(lambda x: RSIIndicator(x, 14).rsi())
    dist = (close - sma20) / sma20

    entries = pd.DataFrame(False, index=close.index, columns=close.columns)
    exits = pd.DataFrame(False, index=close.index, columns=close.columns)

    # Portfolio
    pf = vbt.Portfolio.from_orders(
        close, size=np.nan, init_cash=capital, cash_sharing=True, group_by=True
    )

    # Scan loop
    for date in close.index[35:]:
        if date not in open_.index: continue
        c, o, s, r, d = close.loc[date], open_.loc[date], sma20.loc[date], rsi.loc[date], dist.loc[date]

        # Scan
        valid = (r < rsi_threshold) & (d < 0)
        candidates = d[valid].nsmallest(max_positions)
        for sym in candidates.index:
            pos = pf.positions[sym]
            if pos.count() == 0 or pos.is_flat():
                entries.loc[date, sym] = True

        # Avg down & exit
        for sym in close.columns:
            pos = pf.positions[sym]
            if pos.count() > 0 and not pos.is_flat():
                avg = pos.avg_price()
                if c[sym] < avg * 0.97:
                    entries.loc[date, sym] = True
                if c[sym] >= avg * 1.08:
                    exits.loc[date, sym] = True

    # Final PF
    size = capital * 0.20 / max_positions
    pf = vbt.Portfolio.from_signals(
        close, open_, entries, exits,
        size=size, size_type='value', init_cash=capital,
        fees=0.001, freq='1D'
    )

    return pf, entries, close, sma20, rsi, dist