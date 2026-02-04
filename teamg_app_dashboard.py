import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
from dotenv import load_dotenv

# --- 1. SETTING & THEME (คงเดิม) ---
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

# --- 2. DATA CONNECTION (ปรับดึงผ่าน View เพื่อให้ได้ข้อมูลครบแบบเดิม) ---
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

@st.cache_data(ttl=10)
def load_all_data():
    # เปลี่ยนจากดึงตารางตรงๆ เป็นดึงผ่าน View (v_stock_master_full)
    m_res = supabase.table("v_stock_master_full").select("*").order("date", desc=True).limit(2000).execute()
    n_res = supabase.table("teamg_news_headers").select("*").order("date", desc=True).limit(8).execute()
    
    df_raw = pd.DataFrame(m_res.data)
    if not df_raw.empty:
        df_raw.columns = [col.lower() for col in df_raw.columns]
        # Mapping ค่า z_score ให้รองรับชื่อคอลัมน์ใหม่
        if 'z_score' not in df_raw.columns and 'z_score_price' in df_raw.columns:
            df_raw['z_score'] = df_raw['z_score_price']
            
        df_plot = df_raw.sort_values("date", ascending=True)
        return df_raw, df_plot, pd.DataFrame(n_res.data)
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_raw, df_plot, news_df = load_all_data()

# --- 3. HEADER (คงเดิม) ---
st.title("🏹 TEAMG Strategic Dashboard V.11.7 (Latest)")
if not df_raw.empty:
    latest_date = df_raw['date'].iloc[0]
    st.success(f"✅ ข้อมูลในระบบอัปเดตล่าสุดถึงวันที่: **{latest_date}**")

# --- 4. TOP SECTION: FINANCIAL HEALTH (แสดงผลแบบเดิม) ---
st.subheader("💎 Financial Health Insights (DuPont)")
if not df_raw.empty:
    # เลือกแถวล่าสุด
    latest_fin = df_raw.iloc[0]
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: 
        val = latest_fin.get('roe', 0)
        st.metric("Efficiency (ROE)", f"{float(val)*100 if val else 0:.2f} %")
    with m2: 
        val = latest_fin.get('net_margin', 0)
        st.metric("Profitability (Margin)", f"{float(val)*100 if val else 0:.2f} %")
    with m3: 
        val = latest_fin.get('asset_turnover', 0)
        st.metric("Asset Velocity (ATO)", f"{float(val) if val else 0:.2f} x")
    with m4: 
        val = latest_fin.get('z_score', 0)
        st.metric("Z-Score (Volatility)", f"{float(val) if val else 0:.2f}")

st.write("---")

# --- 5. MIDDLE SECTION: TECHNICAL GRAPH (คงเดิม) ---
st.subheader("📊 Multi-Layer Technical Analysis")
fig = make_subplots(
    rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
    row_heights=[0.4, 0.15, 0.2, 0.25],
    subplot_titles=("Price & AI Pivot High", "RSI Momentum", "MACD Trend", "Z-Score")
)

fig.add_trace(go.Candlestick(x=df_plot['date'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['ema_50'], name='EMA 50', line=dict(color='orange', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['ema_200'], name='EMA 200', line=dict(color='red', width=1.5)), row=1, col=1)

if 'is_pivot_high' in df_plot.columns:
    pivots = df_plot[df_plot['is_pivot_high'] == True]
    fig.add_trace(go.Scatter(x=pivots['date'], y=pivots['high']*1.02, mode='markers', marker=dict(color='#00e5ff', size=7, symbol='diamond'), name='AI Pivot'), row=1, col=1)

fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['rsi'], name='RSI', line=dict(color='purple')), row=2, col=1)
fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1); fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

fig.add_trace(go.Bar(x=df_plot['date'], y=df_plot['macd_hist'], name='MACD Hist'), row=3, col=1)
fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['macd'], name='MACD Line', line=dict(color='blue')), row=3, col=1)

fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['z_score'], name='Z-Score', fill='tozeroy', line=dict(color='#00e5ff')), row=4, col=1)
fig.add_hline(y=2, line_dash="dash", line_color="red", row=4, col=1); fig.add_hline(y=-2, line_dash="dash", line_color="green", row=4, col=1)

fig.update_layout(height=1100, template='plotly_dark', xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- 6. BOTTOM SECTION: NEWS TIMELINE (คงเดิม) ---
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

# --- 7. RAW DATA EXPLORER (คงเดิม) ---
with st.expander("🔍 Raw Data Explorer (Latest -> Past)", expanded=True):
    display_map = {
        "date": "Date", "close": "Close (THB)", "rsi": "RSI (14)", 
        "z_score": "Z-Score", "ema_50": "EMA50", "ema_200": "EMA200", 
        "roe": "ROE (%)", "net_margin": "Net Margin (%)", "asset_turnover": "ATO (x)"
    }
    df_view = df_raw.rename(columns=display_map)
    cols_to_show = [v for k, v in display_map.items() if k in df_raw.columns]
    st.dataframe(df_view[cols_to_show], use_container_width=True)