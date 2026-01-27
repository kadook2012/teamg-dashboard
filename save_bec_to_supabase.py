import os
from datetime import datetime
import yfinance as yf
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# โหลด environment variables จากไฟล์ .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: ไม่พบ SUPABASE_URL หรือ SUPABASE_KEY ในไฟล์ .env")
    print("กรุณาตรวจสอบไฟล์ .env ใน folder เดียวกัน")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# รายชื่อหุ้น SET50 (อัพเดตตามช่วงเวลาปัจจุบัน ธันวาคม 2025 - มิถุนายน 2026)
# สามารถอัพเดตจาก https://www.set.or.th/th/market/index/set50/overview
set50_symbols = [
    "AOT.BK", "ADVANC.BK", "BANPU.BK", "BBL.BK", "BCP.BK", "BDMS.BK", "BEM.BK",
    "BGRIM.BK", "BTS.BK", "CBG.BK", "CPALL.BK", "CPF.BK", "CPN.BK", "DELTA.BK",
    "EA.BK", "EGCO.BK", "GLOBAL.BK", "GPSC.BK", "GULF.BK", "HMPRO.BK", "INTUCH.BK",
    "IRPC.BK", "IVL.BK", "KBANK.BK", "KCE.BK", "KTB.BK", "KTC.BK", "MINT.BK",
    "MTC.BK", "OR.BK", "OSP.BK", "PTT.BK", "PTTEP.BK", "PTTGC.BK", "SAWAD.BK",
    "SCB.BK", "SCC.BK", "SCGP.BK", "TISCO.BK", "TMB.BK", "TOP.BK", "TRUE.BK",
    "TTA.BK", "TU.BK", "VGI.BK", "WHA.BK", "AMATA.BK", "BCH.BK", "CRC.BK", "JMT.BK"
]

print(f"กำลังดึงข้อมูลหุ้นทั้ง {len(set50_symbols)} ตัวจาก SET50...")

total_rows = 0
successful_symbols = 0

for symbol in set50_symbols:
    ticker = yf.Ticker(symbol)
    print(f"กำลังดึงข้อมูล {symbol.replace('.BK', '')}...")

    try:
        df = ticker.history(period="5d")
        if df.empty:
            print(f"ไม่พบข้อมูลสำหรับ {symbol}")
            continue

        # เตรียมข้อมูล
        df = df.reset_index()
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df['symbol'] = symbol.replace('.BK', '')
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        # ลบคอลัมน์ที่ไม่ต้องการ (ป้องกันหลุด id หรือ index)
        columns_to_drop = ['id', 'index', 'level_0']
        df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')

        # เลือกเฉพาะคอลัมน์ที่ส่ง
        required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        data_to_insert = df[required_columns].to_dict(orient='records')

        # upsert ข้อมูล
        response = supabase.table('stock_prices').upsert(
            data_to_insert,
            on_conflict='symbol, date'
        ).execute()

        inserted = len(data_to_insert)
        total_rows += inserted
        successful_symbols += 1
        print(f"บันทึก {inserted} แถวสำหรับ {symbol.replace('.BK', '')} สำเร็จ")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดสำหรับ {symbol}: {e}")

print(f"\nสรุปการทำงาน:")
print(f"- ดึงข้อมูลสำเร็จทั้งหมด {successful_symbols} / {len(set50_symbols)} ตัว")
print(f"- บันทึกข้อมูลรวมทั้งสิ้น {total_rows} แถว")
print(f"- เสร็จสิ้นเวลา {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

input("\nกด Enter เพื่อปิดหน้าต่าง...")