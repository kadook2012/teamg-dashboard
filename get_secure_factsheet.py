import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: ไม่พบ SUPABASE_URL หรือ SUPABASE_KEY ใน .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def scrape_secure_factsheet():
    url = "https://www.set.or.th/th/market/product/stock/quote/secure/factsheet"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error ดึงหน้าเว็บ: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    facts = {}
    facts['symbol'] = 'SECURE'

    # ชื่อบริษัท (ค้นหาจาก h1 หรือ div ที่มีชื่อบริษัท)
    company_name = soup.find('h1') or soup.find('div', class_='company-name') or soup.find('h2')
    facts['name_th'] = company_name.text.strip() if company_name else 'ไม่พบ'

    # ชื่ออังกฤษ (มักอยู่ใต้ชื่อไทย)
    name_en = soup.find('h2') or soup.find(string=lambda t: t and 'English' in t)
    facts['name_en'] = name_en.text.strip() if name_en else 'ไม่พบ'

    # ข้อมูลจาก table หรือ div factsheet
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                key = cells[0].text.strip()
                value = cells[1].text.strip()
                if 'กลุ่มอุตสาหกรรม' in key:
                    facts['sector'] = value
                elif 'อุตสาหกรรม' in key:
                    facts['industry'] = value
                elif 'มูลค่าหลักทรัพย์' in key or 'Market Cap' in key:
                    # แปลง 'xx,xxx.xx ล้านบาท' เป็นตัวเลข
                    value_clean = value.replace(',', '').replace(' ล้านบาท', '').replace(' Million Baht', '')
                    try:
                        facts['market_cap'] = float(value_clean)
                    except:
                        facts['market_cap'] = None
                elif 'ลักษณะธุรกิจ' in key or 'Business Description' in key:
                    facts['business_type'] = value

    # ลักษณะธุรกิจ (ถ้าอยู่ใน div แยก)
    business_div = soup.find('div', class_='business-description') or soup.find('p', class_='company-desc')
    if business_div:
        facts['business_type'] = business_div.text.strip()

    # เว็บไซต์
    website = soup.find('a', href=lambda h: h and 'http' in h and 'www.' in h)
    facts['website'] = website['href'] if website else 'ไม่พบ'

    # ปีก่อตั้ง (ค้นหาข้อความที่มี "ก่อตั้ง")
    founded = soup.find(string=lambda t: t and 'ก่อตั้ง' in t)
    if founded:
        try:
            facts['founded_year'] = int(founded.find_next(string=True).strip())
        except:
            facts['founded_year'] = None

    print("ข้อมูล Factsheet ที่ scrape ได้:")
    print(facts)

    return facts

def upsert_to_supabase(facts):
    if not facts:
        return

    try:
        response = supabase.table('companies').upsert(
            facts,
            on_conflict='symbol'
        ).execute()
        print("อัพเดตข้อมูลบริษัท SECURE สำเร็จใน Supabase!")
    except Exception as e:
        print(f"Error upsert ไป Supabase: {e}")

if __name__ == "__main__":
    facts = scrape_secure_factsheet()
    if facts:
        upsert_to_supabase(facts)

        df = pd.DataFrame(list(facts.items()), columns=['รายการ', 'ข้อมูล'])
        df.to_csv('secure_factsheet.csv', index=False, encoding='utf-8-sig')
        print("บันทึกไฟล์ secure_factsheet.csv สำเร็จ!")