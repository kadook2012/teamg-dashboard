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

# --- 2. DATA CONNECTION ---
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

@st.cache_data(ttl=10)
def load_all_data():
    # ดึงข้อมูลจาก View ที่เราเพิ่งสร้างใหม่
    m_res = supabase.table("teamg_master_view").select("*").order("date", desc=True).limit(2000).execute()
    n_res = supabase.table("teamg_news_headers").select("*").order("date", desc=True).limit(8).execute()
    
    df_raw = pd.DataFrame(m_res.data)
    if not df_raw.empty:
        df_raw.columns = [col.lower() for col in df_raw.columns]
        df_plot = df_raw.sort_values("date", ascending=True)
        return df_raw, df_plot, pd.DataFrame(n_res.data)
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_raw, df_plot, news_df = load_all_data()

# --- 3. DISPLAY ---
if not df_raw.empty:
    latest = df_raw.iloc[0]
    st.title(f"🏹 TEAMG Strategic Dashboard - {latest['date']}")
    
    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("ROE", f"{float(latest.get('roe', 0))*100:.2f} %")
    with m2: st.metric("Net Margin", f"{float(latest.get('net_margin', 0))*100:.2f} %")
    with m3: st.metric("Market Cap", f"{float(latest.get('market_cap', 0))/1e9:.2f} B")
    with m4: st.metric("Z-Score", f"{float(latest.get('z_score', 0)):.2f}")

    # Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df_plot['date'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['z_score'], name='Z-Score', fill='tozeroy'), row=2, col=1)
    
    fig.update_layout(height=800, template='plotly_dark', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 View Raw Data"):
        st.dataframe(df_raw[['date', 'close', 'roe', 'z_score']].head(10))