import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
import requests
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def calculate_indicators(df):
    # RSI 14
    window = 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan) 
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # EMA 20
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # Volume Spike 200%
    df['vol_avg_5'] = df['volume'].shift(1).rolling(window=5).mean()
    df['vol_spike'] = (df['volume'] > (df['vol_avg_5'] * 2)) & (df['vol_avg_5'] > 0)
    return df

def get_stock_data(symbol="TEAMG.BK"):
    print(f"🚀 Fetching data for {symbol}...")
    # ดึงข้อมูลและจัดการ Multi-index ทันที
    df = yf.download(symbol, period="1y", interval="1d", auto_adjust=True)
    
    if df.empty or len(df) < 20:
        print(f"❌ No data found.")
        return None

    # แก้ปัญหา Multi-Index จาก yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # แปลงชื่อคอลัมน์เป็นตัวพิมพ์เล็กให้หมดก่อนคำนวณ
    df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns] # ทำซ้ำเพื่อความชัวร์หลัง reset_index

    # คำนวณค่าต่างๆ
    df = calculate_indicators(df)
    df = df.dropna(subset=['rsi_14'])
    
    # จัดฟอร์แมตข้อมูล
    df['vol_spike'] = df['vol_spike'].astype(int)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df['symbol'] = symbol
    
    # เลือกคอลัมน์ให้ตรงกับ Supabase (image_186dad.png)
    cols = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'rsi_14', 'ema_20', 'vol_spike']
    return df[cols].to_dict(orient='records')

def upload_to_supabase(data):
    if not data: return
    print(f"📤 Updating Supabase with {len(data)} rows...")
    try:
        supabase.table("stock_prices").upsert(data).execute()
        print("🎉 Success! Data updated.")
        
        last_day = data[-1]
        if last_day['vol_spike'] == 1:
            msg = f"🚀 <b>Volume Spike!</b>\nหุ้น: <code>{last_day['symbol']}</code>\nวันที่: {last_day['date']}\nปิด: {last_day['close']:.2f}\nVol: {last_day['volume']:,}"
            send_telegram_msg(msg)
    except Exception as e:
        print(f"❌ Upsert Error: {e}")

if __name__ == "__main__":
    stock_data = get_stock_data("TEAMG.BK")
    if stock_data:
        upload_to_supabase(stock_data)