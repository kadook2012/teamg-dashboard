import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_indicators(df):
    """คำนวณ RSI และ EMA ด้วย Pandas (ไม่ใช้ pandas-ta เพื่อความเสถียร)"""
    # คำนวณ RSI 14
    window = 14
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    # เลี่ยงการหารด้วย 0
    rs = gain / loss.replace(0, np.nan) 
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # คำนวณ EMA 20
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    return df

def get_stock_data(symbol="TEAMG.BK"):
    print(f"Fetching data for {symbol}...")
    stock = yf.Ticker(symbol)
    df = stock.history(period="1y") # ดึงข้อมูลย้อนหลัง 1 ปี
    
    if df.empty:
        print("No data found.")
        return None

    # จัดการ Index และคำนวณ Indicator
    df = df.reset_index()
    df = calculate_indicators(df)
    
    # ลบแถวที่คำนวณไม่ได้ (NaN) ออก
    df = df.dropna(subset=['RSI_14'])
    
    # เลือกเฉพาะคอลัมน์ที่จะใช้
    final_df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'RSI_14', 'EMA_20']].copy()
    final_df['Date'] = final_df['Date'].dt.strftime('%Y-%m-%d')
    final_df['Symbol'] = symbol
    
    return final_df.to_dict(orient='records')

def upload_to_supabase(data):
    if not data:
        return
    
    print(f"Uploading {len(data)} rows to Supabase...")
    try:
        # ใช้ upsert เพื่ออัปเดตข้อมูลเดิมหรือเพิ่มข้อมูลใหม่โดยอิงจาก Date และ Symbol
        response = supabase.table("stock_prices").upsert(data).execute()
        print("Upload successful!")
    except Exception as e:
        print(f"Error uploading to Supabase: {e}")

if __name__ == "__main__":