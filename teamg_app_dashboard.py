import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
from dotenv import load_dotenv

# --- 1. SETTING & THEME (V.10 STYLE) ---
load_dotenv()
st.set_page_config(layout="wide", page_title="TEAMG Strategic Dashboard V.10 (Technical Upgrade)")

st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 12px;
    }
    [data-testid="stMetricValue"] { color: #00ff88 !important; }
    .news-card {
        background-color: #0f172a;
        padding: 15px;
        border-radius: 10px;
        border-top: 3px solid #00e5ff;
        height: 160px;
        margin-bottom: 15px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA CONNECTION ---
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

@st.cache_data(ttl=60)
def load_all_data():
    # ดึงข้อมูล 2,000 แถวเพื่อให้ครอบคลุมข้อมูล 5 ปีถึงปัจจุบัน
    m_res = supabase.table("teamg_master_analysis").select("*").order("date", desc=False).limit(2000).execute()
    n_res = supabase.table("teamg_news_headers").select("*").order("date", desc=True).limit(8).execute()
    return pd.DataFrame(m_res.data), pd.DataFrame(n_res.data)

df, news_df = load_all_data()
if not df.empty:
    df.columns = [col.lower() for col in df.columns]

# --- 3. HEADER (V.10 STYLE) ---
st.title("🏹 TEAMG Strategic Dashboard (V.10 Core + Technical)")
if not df.empty:
    st.info(f"📅 Data Updated: **{df['date'].iloc[-1]}**")

# --- 4. TOP SECTION: FINANCIAL HEALTH (DuPont V.10) ---
st.subheader("💎 Financial Health Insights (DuPont)")
if not df.empty:
    latest = df.iloc[-1]
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Efficiency (ROE)", f"{latest.get('roe', 0)*100:.2f} %")
    with m2: st.metric("Profitability (Margin)", f"{latest.get('net_margin', 0)*100:.2f} %")
    with m3: st.metric("Asset Velocity (ATO)", f"{latest.get('asset_turnover', 0):.2f} x")
    with m4: st.metric("Z-Score (Volatility)", f"{latest.get('z_score', 0):.2f}")

st.write("---")

# --- 5. MIDDLE SECTION: TECHNICAL GRAPH (4 Layers) ---
st.subheader("📊 Multi-Layer Technical Analysis")

fig = make_subplots(
    rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
    row_heights=[0.4, 0.2, 0.2, 0.2],
    subplot_titles=("Price & AI Pivot High", "RSI Momentum", "MACD Trend", "Z-Score")
)

# Layer 1: Price + EMA + AI Pivot
fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['ema_50'], name='EMA 50', line=dict(color='orange', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['ema_200'], name='EMA 200', line=dict(color='red', width=1.5)), row=1, col=1)

# AI Pivot High (แสดงผลย้อนหลังตามข้อมูลใน DB)
if 'is_pivot_high' in df.columns:
    pivots = df[df['is_pivot_high'] == True]
    fig.add_trace(go.Scatter(x=pivots['date'], y=pivots['high']*1.02, mode='markers', 
                             marker=dict(color='#00e5ff', size=7, symbol='diamond'), name='AI Pivot'), row=1, col=1)

# Layer 2: RSI
fig.add_trace(go.Scatter(x=df['date'], y=df['rsi'], name='RSI', line=dict(color='purple')), row=2, col=1)
fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

# Layer 3: MACD
fig.add_trace(go.Bar(x=df['date'], y=df['macd_hist'], name='MACD Hist'), row=3, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['macd'], name='MACD Line', line=dict(color='blue')), row=3, col=1)

# Layer 4: Z-Score
fig.add_trace(go.Scatter(x=df['date'], y=df['z_score'], name='Z-Score', fill='tozeroy', line=dict(color='#00e5ff')), row=4, col=1)
fig.add_hline(y=2, line_dash="dash", line_color="red", row=4, col=1); fig.add_hline(y=-2, line_dash="dash", line_color="green", row=4, col=1)

fig.update_layout(height=1000, template='plotly_dark', xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- 6. BOTTOM SECTION: NEWS TIMELINE (Grid 4 Columns V.10 Style) ---
st.write("---")
st.subheader("📰 Market Intelligence Timeline")
if not news_df.empty:
    n_display = news_df.head(8)
    for i in range(0, len(n_display), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(n_display):
                row = n_display.iloc[i + j]
                with col:
                    st.markdown(f"""
                        <div class="news-card">
                            <small style='color: #64748b;'>{row['date']} | {row['source']}</small><br>
                            <p style='color: #e2e8f0; font-weight: bold; font-size: 13px; margin-top:8px;'>{row['header'][:80]}...</p>
                            <a href='{row['link']}' target='_blank' style='color: #00e5ff; font-size: 11px; text-decoration: none;'>Read More →</a>
                        </div>
                    """, unsafe_allow_html=True)

# --- 7. RAW DATA EXPLORER (ล่าสุดขึ้นก่อน) ---
with st.expander("🔍 Raw Data Explorer (Latest -> Past)"):
    st.dataframe(df.sort_values('date', ascending=False), use_container_width=True)