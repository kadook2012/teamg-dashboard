import os
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
import schedule

# โหลด environment variables จาก .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: ไม่พบ SUPABASE_URL หรือ SUPABASE_KEY ในไฟล์ .env")
    print("กรุณาตรวจสอบไฟล์ .env ใน folder เดียวกัน")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# หุ้นที่ต้องการดึง (ใช้ตัวเดียวก่อนตามที่ขอ)
SYMBOL = "SECURE.BK"  # ถ้าต้องการเปลี่ยนหุ้น แก้บรรทัดนี้

def get_latest_date_in_db(symbol):
    """ดึงวันที่ล่าสุดที่มีในฐานข้อมูลสำหรับหุ้นตัวนี้"""
    try:
        response = supabase.table('stock_prices')\
            .select('date')\
            .eq('symbol', symbol.replace('.BK', ''))\
            .order('date', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data and len(response.data) > 0:
            latest_date = response.data[0]['date']
            print(f"วันที่ล่าสุดใน DB สำหรับ {symbol}: {latest_date}")
            return datetime.strptime(latest_date, '%Y-%m-%d')
        else:
            print(f"ไม่พบข้อมูลใน DB สำหรับ {symbol} → ดึงทั้งหมดครั้งแรก")
            return None
    except Exception as e:
        print(f"Error ดึงวันที่ล่าสุด: {e}")
        return None

def update_stock_data():
    """ฟังก์ชันหลักในการอัพเดตข้อมูลหุ้น"""
    print(f"\nเริ่มอัพเดตข้อมูล {SYMBOL.replace('.BK', '')} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    ticker = yf.Ticker(SYMBOL)

    # ดึงวันที่ล่าสุดจาก DB
    latest_db_date = get_latest_date_in_db(SYMBOL)

    if latest_db_date:
        # ดึงข้อมูลใหม่ตั้งแต่วันถัดไป
        start_date = (latest_db_date + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        print(f"ดึงข้อมูลใหม่ตั้งแต่ {start_date} ถึง {end_date}")
        df = ticker.history(start=start_date, end=end_date)
    else:
        # ครั้งแรก ดึงทั้งหมด
        print("ดึงข้อมูลย้อนหลังทั้งหมด (ครั้งแรก)")
        df = ticker.history(period="max")

    if df.empty:
        print(f"ไม่พบข้อมูลใหม่สำหรับ {SYMBOL}")
        return

    # เตรียมข้อมูล
    df = df.reset_index()
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    df['symbol'] = SYMBOL.replace('.BK', '')
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

    # ลบคอลัมน์ที่ไม่ต้องการ (ป้องกันหลุด id หรือ index)
    columns_to_drop = ['id', 'index', 'level_0']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')

    required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
    data_to_insert = df[required_columns].to_dict(orient='records')

    try:
        response = supabase.table('stock_prices').upsert(
            data_to_insert,
            on_conflict='symbol, date'
        ).execute()

        inserted = len(data_to_insert)
        print(f"บันทึก/อัพเดต {inserted} แถวสำเร็จ")
        
        # แสดงตัวอย่างข้อมูลล่าสุด
        print("\nข้อมูลล่าสุด 3 แถว:")
        print(df.tail(3))
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")

def run_scheduler():
    """ตั้งเวลาให้รันทุกวันตอน 17:30 น. (หลังตลาดปิด)"""
    # รันทันทีครั้งแรก
    update_stock_data()

    # ตั้งเวลา
    schedule.every().day.at("17:30").do(update_stock_data)
    
    print("Scheduler เริ่มทำงานแล้ว รอเวลา 17:30 ทุกวันเพื่ออัพเดตข้อมูล")

    while True:
        schedule.run_pending()
        time.sleep(60)  # เช็คทุก 1 นาที

if __name__ == "__main__":
    print(f"โปรแกรมอัพเดตข้อมูลหุ้น {SYMBOL.replace('.BK', '')} เริ่มต้น...")
    run_scheduler()