import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
from dotenv import load_dotenv

# 1. Setup
load_dotenv()
st.set_page_config(layout="wide", page_title="TEAMG Strategic Dashboard V.10")

# 2. CSS เพื่อความชัดเจน (High Contrast & Clear Suffix)
st.markdown("""
    <style>
    /* ปรับแต่ง Metric Box */
    [data-testid="stMetric"] {
        background-color: #263238 !important;
        border: 2px solid #455a64 !important;
        padding: 15px !important;
        border-radius: 12px !important;
    }
    /* หัวข้อสีขาวจ้า */
    [data-testid="stMetricLabel"] p {
        color: #FFFFFF !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        opacity: 1 !important;
    }
    /* ตัวเลขเขียวนีออน */
    [data-testid="stMetricValue"] {
        color: #00ffcc !important;
        font-size: 1.6rem !important;
    }
    /* การแสดงผล News Card */
    .news-card {
        background-color: #0f172a !important;
        border-top: 4px solid #00ffcc !important;
        padding: 15px !important;
        border-radius: 10px !important;
        height: 180px !important;
        margin-bottom: 10px !important;
    }
    .news-title { color: #ffffff !important; font-weight: bold; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Loading
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@st.cache_data(ttl=60)
def load_data():
    m_res = supabase.table("teamg_master_analysis").select("*").order("date").execute()
    n_res = supabase.table("teamg_news_headers").select("*").order("date", desc=True).execute()
    return pd.DataFrame(m_res.data), pd.DataFrame(n_res.data)

df, news_df = load_data()

# --- 4. HEADER: FUNDAMENTAL INSIGHTS (พร้อมหน่วยข้อมูล) ---
st.title("🏹 TEAMG Strategic Dashboard V.10")

if not df.empty:
    curr = df.iloc[-1]
    f1, f2, f3, f4, f5 = st.columns(5)
    with f1: st.metric("Market Cap", f"{curr.get('market_cap', 0)/1e9:.2f} B. THB")
    with f2: st.metric("EV/EBITDA", f"{curr.get('ev_ebitda', 0):.2f} x")
    with f3: st.metric("52W High", f"{curr.get('high_52week', 0):.2f} THB")
    with f4: st.metric("52W Low", f"{curr.get('low_52week', 0):.2f} THB")
    with f5: st.metric("Free Float", f"{curr.get('free_float_pct', 0):.2f} %")

st.write("---")

# --- 5. MAIN CHART: PRICE & AI ALERT ---
st.subheader("📈 Price Action & AI Detection Insights")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

# Candlestick
fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='TEAMG'), row=1, col=1)

# AI Pivot (ปี 2025-2026)
pivots = df[df['is_pivot_high'] == True]
if not pivots.empty:
    fig.add_trace(go.Scatter(x=pivots['date'], y=pivots['high'] * 1.02, mode='markers+text', 
                             text=["<b>AI: Pivot</b>" for _ in range(len(pivots))], textposition="top center",
                             marker=dict(color='#00ffcc', size=10, symbol='diamond'), 
                             textfont=dict(color="#ffffff"), name='AI Alert'), row=1, col=1)

fig.add_trace(go.Bar(x=df['date'], y=df['z_score_price'], name='Volatility (Z-Score)', marker_color='#3b82f6'), row=2, col=1)
fig.update_layout(height=600, template='plotly_dark', xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- 6. LATEST NEWS (4 คอลัมน์แนวนอน) ---
st.write("---")
st.subheader("📰 Market Intelligence (Latest News)")
if not news_df.empty:
    latest_n = news_df.head(4)
    n_cols = st.columns(4)
    for i, col in enumerate(n_cols):
        if i < len(latest_n):
            row = latest_n.iloc[i]
            with col:
                st.markdown(f"""<div class="news-card">
                    <small style="color:#94a3b8;">{row['date']}</small><br>
                    <div class="news-title">{row['header'][:85]}...</div><br>
                    <a href="{row['link']}" target="_blank" style="color:#00ffcc; text-decoration:none; font-size:12px;">อ่านต่อแบบเต็ม →</a>
                </div>""", unsafe_allow_html=True)

# --- 7. STOCK TABLE (เพิ่มหน่วยในหัวข้อคอลัมน์เพื่อความชัดเจน) ---
st.write("---")
with st.expander("🔍 STOCK TABLE", expanded=True):
    if not df.empty:
        # 1. เรียงข้อมูลจากล่าสุดไปอดีต
        df_display = df.sort_values(by='date', ascending=False).copy()
        
        # 2. ปรับแต่งชื่อคอลัมน์เพื่อใส่หน่วย (Unit Suffix)
        df_display = df_display.rename(columns={
            'open': 'Open (THB)',
            'high': 'High (THB)',
            'low': 'Low (THB)',
            'close': 'Close (THB)',
            'volume': 'Volume (Shares)',
            'market_cap': 'Market Cap (THB)',
            'ev_ebitda': 'EV/EBITDA (x)',
            'free_float_pct': 'Free Float (%)',
            'high_52week': '52W High (THB)',
            'low_52week': '52W Low (THB)',
            'net_income': 'Net Income (THB)',
            'operating_cash_flow': 'Op. Cash Flow (THB)',
            'roe': 'ROE (%)',
            'roa': 'ROA (%)',
            'net_margin': 'Net Margin (%)'
        })
        
        st.write("ข้อมูลรายละเอียดหุ้นรายวัน (พร้อมหน่วยกำชัด):")
        st.dataframe(df_display, use_container_width=True, height=400)