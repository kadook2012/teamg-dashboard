import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
from plotly.subplots import make_subplots

load_dotenv()

st.set_page_config(page_title="TEAMG Strategic Dashboard", layout="wide")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

@st.cache_data(ttl=3600)
def load_data():
    # ดึงข้อมูลจากตารางมาสเตอร์ตามรูป Bible
    response = supabase.table("teamg_master_analysis").select("*").order("date", desc=False).execute()
    return pd.DataFrame(response.data)

df = load_data()

st.title("🏹 TEAMG Strategic Analysis (V.11)")
st.write(f"Data period: 5 Years | Latest update: {df['date'].iloc[-1]}")

# --- กราฟ Technical วิเคราะห์ 3 ชั้น ---
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, row_heights=[0.5, 0.25, 0.25],
                    subplot_titles=("Price & EMA", "RSI Momentum", "MACD Trend"))

# 1. Price + EMA 50/200
fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], 
                             low=df['low'], close=df['close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['ema_50'], name='EMA 50', line=dict(color='orange')), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['ema_200'], name='EMA 200', line=dict(color='red')), row=1, col=1)

# 2. RSI
fig.add_trace(go.Scatter(x=df['date'], y=df['rsi'], name='RSI', line=dict(color='purple')), row=2, col=1)
fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1, annotation_text="Overbought")
fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1, annotation_text="Oversold")

# 3. MACD
fig.add_trace(go.Bar(x=df['date'], y=df['macd_hist'], name='MACD Histogram'), row=3, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['macd'], name='MACD Line', line=dict(color='blue')), row=3, col=1)

fig.update_layout(height=900, xaxis_rangeslider_visible=False, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# --- Statistical Scoreboard ---
st.subheader("📌 Key Strategic Indicators")
c1, c2, c3, c4 = st.columns(4)
c1.metric("EMA 200 Status", "Bullish" if df['close'].iloc[-1] > df['ema_200'].iloc[-1] else "Bearish")
c2.metric("RSI (14)", f"{df['rsi'].iloc[-1]:.2f}")
c3.metric("Z-Score (Volatility)", f"{df['z_score'].iloc[-1]:.2f}")
c4.metric("Rel. Volume (20D)", f"{df['rel_vol'].iloc[-1]:.2fx}")

st.dataframe(df.tail(30))