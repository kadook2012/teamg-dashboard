import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(layout="wide", page_title="TEAMG Stable Dashboard")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@st.cache_data(ttl=10)
def load_data():
    # ดึงจากตารางหลักตรงๆ เลย
    res = supabase.table("teamg_master_analysis").select("*").order("date", desc=True).limit(1000).execute()
    return pd.DataFrame(res.data)

df = load_data()

if not df.empty:
    df.columns = [c.lower() for c in df.columns]
    latest = df.iloc[0]

    st.title(f"🏹 TEAMG Dashboard - {latest['date']}")

    # --- Metrics ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("ROE", f"{float(latest.get('roe', 0))*100:.2f} %")
    with b := c2:
        st.metric("Net Margin", f"{float(latest.get('net_margin', 0))*100:.2f} %")
    with c3:
        st.metric("Z-Score", f"{float(latest.get('z_score', 0)):.2f}")
    with c4:
        st.metric("Close", f"{latest['close']:.2f} THB")

    # --- Chart ---
    df_plot = df.sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_plot['date'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], name="Price"))
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['z_score'], name="Z-Score Trend", yaxis="y2", line=dict(color="#00e5ff")))
    
    fig.update_layout(
        template="plotly_dark", height=600, xaxis_rangeslider_visible=False,
        yaxis2=dict(title="Z-Score", overlaying="y", side="right")
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Raw Data ---
    with st.expander("Check Daily Data (Latest 10 Days)"):
        st.dataframe(df[['date', 'close', 'roe', 'z_score']].head(10))