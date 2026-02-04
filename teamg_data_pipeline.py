import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
import requests
from dotenv import load_dotenv

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
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan) 
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # EMA 20
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # Volume Spike 200% (เทียบค่าเฉลี่ย 5 วันย้อนหลัง)
    df['Vol_Avg_5'] = df['Volume'].shift(1).rolling(window=5).mean()
    df['Vol_Spike'] = (df['Volume'] > (df['Vol_Avg_5'] * 2)) & (df['Vol_Avg_5'] > 0)
    return df

def get_stock_data(symbol="TEAMG.BK"):
    print(f"Fetching data for {symbol}...")
    stock = yf.Ticker(symbol)
    # ใช้ period="1mo" ก็พอสำหรับการอัปเดตรายวัน จะได้ไม่หนัก Database
    df = stock.history(period="1mo") 
    
    if df.empty:
        print("No data found.")
        return None

    df = df.reset_index()
    df = calculate_indicators(df)
    df = df.dropna(subset=['RSI_14'])
    
    # จัดรูปแบบข้อมูล
    df['Vol_Spike'] = df['Vol_Spike'].astype(int) 
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    df['Symbol'] = symbol
    
    # เลือกคอลัมน์ให้ตรงกับ Table ใน Supabase
    final_df = df[['Date', 'Symbol', 'Open', 'High', 'Low', 'Close', 'Volume', 'RSI_14', 'EMA_20', 'Vol_Spike']]
    return final_df.to_dict(orient='records')

def upload_to_supabase(data):
    if not data: return
    print(f"Updating Supabase with {len(data)} rows...")
    try:
        # มั่นใจว่าใน Supabase ตั้ง Date เป็น Primary Key
        supabase.table("stock_prices").upsert(data).execute()
        print("Success!")
        
        # ส่งแจ้งเตือนถ้าวันล่าสุดมี Volume Spike
        last_day = data[-1]
        if last_day['Vol_Spike'] == 1:
            msg = f"🚀 <b>Volume Spike: {last_day['Symbol']}</b>\n📅 {last_day['Date']}\n💰 ปิด: {last_day['Close']}\n📊 Vol: {last_day['Volume']:,}"
            send_telegram_msg(msg)
            
    except Exception as e:
        print(f"Upsert Error: {e}")

if __name__ == "__main__":
    stock_data = get_stock_data("TEAMG.BK")
    if stock_data:
        upload_to_supabase(stock_data)