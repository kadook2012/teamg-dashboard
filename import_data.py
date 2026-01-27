import pandas as pd
import os
import re
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# โหลดค่า Config จากไฟล์ .env
load_dotenv()

# --- การตั้งค่า ---
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
EXCEL_FILE_PATH: str = "holder_data.xlsx"
TABLE_NAME: str = "stock_holders"

# คำที่ใช้ตรวจสอบว่าเป็นแถวข้อมูลเมตาหรือไม่
METADATA_KEYWORDS = [
    'จำนวนผู้ถือหุ้นรายย่อย (Free float):',
    '%การถือหุ้นของผู้ถือหุ้นรายย่อย (%Free Float):',
    'วันที่ขึ้น:',
    '%การถือหุ้นแบบไร้ใบหุ้น:',
    'ผู้ถือหุ้นรายย่อย ณ วันที่:',
    'จำนวนผู้ถือหุ้นทั้งหมด:'
]

def clean_general_value(value):
    """ฟังก์ชันสำหรับแปลงค่า NaN จาก pandas ให้เป็น None สำหรับข้อมูลทั่วไป"""
    if pd.isna(value):
        return None
    return value

def clean_numeric_value(value):
    """ฟังก์ชันสำหรับทำความสะอาดค่าและแปลงเป็น float (สำหรับ %, ราคา, P/E)"""
    if pd.isna(value) or value == '*' or value == '-':
        return None
    if isinstance(value, str):
        value = value.replace(',', '').replace('%', '').strip()
        if not value:
            return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def clean_integer_value(value):
    """ฟังก์ชันสำหรับทำความสะอาดค่าและแปลงเป็น integer (สำหรับจำนวนหุ้น, จำนวนผู้ถือหุ้น)"""
    if pd.isna(value) or value == '*' or value == '-':
        return None
    if isinstance(value, str):
        value = value.replace(',', '').strip()
        if not value:
            return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def parse_date(date_input):
    """ฟังก์ชันสำหรับแปลงวันที่ในรูปแบบต่างๆ"""
    if pd.isna(date_input) or date_input == '-' or date_input == '*':
        return None

    if isinstance(date_input, (datetime, pd.Timestamp)):
        return date_input.date().isoformat()

    date_str = str(date_input)
    
    if 'XD' in date_str:
        date_str = date_str.split('XD')[-1].strip()
    
    try:
        return datetime.strptime(date_str, '%A, %B %d, %Y').date().isoformat()
    except ValueError:
        pass
    
    try:
        return datetime.strptime(date_str, '%Y/%m/%d').date().isoformat()
    except ValueError:
        pass
    
    return None

def main():
    """ฟังก์ชันหลัก (Final Correct Version)"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: กรุณาตั้งค่า SUPABASE_URL และ SUPABASE_KEY ในไฟล์ .env")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("เชื่อมต่อ Supabase สำเร็จ")

    try:
        df = pd.read_excel(EXCEL_FILE_PATH, sheet_name="holder")
        print(f"อ่านไฟล์ Excel สำเร็จ: {EXCEL_FILE_PATH}")
    except FileNotFoundError:
        print(f"Error: ไม่พบไฟล์ {EXCEL_FILE_PATH}")
        return

    final_records = []
    df = df.dropna(subset=['SYMBOL'])

    for symbol, group in df.groupby('SYMBOL'):
        print(f"กำลังประมวลผลข้อมูลสำหรับหุ้น: {symbol}")
        
        metadata = {}
        shareholder_rows = []

        for index, row in group.iterrows():
            shareholder_name = str(row['ผู้ถือหุ้นรายใหญ่'])
            is_metadata_row = any(keyword in shareholder_name for keyword in METADATA_KEYWORDS)
            
            if is_metadata_row:
                key = shareholder_name
                if 'จำนวนผู้ถือหุ้นรายย่อย' in key:
                    metadata['free_float_count'] = clean_integer_value(row['จำนวนหุ้น'])
                elif '%การถือหุ้นของผู้ถือหุ้นรายย่อย' in key:
                    metadata['free_float_percentage'] = clean_numeric_value(row['%'])
                elif 'วันที่ขึ้น:' in key:
                    metadata['xd_date'] = parse_date(row['%Free'])
                elif '%การถือหุ้นแบบไร้ใบหุ้น:' in key:
                    metadata['non_cert_share_percent'] = clean_numeric_value(row['%'])
                elif 'ผู้ถือหุ้นรายย่อย ณ วันที่:' in key:
                    metadata['minor_shareholder_date'] = parse_date(row['จำนวนหุ้น'])
                elif 'จำนวนผู้ถือหุ้นทั้งหมด:' in key:
                    metadata['total_shareholders'] = clean_integer_value(row['จำนวนหุ้น'])
            else:
                # *** แก้ไขตรงนี้: ถ้าไม่ใช่แถวเมตา ให้เพิ่มเข้าไปเลย ไม่ต้องตรวจสอบอะไรเพิ่ม ***
                shareholder_rows.append(row)

        common_data = {
            'symbol': clean_general_value(symbol),
            'closing_date': parse_date(group['วันปิดสมุด'].iloc[0]),
            'free_float_percent_header': clean_numeric_value(group['%Free'].iloc[0]),
            'price': clean_numeric_value(group['ราคา'].iloc[0]),
            'pe_ratio': clean_numeric_value(group['P/E'].iloc[0]),
            'sector': clean_general_value(group['หมวด'].iloc[0]),
        }
        common_data.update(metadata)

        for row in shareholder_rows:
            record = common_data.copy()
            record.update({
                'shareholder_name': clean_general_value(row['ผู้ถือหุ้นรายใหญ่']),
                'share_count': clean_integer_value(row['จำนวนหุ้น']),
                'share_percent': clean_numeric_value(row['%']),
            })
            final_records.append(record)

    print(f"ประมวลผลข้อมูลทั้งหมดสำเร็จ {len(final_records)} รายการ")

    if final_records:
        print("กำลังนำเข้าข้อมูลลง Supabase...")
        try:
            for i in range(0, len(final_records), 100):
                batch = final_records[i:i+100]
                result = supabase.table(TABLE_NAME).insert(batch).execute()
                print(f"นำเข้าข้อมูลสำเร็จช่วงที่ {i//100 + 1} ({len(batch)} รายการ)")
            print("นำเข้าข้อมูลลง Supabase สำเร็จทั้งหมด!")
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการนำเข้าข้อมูล: {e}")

if __name__ == "__main__":
    main()