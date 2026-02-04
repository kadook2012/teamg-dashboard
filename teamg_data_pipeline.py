import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def run_pipeline(symbol="TEAMG.BK"):
    print(f"🚀 Processing {symbol}...")
    ticker = yf.Ticker(symbol)
    
    # 1. ดึง Fundamental
    info = ticker.info
    roe = info.get("returnOnEquity")
    margin = info.get("profitMargins")
    m_cap = info.get("marketCap")

    # 2. ดึงราคา 2 ปี (เพื่อให้ Z-Score และ EMA ไม่ Null)
    df = yf.download(symbol, period="2y", interval="1d", auto_adjust=True)
    if df.empty: return

    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]

    # 3. คำนวณ Technical (เน้น Z-Score ต้องไม่ Null)
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # คำนวณ Z-Score ย้อนหลัง 20 วัน
    rolling_mean = df['close'].rolling(window=20, min_periods=1).mean()
    rolling_std = df['close'].rolling(window=20, min_periods=1).std()
    df['z_score'] = (df['close'] - rolling_mean) / rolling_std

    # 4. ฝังข้อมูลทุกอย่างลงใน DataFrame เดียวกัน
    df['symbol'] = symbol
    df['roe'] = roe
    df['net_margin'] = margin
    df['market_cap'] = m_cap
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

    # ล้างค่า NaN/Inf ก่อนส่ง
    records = df.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient='records')
    
    # 5. Upsert เข้าตารางหลัก
    supabase.table("teamg_master_analysis").upsert(records).execute()
    print(f"✅ {symbol} Data Synced Successfully!")

if __name__ == "__main__":
    run_pipeline()