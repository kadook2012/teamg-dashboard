import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv

# --- 1. INITIAL SETTING ---
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# รายชื่อหุ้น (อนาคตเพิ่มได้ถึง 800 ตัว)
STOCKS = ["TEAMG.BK"] 

def get_and_upsert_info(symbol):
    """ดึงข้อมูลงบการเงินและข้อมูลบริษัทเข้าตาราง master_info"""
    print(f"📊 Fetching info for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        info_data = {
            "symbol": symbol,
            "company_name": info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "net_margin": info.get("profitMargins")
        }
        
        # ล้างค่าที่เป็น NaN เพื่อป้องกัน Error
        info_cleaned = {k: (v if pd.notnull(v) else None) for k, v in info_data.items()}
        
        supabase.table("teamg_master_info").upsert(info_cleaned).execute()
        print(f"✅ Info updated for {symbol}")
    except Exception as e:
        print(f"❌ Error updating info for {symbol}: {e}")

def calculate_technical(df):
    """คำนวณ Technical Indicators ตามโครงสร้างเดิมที่ Dashboard ต้องการ"""
    # EMA
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    window = 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Z-Score (เทียบกับราคาเฉลี่ย 20 วัน)
    df['z_score'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).std()
    
    return df

def get_and_upsert_analysis(symbol):
    """ดึงราคาและคำนวณ Technical เข้าตาราง master_analysis"""
    print(f"🚀 Fetching price analysis for {symbol}...")
    try:
        df = yf.download(symbol, period="2y", interval="1d", auto_adjust=True)
        if df.empty: return

        # จัดการชื่อคอลัมน์ให้เป็นตัวเล็ก
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]

        # คำนวณค่าต่างๆ
        df = calculate_technical(df)
        df['symbol'] = symbol
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # แทนที่ค่า NaN/Inf ด้วย None เพื่อให้ Supabase รับได้
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        
        # แปลงเป็น List of Dicts
        records = df.to_dict(orient='records')
        
        # Upsert ทีละ Batch เพื่อความเสถียร
        supabase.table("teamg_master_analysis").upsert(records).execute()
        print(f"✅ Price analysis updated for {symbol} ({len(records)} rows)")
    except Exception as e:
        print(f"❌ Error updating analysis for {symbol}: {e}")

# --- 2. EXECUTION ---
if __name__ == "__main__":
    for s in STOCKS:
        print(f"--- Processing {s} ---")
        get_and_upsert_info(s)      # อัปเดตข้อมูลพื้นฐาน (ลง table: teamg_master_info)
        get_and_upsert_analysis(s)  # อัปเดตราคาและเทคนิคัล (ลง table: teamg_master_analysis)
        
    print("\n🎉 All tasks completed successfully!")