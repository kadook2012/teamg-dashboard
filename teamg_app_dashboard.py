import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(layout="wide", page_title="TEAMG Dashboard")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@st.cache_data(ttl=10)
def load_data():
    # ดึงจาก View ที่เราสร้างไว้
    m_res = supabase.table("teamg_master_view").select("*").order("date", desc=True).limit(1000).execute()
    n_res = supabase.table("teamg_news_headers").select("*").order("date", desc=True).limit(8).execute()
    return pd.DataFrame(m_res.data), pd.DataFrame(n_res.data)

df_raw, news_df = load_data()

if not df_raw.empty:
    df_raw.columns = [c.lower() for c in df_raw.columns]
    latest = df_raw.iloc[0] # ข้อมูลวันล่าสุด (เช่น 4 ก.พ. 2026)

    st.title(f"🏹 TEAMG Dashboard - Update: {latest['date']}")

    # --- Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        roe = latest.get('roe', 0)
        st.metric("ROE", f"{float(roe or 0)*100:.2f} %")
    with m2:
        margin = latest.get('net_margin', 0)
        st.metric("Net Margin", f"{float(margin or 0)*100:.2f} %")
    with m3:
        mcap = latest.get('market_cap', 0)
        st.metric("Market Cap", f"{float(mcap or 0)/1e9:.2f} B")
    with m4:
        zscore = latest.get('z_score', 0)
        st.metric("Z-Score", f"{float(zscore or 0):.2f}")

    # --- Chart ---
    df_plot = df_raw.sort_values("date")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df_plot['date'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['z_score'], name="Z-Score", line=dict(color='#00e5ff')), row=2, col=1)
    fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- Table ---
    with st.expander("View Raw Data"):
        st.dataframe(df_raw[['date', 'close', 'roe', 'z_score']], use_container_width=True)