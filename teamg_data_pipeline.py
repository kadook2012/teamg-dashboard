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
    print("🚀 Downloading TEAMG 5-year data...")
    df = yf.download("TEAMG.BK", period="5y", interval="1d")
    
    if df.empty: return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.columns = [col.lower() for col in df.columns]

    # --- Technical Analysis (V.11.1) ---
    print("📊 Calculating Technical & Stat Indicators...")
    df['ema_50'] = ta.ema(df['close'], length=50)
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    macd = ta.macd(df['close'])
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['macd_hist'] = macd['MACDh_12_26_9']
    
    stoch = ta.stoch(df['high'], df['low'], df['close'])
    df['stoch_k'] = stoch['STOCHk_14_3_3']
    df['stoch_d'] = stoch['STOCHd_14_3_3']
    
    # --- Statistics & Volume ---
    df['vol_ema20'] = ta.ema(df['volume'], length=20)
    df['rel_vol'] = df['volume'] / df['vol_ema20']
    df['z_score'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).std()

    # ✨ ป้องกัน Error: ใส่ค่า TEAMG ในคอลัมน์ symbol
    df['symbol'] = 'TEAMG'

    # ลบแถวที่ยังคำนวณ Indicator ไม่ได้ (เช่น 200 วันแรกของ EMA200)
    df = df.dropna()

    data_dict = df.to_dict(orient='records')
    for record in data_dict:
        record['date'] = record['date'].strftime('%Y-%m-%d')

    try:
        # อัปเดตเข้าตารางมาสเตอร์ตาม Bible
        supabase.table("teamg_master_analysis").upsert(data_dict).execute()
        print(f"✅ Successfully updated 'teamg_master_analysis' with {len(df)} rows!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    get_and_process_data()