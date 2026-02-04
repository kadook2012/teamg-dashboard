import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def run_pipeline(symbol="TEAMG.BK"):
    print(f"🚀 เริ่มต้นดึงข้อมูล {symbol}...")
    ticker = yf.Ticker(symbol)
    
    # 1. ดึงข้อมูลราคาและตัวแปรเทคนิคัล
    df = yf.download(symbol, period="2y", interval="1d", auto_adjust=True)
    if df.empty: return

    # จัดการชื่อคอลัมน์ให้เป็นมาตรฐาน
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]

    # คำนวณ Technical Indicators
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))

    # Z-Score (ใช้ Window 20 วัน)
    df['z_score'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).std()

    # 2. ดึงข้อมูลงบการเงินมาแปะรวม
    info = ticker.info
    df['roe'] = info.get("returnOnEquity")
    df['net_margin'] = info.get("profitMargins")
    df['market_cap'] = info.get("marketCap")
    df['symbol'] = symbol
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

    # 3. ส่งข้อมูลขึ้นตารางหลัก (Upsert)
    records = df.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient='records')
    supabase.table("teamg_master_analysis").upsert(records).execute()
    print(f"✅ ข้อมูลถูกอัปเดตเรียบร้อยแล้ว!")

if __name__ == "__main__":
    run_pipeline()