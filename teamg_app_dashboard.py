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