import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
import sys
import time

# --- 1. ตั้งค่าการเชื่อมต่อ ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("--- เชื่อมต่อ Supabase สำเร็จ ---")
except Exception as e:
    print(f"Error: {e}")
    sys.exit()

def safe_float(value):
    try:
        if pd.isna(value) or value == "" or str(value).strip() in ["-", "#N/A"]:
            return 0.0
        clean_val = str(value).replace(',', '').strip()
        return float(clean_val)
    except:
        return None

# --- 2. ดึงราคาประวัติศาสตร์ (จากอดีตใน CSV ทั้งหมด) ---
def get_historical_prices(file_path, stock_name):
    print(f"--- เริ่มประมวลผลข้อมูลราคาอดีตจากไฟล์ CSV ---")
    try:
        # อ่านไฟล์ทั้งหมดโดยไม่ระบุ Header
        df = pd.read_csv(file_path, header=None, low_memory=False)
        data_to_insert = []
        
        # วนลูปทุกแถวเพื่อดึงประวัติศาสตร์
        for i in range(len(df)):
            row = df.iloc[i]
            close_val = safe_float(row[342]) # Index 342 ตามที่คุณตรวจพบ
            
            # ถ้ามีราคาปิด ให้ถือว่าเป็นแถวข้อมูล
            if close_val is not None and close_val > 0:
                data_to_insert.append({
                    "stock_symbol": stock_name,
                    "date": str(row[338]) if pd.notnull(row[338]) else None,
                    "open_price": safe_float(row[339]) or 0.0,
                    "high_price": safe_float(row[340]) or 0.0,
                    "low_price": safe_float(row[341]) or 0.0,
                    "close_price": close_val,
                    "volume": int(safe_float(row[343])) if safe_float(row[343]) else 0,
                    "eps": safe_float(row[69]) # EPSเฉลี่ย
                })
        return data_to_insert
    except Exception as e:
        print(f"Error reading historical CSV: {e}")
        return []

# --- 3. Scrape ข่าว (จากปัจจุบัน ย้อนกลับไปหลายหน้า) ---
def scrape_news_to_past(stock_name, pages=5):
    print(f"--- เริ่มดึงข่าวปัจจุบันย้อนหลัง {pages} หน้า ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    all_news = []
    
    for page in range(1, pages + 1):
        # เว็บส่วนใหญ่ใช้โครงสร้าง /page/x สำหรับหน้าถัดไป
        url = f"https://www.kaohoon.com/tag/{stock_name.lower()}/page/{page}"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                break # หยุดถ้าไม่พบหน้าถัดไป
                
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.find_all('article')
            
            if not articles: break
            
            for art in articles:
                h3 = art.find('h3')
                if h3 and h3.find('a'):
                    a_tag = h3.find('a')
                    headline = a_tag.get_text(strip=True)
                    if len(headline) > 15:
                        all_news.append({
                            "stock_symbol": stock_name,
                            "headline": headline,
                            "link": a_tag['href'] if a_tag['href'].startswith('http') else f"https://www.kaohoon.com{a_tag['href']}",
                            "source": "Kaohoon"
                        })
            print(f"เก็บข้อมูลข่าวหน้า {page} สำเร็จ...")
            time.sleep(1) # นอน 1 วินาทีเพื่อไม่ให้เซิร์ฟเวอร์บล็อก
        except Exception as e:
            print(f"Error page {page}: {e}")
            break
            
    return all_news

# --- 4. Main 실행 ---
def main():
    stock = "TEAMG"
    file = "EPS16YEAR12.csv"

    # 1. จัดการราคา (อดีตจากไฟล์)
    historical_prices = get_historical_prices(file, stock)
    if historical_prices:
        print(f"พบข้อมูลประวัติศาสตร์ {len(historical_prices)} รายการ กำลังอัปโหลด...")
        # แบ่งส่งครั้งละ 200 แถวเพื่อความเสถียร
        for i in range(0, len(historical_prices), 200):
            batch = historical_prices[i:i+200]
            supabase.table("excel_stock_prices").insert(batch).execute()
        print("SUCCESS: ข้อมูลราคาอดีตเข้าสู่ระบบแล้ว")

    # 2. จัดการข่าว (ปัจจุบันย้อนหลังไป 5 หน้า)
    news_to_present = scrape_news_to_past(stock, pages=5)
    if news_to_present:
        try:
            supabase.table("excel_stock_news").insert(news_to_present).execute()
            print(f"SUCCESS: ข้อมูลข่าวประวัติศาสตร์และปัจจุบันเข้าสู่ระบบแล้ว {len(news_to_present)} หัวข้อ")
        except Exception as e:
            print(f"Error Insert News: {e}")

if __name__ == "__main__":
    main()