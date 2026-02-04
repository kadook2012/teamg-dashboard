import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(layout="wide", page_title="TEAMG Dashboard Baseline")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@st.cache_data(ttl=10)
def load_data():
    # ดึงข้อมูลตรงจากตารางหลัก
    res = supabase.table("teamg_master_analysis").select("*").order("date", desc=True).limit(1000).execute()
    return pd.DataFrame(res.data)

df = load_data()

if not df.empty:
    df.columns = [c.lower() for c in df.columns]
    latest = df.iloc[0]

    st.title(f"🏹 TEAMG Dashboard - Update: {latest['date']}")

    # --- Metrics Section ---
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("ROE (%)", f"{float(latest.get('roe', 0))*100:.2f} %")
    with m2: st.metric("Net Margin (%)", f"{float(latest.get('net_margin', 0))*100:.2f} %")
    with m3: st.metric("Z-Score", f"{float(latest.get('z_score', 0)):.2f}")
    with m4: st.metric("Close Price", f"{latest['close']:.2f}")

    # --- Chart Section ---
    df_plot = df.sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_plot['date'], open=df_plot['open'], 
                                 high=df_plot['high'], low=df_plot['low'], 
                                 close=df_plot['close'], name="TEAMG"))
    
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- Raw Data Table ---
    st.write("### ข้อมูลย้อนหลังล่าสุด")
    st.dataframe(df[['date', 'close', 'rsi', 'z_score', 'roe']].head(10), use_container_width=True)