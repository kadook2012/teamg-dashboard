import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv

# --- 1. การตั้งค่าเบื้องต้น ---
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# รายชื่อหุ้นที่ต้องการดึงข้อมูล
STOCKS = ["TEAMG.BK"] 

def get_and_upsert_info(symbol):
    """ดึงข้อมูลพื้นฐาน (ROE, ROA, Sector) เข้าตาราง teamg_master_info"""
    print(f"📊 กำลังดึงข้อมูลพื้นฐานสำหรับ {symbol}...")
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
        
        # จัดการค่าว่างและส่งขึ้น Supabase
        info_cleaned = {k: (v if pd.notnull(v) else None) for k, v in info_data.items()}
        supabase.table("teamg_master_info").upsert(info_cleaned).execute()
        print(f"✅ อัปเดตข้อมูลพื้นฐาน {symbol} สำเร็จ")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ข้อมูลพื้นฐาน {symbol}: {e}")

def calculate_technical(df):
    """คำนวณ Technical Indicators และแก้ปัญหาค่า NULL ในวันล่าสุด"""
    # 1. EMA
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # 2. RSI
    window = 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))
    
    # 3. MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 4. Z-Score (คำนวณจากค่าเฉลี่ย 20 วัน)
    # เราใช้ .fillna(method='ffill') หรือเติม 0 เพื่อป้องกัน NULL ในวันล่าสุด
    rolling_mean = df['close'].rolling(window=20).mean()
    rolling_std = df['close'].rolling(window=20).std()
    df['z_score'] = (df['close'] - rolling_mean) / rolling_std
    
    # เติมค่าที่หายไป (ถ้ามี) ด้วยค่าก่อนหน้า หรือ 0
    df['z_score'] = df['z_score'].ffill().fillna(0)
    
    return df

def get_and_upsert_analysis(symbol):
    """ดึงข้อมูลราคาและคำนวณทางเทคนิคเข้าตาราง teamg_master_analysis"""
    print(f"🚀 กำลังดึงราคาและวิเคราะห์เทคนิคัลสำหรับ {symbol}...")
    try:
        # ดึงข้อมูลย้อนหลัง 2 ปี เพื่อให้มีข้อมูลพอคำนวณ EMA200 และ Z-Score
        df = yf.download(symbol, period="2y", interval="1d", auto_adjust=True)
        if df.empty: return

        # จัดการโครงสร้าง DataFrame ให้เป็นระเบียบ
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]

        # คำนวณค่าทางเทคนิค
        df = calculate_technical(df)
        df['symbol'] = symbol
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # แปลงค่าที่เป็น Infinity หรือ NaN ให้เป็น None เพื่อให้ Database รับได้
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        
        # แปลงข้อมูลเป็นรูปแบบที่จะส่งขึ้น Supabase
        records = df.to_dict(orient='records')
        
        # ส่งข้อมูลทั้งหมดขึ้นไป Upsert
        supabase.table("teamg_master_analysis").upsert(records).execute()
        print(f"✅ อัปเดตราคาและเทคนิคัล {symbol} ({len(records)} แถว) สำเร็จ")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ข้อมูลเทคนิคัล {symbol}: {e}")

# --- 2. เริ่มการทำงาน ---
if __name__ == "__main__":
    for s in STOCKS:
        print(f"\n--- เริ่มต้นจัดการหุ้น: {s} ---")
        get_and_upsert_info(s)      # อัปเดตพื้นฐาน
        get_and_upsert_analysis(s)  # อัปเดตราคา/เทคนิค
        
    print("\n🎉 ดึงข้อมูลและอัปเดตเรียบร้อยแล้ว!")