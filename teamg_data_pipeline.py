import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv

# 1. Setup Connection
load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def calculate_ai_pivots(df, window=5):
    """คำนวณจุดยอด (Pivot High) เพื่อติ๊กถูกในฐานข้อมูล"""
    df = df.copy()
    df['is_pivot_high'] = False
    for i in range(window, len(df) - window):
        current_high = df.iloc[i]['high']
        left_max = df.iloc[i-window:i]['high'].max()
        right_max = df.iloc[i+1:i+window+1]['high'].max()
        if current_high > left_max and current_high > right_max:
            df.at[df.index[i], 'is_pivot_high'] = True
    return df

def run_pipeline():
    print("🛰️ ดึงข้อมูล TEAMG.BK พร้อมคำนวณ Fundamental & AI Logic...")
    ticker = yf.Ticker("TEAMG.BK")
    info = ticker.info
    
    # Fundamental Data
    mkt_cap = info.get('marketCap')
    ev_ebitda = info.get('enterpriseToEbitda')
    h_52w = info.get('fiftyTwoWeekHigh')
    l_52w = info.get('fiftyTwoWeekLow')
    total_shares = info.get('sharesOutstanding')
    float_shares = info.get('floatShares')
    free_float_val = (float_shares / total_shares * 100) if float_shares and total_shares else None

    # ดึงข้อมูลย้อนหลัง 2 ปี (ครอบคลุมถึงปัจจุบันปี 2026)
    hist = ticker.history(period="2y")
    df = hist.reset_index()
    df.columns = [c.lower() for c in df.columns]
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    # คำนวณ AI Pivot
    df = calculate_ai_pivots(df)
    
    data_list = []
    for _, row in df.iterrows():
        data_list.append({
            "symbol": "TEAMG",
            "date": row['date'],
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close']),
            "volume": int(row['volume']),
            "market_cap": float(mkt_cap) if mkt_cap else None,
            "ev_ebitda": float(ev_ebitda) if ev_ebitda else None,
            "high_52week": float(h_52w) if h_52w else None,
            "low_52week": float(l_52w) if l_52w else None,
            "free_float_pct": float(free_float_val) if free_float_val else None,
            "is_pivot_high": bool(row['is_pivot_high'])
        })

    # ส่งข้อมูลเข้า Supabase
    supabase.table("teamg_master_analysis").upsert(data_list).execute()
    print(f"✅ สำเร็จ! อัปเดตข้อมูล {len(data_list)} แถวเรียบร้อย")

if __name__ == "__main__":
    run_pipeline()