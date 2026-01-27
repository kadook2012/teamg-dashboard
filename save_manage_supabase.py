import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# โหลด environment variables
load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("กรุณาตั้งค่า SUPABASE_URL และ SUPABASE_KEY ใน .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# URL ของหน้า รายงานแบบ 59
BASE_URL = "https://market.sec.or.th/public/idisc/th/r59"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
}

def scrape_form59_data(company=None, date_from=None, date_to=None):
    """
    Scrape ข้อมูลจากหน้าเว็บ
    - ถ้าไม่ใส่เงื่อนไข = ดึงข้อมูล default (ล่าสุด)
    - ถ้าต้องการค้นหา ต้องใช้ selenium เพราะเว็บใช้ JS submit
    """
    params = {}
    if company:
        params["company"] = company
    if date_from:
        params["dateFrom"] = date_from  # format YYYY-MM-DD
    if date_to:
        params["dateTo"] = date_to

    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # หาตาราง (จากโครงสร้างที่พบ = class="result-table")
    table = soup.find("table", class_="result-table")
    if not table:
        print("ไม่พบตารางผลลัพธ์ อาจถูก block หรือโครงสร้างเว็บเปลี่ยน")
        print(soup.prettify()[:800])  # debug
        return []

    # ดึง header
    headers = [th.get_text(strip=True) for th in table.select("thead tr th")]

    # ดึงข้อมูล rows
    data = []
    rows = table.select("tbody tr")
    for row in rows:
        cols = row.select("td")
        if len(cols) < 8:
            continue

        row_data = [col.get_text(strip=True) for col in cols[:8]]

        # ดึงลิงก์หมายเหตุ (คอลัมน์สุดท้าย)
        remark_link = ""
        a_tag = cols[-1].find("a")
        if a_tag and "href" in a_tag.attrs:
            remark_link = "https://market.sec.or.th" + a_tag["href"] if a_tag["href"].startswith("/") else a_tag["href"]

        row_data.append(remark_link)
        data.append(row_data)

    # สร้าง DataFrame
    columns = headers + ["หมายเหตุ_URL"]
    df = pd.DataFrame(data, columns=columns)

    return df


def insert_to_supabase(df):
    """ Insert ข้อมูลจาก DataFrame ไปยัง Supabase (แบบ bulk) """
    if df.empty:
        print("ไม่มีข้อมูลให้ insert")
        return

    # แปลงชื่อ column ให้ตรงกับตาราง (snake_case)
    rename_map = {
        "ชื่อบริษัท": "company_name",
        "ชื่อผู้บริหาร": "executive_name",
        "ความสัมพันธ์ *": "relationship",
        "ประเภทหลักทรัพย์": "security_type",
        "วันที่ได้มา/จำหน่าย": "transaction_date",
        "จำนวน": "quantity",
        "ราคา": "price",
        "วิธีการได้มา/จำหน่าย": "method",
        "หมายเหตุ_URL": "remark_url",
    }

    df = df.rename(columns=rename_map)

    # แปลงเป็น list of dicts
    records = df.to_dict(orient="records")

    try:
        # Insert แบบ bulk (supabase รองรับ list ได้)
        response = (
            supabase.table("form_59_reports")
            .insert(records)
            .execute()
        )

        print(f"Insert สำเร็จ {len(response.data)} รายการ")
        print(f"ตัวอย่าง record แรก: {response.data[0] if response.data else 'ไม่มี'}")

    except Exception as e:
        print(f"Error insert to Supabase: {e}")
        print("ตัวอย่าง record แรกที่ error:", records[0] if records else "ไม่มีข้อมูล")


# ----------------- ตัวอย่างการใช้งาน -----------------

if __name__ == "__main__":
    print(f"เริ่ม scrape Form 59 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ตัวอย่าง 1: ดึงข้อมูล default (วันล่าสุด)
    df_default = scrape_form59_data()
    if not df_default.empty:
        print(f"พบ {len(df_default)} รายการ")
        print(df_default.head(3))
        insert_to_supabase(df_default)

    # ตัวอย่าง 2: ค้นหาเฉพาะบริษัท + ช่วงวันที่ (อาจต้องใช้ selenium ถ้าไม่ทำงาน)
    # df_search = scrape_form59_data(
    #     company="เกียรตินาคินภัทร",
    #     date_from="2026-01-01",
    #     date_to="2026-01-22"
    # )
    # insert_to_supabase(df_search)

    print("เสร็จสิ้น")