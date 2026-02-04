import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

STOCKS = ["TEAMG.BK"]

def calculate_technical(df):
    # EMA & RSI
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
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

    # Z-Score: ใช้ min_periods=1 เพื่อให้คำนวณได้แม้ข้อมูลช่วงแรกไม่ครบ
    rolling_mean = df['close'].rolling(window=20, min_periods=1).mean()
    rolling_std = df['close'].rolling(window=20, min_periods=1).std()
    df['z_score'] = (df['close'] - rolling_mean) / rolling_std
    
    # เติมค่า 0 ในจุดที่ยังเป็น NaN หรือ Inf
    df['z_score'] = df['z_score'].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df

def run_pipeline():
    for symbol in STOCKS:
        print(f"🚀 Processing {symbol}...")
        ticker = yf.Ticker(symbol)
        
        # 1. Update Info Table
        info = ticker.info
        info_data = {
            "symbol": symbol,
            "company_name": info.get("longName"),
            "market_cap": info.get("marketCap"),
            "roe": info.get("returnOnEquity"),
            "net_margin": info.get("profitMargins")
        }
        supabase.table("teamg_master_info").upsert(info_data).execute()

        # 2. Update Analysis Table (ดึง 2 ปีเพื่อให้คำนวณแม่นยำ)
        df = yf.download(symbol, period="2y", interval="1d", auto_adjust=True)
        if df.empty: continue
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]

        df = calculate_technical(df)
        df['symbol'] = symbol
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        records = df.replace({np.nan: None}).to_dict(orient='records')
        supabase.table("teamg_master_analysis").upsert(records).execute()
        print(f"✅ {symbol} updated!")

if __name__ == "__main__":
    run_pipeline()