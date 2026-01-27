import os
import re
import time
from datetime import datetime
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from supabase import create_client, Client

# โหลด environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLE_NAME = "news_set"

# ====================== Selenium Setup ======================
options = Options()
# options.add_argument("--headless=new")  # comment ออกเพื่อดูหน้า browser ถ้าต้องการ debug
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20)

driver.get("https://www.set.or.th/th/market/news-and-alert/news")

# จัดการ Cookie ถ้ามี
try:
    accept_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='accept'], button[id*='cookie'], button[contains(., 'ยอมรับ')]"))
    )
    accept_btn.click()
    print("✓ ยอมรับ cookie แล้ว")
except:
    print("ไม่มี cookie modal หรือกดไม่ได้")

time.sleep(3)  # รอหน้าโหลด JS

# ====================== ฟังก์ชัน scrape หน้าเดียว ======================
def scrape_page(page_num: int):
    try:
        # รอ container หลัก
        wait.until(EC.presence_of_element_located((By.ID, "news-alert-tab-news")))
        time.sleep(2)  # รอเนื้อหาเพิ่มเติม

        # หา group ข่าวทั้งหมด
        groups = driver.find_elements(By.CSS_SELECTOR, "#news-alert-tab-news div.group-news.mb-4")

        print(f"หน้า {page_num}: พบกลุ่มข่าว {len(groups)} กลุ่ม")

        inserted = 0
        for group_idx, group in enumerate(groups, 1):
            # หาข่าวย่อยใน group นี้ (ใช้ div ที่มี class d-flex หรือ new-alert-wrapper)
            items = group.find_elements(By.CSS_SELECTOR,
                "div.d-flex, div.d-none.d-md-flex.new-alert-wrapper, div.new-alert-wrapper, div[class*='alert-wrapper']")

            for item_idx, item in enumerate(items, 1):
                try:
                    # วันที่/เวลา
                    date_elem = item.find_element(By.CSS_SELECTOR, "div.date-time, .date-time, span.date-time")
                    date_time = date_elem.text.strip() if date_elem else "N/A"

                    # ชื่อหุ้น / หลักทรัพย์
                    symbol_elem = item.find_element(By.CSS_SELECTOR, "div.securities, .securities, span.securities")
                    symbol = symbol_elem.text.strip() if symbol_elem else "N/A"

                    # หัวข้อข่าว + ลิงก์
                    title_elem = item.find_element(By.CSS_SELECTOR, "div.news-col a, a, div.col-lg-8 a, div.col-md-6 a")
                    title = title_elem.text.strip()
                    url = title_elem.get_attribute("href") or ""

                    if not url or len(title) < 15:
                        continue  # ข้ามถ้าไม่มีลิงก์หรือหัวข้อสั้นเกิน

                    data = {
                        "date_time": date_time,
                        "symbol": symbol,
                        "title": title,
                        "url": url,
                        "source": "SET",
                        "scraped_at": datetime.utcnow().isoformat()
                    }

                    # Upsert ลง Supabase (ใช้ url เป็น key หลัก)
                    response = supabase.table(TABLE_NAME).upsert(data, on_conflict="url").execute()

                    if len(response.data) > 0:
                        inserted += 1
                        print(f"  ✓ {symbol:<8} | {date_time:<20} | {title[:60]}... | {url[:70]}...")

                except Exception as inner_e:
                    continue  # ข้าม item นี้ถ้า error

        print(f"หน้า {page_num}: บันทึกสำเร็จ {inserted} รายการ")
        return inserted

    except Exception as e:
        print(f"หน้า {page_num} Error: {str(e)[:150]}")
        return 0

# ====================== Pagination Loop ======================
page = 1
max_pages = 5  # ปรับได้ หรือตั้ง None เพื่อ scrape ทุกหน้า
total_inserted = 0

while True:
    print(f"\n================ หน้า {page} ================")
    inserted = scrape_page(page)
    total_inserted += inserted

    if inserted == 0 and page > 1:
        print("ไม่พบข้อมูลเพิ่มเติม → จบการ scrape")
        break

    try:
        # ปุ่มถัดไป (ลองหลาย pattern)
        next_btn = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "button[aria-label='ถัดไป'], button.next, .ant-pagination-next button, "
            "button[class*='next'], li.next button, [aria-label*='next']"
        )))

        if "disabled" in (next_btn.get_attribute("class") or "") or next_btn.get_attribute("disabled"):
            print("ปุ่มถัดไปถูก disable แล้ว → จบ")
            break

        next_btn.click()
        time.sleep(4)  # รอหน้าใหม่โหลด
        page += 1

        if max_pages is not None and page > max_pages:
            print(f"ถึงจำนวนหน้าสูงสุดที่กำหนด ({max_pages})")
            break

    except Exception as pag_e:
        print(f"ไม่พบปุ่มถัดไปหรือ timeout → จบ ({str(pag_e)[:80]})")
        break

driver.quit()

print("\n================ เสร็จสิ้น ================")
print(f"รวมบันทึกทั้งหมด: {total_inserted} รายการ")