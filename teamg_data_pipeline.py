import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv

# --- 1. SETTING ---
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

STOCKS = ["TEAMG.BK"]

def get_and_upsert_info(symbol):
    """ดึงข้อมูลพื้นฐาน (ROE, Net Margin) ส่งไปที่ตาราง info"""
    print(f"📊 กำลังดึงข้อมูลพื้นฐานสำหรับ {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        info_data = {
            "symbol": symbol,
            "company_name": info.get("longName"),
            "market_cap": info.get("marketCap"),
            "roe": info.get("returnOnEquity"),
            "net_margin": info.get("profitMargins")
        }
        
        # ล้างค่า NULL และส่งขึ้น Supabase
        cleaned_info = {k: v for k, v in info_data.items() if v is not None}
        supabase.table("teamg_master_info").upsert(cleaned_info).execute()
        print(f"✅ อัปเดตข้อมูลพื้นฐาน {symbol} สำเร็จ")
    except Exception as e:
        print(f"❌ Error (Info): {e}")

def get_and_upsert_analysis(symbol):
    """ดึงข้อมูลราคาและคำนวณ Technical ส่งไปที่ตาราง analysis"""
    print(f"🚀 กำลังดึงราคาและวิเคราะห์เทคนิคัลสำหรับ {symbol}...")
    try:
        # ดึงย้อนหลัง 2 ปีเพื่อให้ EMA200 และ Z-Score นิ่ง
        df = yf.download(symbol, period="2y", interval="1d", auto_adjust=True)
        if df.empty: return

        # ปรับชื่อคอลัมน์
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]

        # --- คำนวณ Technical Indicators ---
        # EMA
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))

        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # Z-Score (ใช้ window 20)
        df['z_score'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).std()
        
        # จัดการข้อมูลก่อนส่ง
        df['symbol'] = symbol
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # แปลงเป็น List of Dictionaries และล้างค่า NaN
        records = df.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient='records')
        
        # ส่งขึ้น Supabase
        supabase.table("teamg_master_analysis").upsert(records).execute()
        print(f"✅ อัปเดตราคาและเทคนิคัล {symbol} สำเร็จ")
        
    except Exception as e:
        print(f"❌ Error (Analysis): {e}")

# --- START ---
if __name__ == "__main__":
    for s in STOCKS:
        print(f"\n--- เริ่มต้นจัดการหุ้น: {s} ---")
        get_and_upsert_info(s)      # อัปเดตพื้นฐานก่อน
        get_and_upsert_analysis(s)  # ตามด้วยราคา
    print("\n🎉 ดึงข้อมูลสำเร็จทุกตาราง!")