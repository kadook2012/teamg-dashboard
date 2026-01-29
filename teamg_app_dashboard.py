import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(layout="wide", page_title="TEAMG Strategic V.11.3")

# Custom CSS
st.markdown("""
    <style>
    [data-testid="stMetric"] { background-color: #1e293b; border: 1px solid #334155; padding: 15px; border-radius: 10px; }
    .news-card { background-color: #0f172a; padding: 12px; border-radius: 8px; border-top: 3px solid #00e5ff; height: 150px; margin-bottom: 10px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)

url = os.getenv("SUPABASE_URL"); key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

@st.cache_data(ttl=60)
def load_data():
    m_res = supabase.table("teamg_master_analysis").select("*").order("date", desc=False).limit(2000).execute()
    n_res = supabase.table("teamg_news_headers").select("*").order("date", desc=True).limit(12).execute()
    return pd.DataFrame(m_res.data), pd.DataFrame(n_res.data)

df, news_df = load_data()
df.columns = [col.lower() for col in df.columns]

st.title("🏹 TEAMG Strategic Dashboard (Technical + Z-Score)")

# --- กราฟ 4 ชั้น (Price, RSI, MACD, Z-Score) ---
fig = make_subplots(
    rows=4, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.04,
    row_heights=[0.4, 0.2, 0.2, 0.2],
    subplot_titles=("Price & EMA (50/200)", "RSI Momentum", "MACD Trend", "Z-Score (Statistical Volatility)")
)

# 1. Price + EMA 50/200
fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['ema_50'], name='EMA 50', line=dict(color='orange', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['ema_200'], name='EMA 200', line=dict(color='red', width=1.5)), row=1, col=1)

# 2. RSI
fig.add_trace(go.Scatter(x=df['date'], y=df['rsi'], name='RSI', line=dict(color='purple')), row=2, col=1)
fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

# 3. MACD
fig.add_trace(go.Bar(x=df['date'], y=df['macd_hist'], name='MACD Hist', marker_color='gray'), row=3, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['macd'], name='MACD', line=dict(color='blue')), row=3, col=1)

# 4. Z-Score (เพิ่มส่วนนี้ตามคำขอ)
# ใช้ fill='tozeroy' เพื่อให้เห็นพื้นที่ความผันผวนชัดเจน
fig.add_trace(go.Scatter(
    x=df['date'], 
    y=df['z_score'], 
    name='Z-Score', 
    fill='tozeroy', 
    line=dict(color='#00e5ff', width=1.5)
), row=4, col=1)

# เส้น Standard Deviation Threshold
fig.add_hline(y=2, line_dash="dash", line_color="red", row=4, col=1, annotation_text="+2 SD (Extreme High)")
fig.add_hline(y=-2, line_dash="dash", line_color="green", row=4, col=1, annotation_text="-2 SD (Extreme Low)")
fig.add_hline(y=0, line_color="white", opacity=0.3, row=4, col=1)

fig.update_layout(height=1100, template='plotly_dark', xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# ส่วน Raw Data (เรียงล่าสุดขึ้นก่อน)
with st.expander("🔍 Raw Data Explorer (5 Years)"):
    st.dataframe(df.sort_values('date', ascending=False), use_container_width=True)