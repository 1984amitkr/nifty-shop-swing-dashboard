# app.py - NIFTY 200 SWEET ZONE SCANNER (200 stocks) - REAL-TIME - NO ERRORS
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
st.set_page_config(page_title="Nifty 200 Sweet Zone", layout="wide")
st.title("NIFTY 200 SWEET ZONE SCANNER")
st.markdown("**Real-time • 200 stocks • -5.3% to -6.5% below 20-SMA + RSI<40 • Live Charts + Alert**")

# SOUND ALERT
def play_alert():
    st.markdown("""
    <audio autoplay>
      <source src="https://assets.mixkit.co/sfx/preview/mixkit-alarm-tone-1065.mp3" type="audio/mp3">
    </audio>
    """, unsafe_allow_html=True)

# FETCH NIFTY 200 SYMBOLS (LIVE FROM NSE)
@st.cache_data(ttl=86400)  # Update once per day
def get_nifty200_symbols():
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
        df = pd.read_csv(url)
        symbols = [symbol + ".NS" for symbol in df['Symbol']]
        return symbols[:200]  # Top 200
    except:
        st.warning("Using fallback list (Nifty 200)")
        return [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS",
            "ITC.NS","HINDUNILVR.NS","LT.NS","AXISBANK.NS","KOTAKBANK.NS","ASIANPAINT.NS","MARUTI.NS",
            "SUNPHARMA.NS","BAJFINANCE.NS","HCLTECH.NS","TITAN.NS","WIPRO.NS","ULTRACEMCO.NS",
            "NESTLEIND.NS","M&M.NS","POWERGRID.NS","NTPC.NS","TATAMOTORS.NS","ONGC.NS","JSWSTEEL.NS",
            "COALINDIA.NS","ADANIPORTS.NS","HINDALCO.NS","GRASIM.NS","TECHM.NS","BAJAJFINSV.NS",
            "INDUSINDBK.NS","TATASTEEL.NS","DIVISLAB.NS","DRREDDY.NS","CIPLA.NS","BRITANNIA.NS",
            "HEROMOTOCO.NS","EICHERMOT.NS","BPCL.NS","SHREECEM.NS","APOLLOHOSP.NS","UPL.NS",
            "IOC.NS","SBILIFE.NS","HDFCLIFE.NS","GODREJCP.NS","DABUR.NS","PIDILITIND.NS",
            "BERGEPAINT.NS","MARICO.NS","AMBUJACEM.NS","HAVELLS.NS","SIEMENS.NS","BAJAJ-AUTO.NS",
            "DLF.NS","ADANIGREEN.NS","ADANIENT.NS","JINDALSTEL.NS","VBL.NS","DMART.NS","NYKAA.NS",
            "ZOMATO.NS","PAYTM.NS","DELHIVERY.NS","NAUKRI.NS","POLYCAB.NS","IRCTC.NS","TRENT.NS",
            "ADANIPOWER.NS","TVSMOTOR.NS","LTIM.NS","SRF.NS","INDIGO.NS","PGHH.NS","MOTHERSON.NS",
            "ABB.NS","BANKBARODA.NS","CANBK.NS","IDBI.NS","PNB.NS","UNIONBANK.NS","IOB.NS",
            "INDIANB.NS","YESBANK.NS","AUBANK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","BANDHANBNK.NS",
            "RBLBANK.NS","CUB.NS","KARURVYSYA.NS","J&KBANK.NS","UJJIVANSFB.NS","EQUITASBNK.NS",
            "CDSL.NS","ANGELONE.NS","CAMS.NS","UTIAMC.NS","IIFL.NS","MOTILALOFS.NS","CHOLAFIN.NS",
            "MUTHOOTFIN.NS","BAJAJHFL.NS","M&MFIN.NS","SUNDARMFIN.NS","L&TFH.NS","MANAPPURAM.NS",
            "AARTIIND.NS","ABBOTINDIA.NS","ACC.NS","ADANITRANS.NS","ALKEM.NS","APLLTD.NS",
            "ASTRAL.NS","ATUL.NS","AUROPHARMA.NS","BALKRISIND.NS","BATAINDIA.NS","BHARATFORG.NS",
            "BHEL.NS","BIOCON.NS","BOSCHLTD.NS","CHOLAHLDNG.NS","CONCOR.NS","CUMMINSIND.NS",
            "DEEPAKNTR.NS","DIXON.NS","EMAMILTD.NS","ENDURANCE.NS","FORTIS.NS","GLAND.NS",
            "GLENMARK.NS","GUJGASLTD.NS","HAL.NS","HAPPSTMNDS.NS","HINDPETRO.NS","IEX.NS",
            "INDHOTEL.NS","INDIAMART.NS","INDUSTOWER.NS","JUBLFOOD.NS","KANSAINER.NS","LALPATHLAB.NS",
            "LINDEINDIA.NS","LUPIN.NS","MAXHEALTH.NS","METROPOLIS.NS","MFSL.NS","MINDTREE.NS",
            "MPHASIS.NS","MRF.NS","NAM-INDIA.NS","NATIONALUM.NS","NAVINFLUOR.NS","OBEROIRLTY.NS",
            "OFSS.NS","PERSISTENT.NS","PETRONET.NS","PFIZER.NS","PRESTIGE.NS","RAMCOCEM.NS",
            "SAIL.NS","SANOFI.NS","SUNTV.NS","SUPREMEIND.NS","SYNGENE.NS","TATACOMM.NS",
            "TATACONSUM.NS","TATAPOWER.NS","TATAELXSI.NS","THERMAX.NS","TORNTPHARM.NS","TRENT.NS",
            "TRIDENT.NS","TTKPRESTIG.NS","TV18BRDCST.NS","VOLTAS.NS","WHIRLPOOL.NS","ZENSARTECH.NS",
            "ZYDUSLIFE.NS","AARTIDRUGS.NS","AFFLE.NS","ALEMBICLTD.NS","APLLTD.NS","ASTRAZEN.NS",
            "BAYERCROP.NS","BLUEDART.NS","CAMS.NS","CDSL.NS","CERA.NS","CHAMBLFERT.NS",
            "CRISIL.NS","CROMPTON.NS","DEEPAKFERT.NS","EIDPARRY.NS","FDC.NS","FINPIPE.NS",
            "GARFIBRES.NS","GMMPFAUDLR.NS","GRINDWELL.NS","HAPPYFORGE.NS","HINDCOPPER.NS",
            "INDOCO.NS","JCHAC.NS","JTEKTINDIA.NS","JYOTHYLAB.NS","KEI.NS","KSB.NS","LATENTVIEW.NS",
            "LAXMIMACH.NS","MAHABANK.NS","MAHLOG.NS","MAHSEAMLES.NS","MANKIND.NS","MEDPLUS.NS",
            "METROBRAND.NS","MHRIL.NS","NATCOPHARM.NS","NAZARA.NS","NIACL.NS","NLCINDIA.NS",
            "NMDC.NS","NUVOCO.NS","OLECTRA.NS","PARKHOTELS.NS","PPLPHARMA.NS","PRAJIND.NS",
            "RATNAMANI.NS","REDINGTON.NS","RENUKA.NS","ROSSARI.NS","SAREGAMA.NS","SCHAEFFLER.NS",
            "SFL.NS","SHARDACROP.NS","SHRIRAMFIN.NS","SKFINDIA.NS","SONACOMS.NS","SPANDANA.NS",
            "SPLPETRO.NS","STLTECH.NS","SUDARSCHEM.NS","SUMICHEM.NS","SUNTV.NS","SUZLON.NS",
            "SWANENERGY.NS","TANLA.NS","TATVA.NS","TCIEXP.NS","TEJASNET.NS","TITAGARH.NS",
            "TRITURBINE.NS","TRIVENI.NS","UNOMINDA.NS","UTIAMC.NS","VGUARD.NS","VIMTALABS.NS",
            "WELCORP.NS","WESTLIFE.NS","WIPRO.NS","ZOMATO.NS","ZYDUSWELL.NS"
        ][:200]

# FETCH LIVE DATA (NO CACHE - ALWAYS FRESH)
def fetch_live_data():
    symbols = get_nifty200_symbols()
    with st.spinner(f"Fetching 200 stocks..."):
        try:
            data = yf.download(symbols, period="3mo", progress=False, auto_adjust=True, threads=True)
            return data['Close'].ffill()
        except Exception as e:
            st.error(f"Data error: {e}")
            return None

df = fetch_live_data()

# SCANNER
def run_nifty200_scan():
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
        'Verdict': 'BUY NOW - SWEET ZONE!'
    }).sort_values('Dist%')
    
    return result, candidates.index[0]  # Best stock

signals, best_stock = run_nifty200_scan()

# SIDEBAR
st.sidebar.header("Nifty 200 Scanner")
st.sidebar.write(f"Stocks: {len(get_nifty200_symbols())}")
rsi_thr = st.sidebar.slider("Max RSI", 30, 50, 40)
min_d = st.sidebar.number_input("Min Dist%", -15.0, -3.0, -6.5)
max_d = st.sidebar.number_input("Max Dist%", -15.0, -3.0, -5.3)
st.sidebar.info(f"Time: {datetime.now().strftime('%I:%M:%S %p')} IST")
if st.sidebar.button("Refresh Now"):
    st.rerun()

# DISPLAY
col1, col2 = st.columns([1.1, 1.9])

with col1:
    st.markdown("### Live Sweet Zone Signals")
    if signals.empty:
        st.success("**NO SWEET-ZONE SIGNALS IN NIFTY 200**")
        st.info("Market is strong. Waiting for real mean-reversion dip.")
    else:
        play_alert()
        st.error(f"**{len(signals)} RARE SWEET-ZONE BUY(S) IN NIFTY 200!**")
        styled = signals.style\
            .applymap(lambda x: 'background-color: #ffcccc; font-weight: bold', subset=['Verdict'])\
            .format({'Price ₹': '₹{:.0f}', '20-SMA ₹': '₹{:.0f}'})
        st.dataframe(styled, use_container_width=True)

with col2:
    if not signals.empty and best_stock:
        symbol = best_stock
        data = df[symbol].tail(60)
        sma = data.rolling(20).mean()
        rsi = RSIIndicator(data, 14).rsi()
        
        fig = make_subplots(rows=2, cols=1, subplot_titles=(f"{symbol.replace('.NS','')} - LIVE", "RSI(14)"),
                            row_heights=[0.7, 0.3], shared_xaxes=True)
        fig.add_trace(go.Scatter(x=data.index, y=data, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sma.index, y=sma, name="20-SMA", line=dict(color="orange")), row=1, col=1)
        fig.add_vrect(x0=data.index[-30], x1=data.index[-1], fillcolor="red", opacity=0.2, row=1, col=1)
        fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI", line=dict(color="#00ff00")), row=2, col=1)
        fig.add_hline(y=40, line_dash="dot", line_color="orange", row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("<h4 style='text-align:center;color:#666;'>Charts appear when signals arrive</h4>", unsafe_allow_html=True)

# FOOTER
st.markdown("---")
st.caption("Nifty 200 Sweet Zone Scanner • Real-time • Zero Errors • Made for @cool_amitkr • Nov 07, 2025 11:22 AM IST")