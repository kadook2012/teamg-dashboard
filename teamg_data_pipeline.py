import yfinance as yf
import pandas as pd
import pandas_ta as ta
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def get_and_process_data():
    print("🚀 Downloading TEAMG 5Y Data...")
    # ดึงข้อมูล 5 ปี
    df = yf.download("TEAMG.BK", period="5y", interval="1d")
    
    if df.empty: 
        print("❌ No data found")
        return

    # ✨ แก้ไขจุดที่เกิด Error: จัดการ Multi-Index Columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.reset_index()
    # ตอนนี้คอลัมน์จะเป็นข้อความธรรมดาแล้ว สามารถใช้ .lower() ได้
    df.columns = [str(col).lower() for col in df.columns]

    print("📊 Calculating Indicators & AI Pivots...")
    # --- Technical Indicators ---
    df['ema_50'] = ta.ema(df['close'], length=50)
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    macd = ta.macd(df['close'])
    # ปรับชื่อคอลัมน์ MACD ให้แน่นอน
    df['macd'] = macd.iloc[:, 0] 
    df['macd_signal'] = macd.iloc[:, 1]
    df['macd_hist'] = macd.iloc[:, 2]
    
    # --- AI Pivot Logic (คำนวณใหม่ย้อนหลัง 5 ปี) ---
    df['is_pivot_high'] = False
    for i in range(2, len(df) - 2):
        if df['high'].iloc[i] > df['high'].iloc[i-1] and \
           df['high'].iloc[i] > df['high'].iloc[i-2] and \
           df['high'].iloc[i] > df['high'].iloc[i+1] and \
           df['high'].iloc[i] > df['high'].iloc[i+2]:
            df.at[i, 'is_pivot_high'] = True

    # --- Statistics ---
    df['vol_ema20'] = ta.ema(df['volume'], length=20)
    df['rel_vol'] = df['volume'] / df['vol_ema20']
    df['z_score'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).std()
    df['symbol'] = 'TEAMG'

    # ลบแถวที่มีค่า NaN (ช่วงเริ่มคำนวณ)
    df = df.dropna()
    
    # เตรียมข้อมูลส่งเข้า Supabase
    data_dict = df.to_dict(orient='records')
    for record in data_dict:
        record['date'] = record['date'].strftime('%Y-%m-%d')

    try:
        supabase.table("teamg_master_analysis").upsert(data_dict).execute()
        print(f"✅ SUCCESS: Updated {len(df)} rows (ถึงวันที่ {df['date'].iloc[-1]})")
    except Exception as e:
        print(f"❌ Supabase Error: {e}")

if __name__ == "__main__":
    get_and_process_data()