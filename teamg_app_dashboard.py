import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
from dotenv import load_dotenv

# --- 1. SETTING & THEME ---
load_dotenv()
st.set_page_config(layout="wide", page_title="TEAMG Strategic Dashboard")

st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #1e293b; 
        border: 1px solid #475569;
        padding: 20px;
        border-radius: 12px;
    }
    [data-testid="stMetricLabel"] {
        color: #f8fafc !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }
    [data-testid="stMetricValue"] { 
        color: #00ff88 !important; 
    }
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

@st.cache_data(ttl=10)
def load_all_data():
    # ดึงข้อมูลจาก View ที่เราสร้าง (รวมราคา + พื้นฐานแล้ว)
    m_res = supabase.table("teamg_master_view").select("*").order("date", desc=True).limit(2000).execute()
    # ดึงข่าวจากตารางข่าวปกติ
    n_res = supabase.table("teamg_news_headers").select("*").order("date", desc=True).limit(8).execute()
    
    df_raw = pd.DataFrame(m_res.data)
    if not df_raw.empty:
        df_raw.columns = [col.lower() for col in df_raw.columns]
        # บังคับให้ชื่อ Z-Score ตรงกับที่กราฟเรียกใช้
        if 'z_score' not in df_raw.columns and 'z_score_price' in df_raw.columns:
            df_raw['z_score'] = df_raw['z_score_price']
            
        df_plot = df_raw.sort_values("date", ascending=True)
        return df_raw, df_plot, pd.DataFrame(n_res.data)
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_raw, df_plot, news_df = load_all_data()

# --- 3. HEADER ---
st.title("🏹 TEAMG Strategic Dashboard V.11.8")
if not df_raw.empty:
    latest_date = df_raw['date'].iloc[0]
    st.success(f"✅ ข้อมูลอัปเดตล่าสุด: **{latest_date}**")

# --- 4. TOP SECTION: FINANCIAL HEALTH (แสดงค่าจาก View) ---
st.subheader("💎 Financial Health Insights (DuPont)")
if not df_raw.empty:
    latest_fin = df_raw.iloc[0]
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: 
        roe = float(latest_fin.get('roe', 0)) * 100 if latest_fin.get('roe') else 0
        st.metric("Efficiency (ROE)", f"{roe:.2f} %")
    with m2: 
        margin = float(latest_fin.get('net_margin', 0)) * 100 if latest_fin.get('net_margin') else 0
        st.metric("Profitability (Margin)", f"{margin:.2f} %")
    with m3: 
        # ใช้ Market Cap หรือ Asset Turnover ตามที่คุณต้องการ
        m_cap = float(latest_fin.get('market_cap', 0)) / 1e6 if latest_fin.get('market_cap') else 0
        st.metric("Market Cap (M)", f"{m_cap:,.0f} THB")
    with m4: 
        z_val = float(latest_fin.get('z_score', 0)) if latest_fin.get('z_score') else 0
        st.metric("Z-Score (Volatility)", f"{z_val:.2f}")

st.write("---")

# --- 5. MIDDLE SECTION: TECHNICAL GRAPH ---
st.subheader("📊 Multi-Layer Technical Analysis")
if not df_plot.empty:
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.4, 0.15, 0.2, 0.25],
        subplot_titles=("Price & Indicators", "RSI Momentum", "MACD Trend", "Z-Score")
    )

    # Price Chart
    fig.add_trace(go.Candlestick(x=df_plot['date'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['ema_50'], name='EMA 50', line=dict(color='orange', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['ema_200'], name='EMA 200', line=dict(color='red', width=1.5)), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['rsi'], name='RSI', line=dict(color='purple')), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

    # MACD
    if 'macd_hist' in df_plot.columns:
        fig.add_trace(go.Bar(x=df_plot['date'], y=df_plot['macd_hist'], name='MACD Hist'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['macd'], name='MACD Line', line=dict(color='blue')), row=3, col=1)

    # Z-Score
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['z_score'], name='Z-Score', fill='tozeroy', line=dict(color='#00e5ff')), row=4, col=1)
    fig.add_hline(y=2, line_dash="dash", line_color="red", row=4, col=1)
    fig.add_hline(y=-2, line_dash="dash", line_color="green", row=4, col=1)

    fig.update_layout(height=1000, template='plotly_dark', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- 6. BOTTOM SECTION: NEWS TIMELINE ---
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

# --- 7. RAW DATA EXPLORER ---
with st.expander("🔍 Raw Data Explorer", expanded=True):
    display_map = {
        "date": "Date", "close": "Close (THB)", "rsi": "RSI", 
        "z_score": "Z-Score", "ema_50": "EMA50", "ema_200": "EMA200", 
        "roe": "ROE (%)", "net_margin": "Net Margin (%)"
    }
    # กรองคอลัมน์ที่มีอยู่จริงมาแสดง
    cols_to_show = [k for k in display_map.keys() if k in df_raw.columns]
    st.dataframe(df_raw[cols_to_show].rename(columns=display_map), use_container_width=True)