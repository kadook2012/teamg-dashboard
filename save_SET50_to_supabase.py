import os
import time
import feedparser
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import schedule

# โหลด .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: ไม่พบ SUPABASE_URL หรือ SUPABASE_KEY ใน .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# รายชื่อหุ้น SET50 (50 ตัวตามดัชนีล่าสุด)
SET50_SYMBOLS = [
    "AOT", "ADVANC", "BANPU", "BBL", "BCP", "BDMS", "BEM", "BGRIM", "BTS", "CBG",
    "CPALL", "CPF", "CPN", "DELTA", "EA", "EGCO", "GLOBAL", "GPSC", "GULF", "HMPRO",
    "INTUCH", "IRPC", "IVL", "KBANK", "KCE", "KTB", "KTC", "MINT", "MTC", "OR",
    "OSP", "PTT", "PTTEP", "PTTGC", "SAWAD", "SCB", "SCC", "SCGP", "TISCO", "TOP",
    "TRUE", "TTA", "TU", "VGI", "WHA", "AMATA", "BCH", "CRC", "JMT"
]

def fetch_kaohoon_rss_news(symbol, limit=10):
    """ดึงข่าวจาก Kaohoon RSS สำหรับหุ้น SET50 โดยเช็ค symbol ใน title ก่อน ถ้าไม่มีค่อยเช็ค summary"""
    rss_url = f"https://www.kaohoon.com/feed/?s={symbol}"
    
    try:
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"RSS Error สำหรับ {symbol}: {feed.bozo_exception}")
            return []

        news_list = []
        symbol_upper = symbol.upper()

        for entry in feed.entries[:limit]:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip() or entry.get("description", "").strip()

            title_upper = title.upper()
            summary_upper = summary.upper()

            # เงื่อนไข: 
            # - ถ้า title มี symbol ตรง → ดึงเลย
            # - ถ้า title ไม่มี → เช็ค summary ถ้ามี symbol ตรง → ดึง
            # - ถ้าไม่มีทั้งคู่ → ข้าม
            if symbol_upper in title_upper or symbol_upper in summary_upper:
                news = {
                    "symbol": symbol,
                    "title": title,
                    "summary": summary,
                    "source": "Kaohoon",
                    "url": entry.get("link", ""),
                    "category": "หุ้น"
                }

                # จัดการวันที่ให้เป็น string 'YYYY-MM-DD' สำหรับ Supabase
                published = entry.get("published_parsed")
                news_date_str = datetime.now().strftime("%Y-%m-%d")
                if published:
                    try:
                        dt = datetime.fromtimestamp(time.mktime(published))
                        news_date_str = dt.strftime("%Y-%m-%d")
                    except:
                        pass
                news["news_date"] = news_date_str

                news_list.append(news)

        print(f"พบ {len(news_list)} ข่าวสำหรับ {symbol}")
        return news_list

    except Exception as e:
        print(f"Error ดึง RSS {symbol}: {e}")
        return []

def update_set50_news():
    total_news = 0
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n=== เริ่มอัพเดตข่าว SET50 วันที่ {today} ===")

    for symbol in SET50_SYMBOLS:
        print(f"ดึงข่าว {symbol}...")
        news_list = fetch_kaohoon_rss_news(symbol, limit=10)

        if news_list:
            try:
                supabase.table('stock_news').upsert(
                    news_list,
                    on_conflict='symbol, news_date, title'
                ).execute()
                inserted = len(news_list)
                total_news += inserted
                print(f"นำเข้า {inserted} ข่าวสำหรับ {symbol} สำเร็จ")
            except Exception as e:
                print(f"Error upsert {symbol}: {e}")

        # Delay 5 วินาทีระหว่างหุ้น
        time.sleep(5)

    print(f"\nสรุปการอัพเดตวันนี้: นำเข้าข่าวทั้งหมด {total_news} ข่าวจาก {len(SET50_SYMBOLS)} หุ้น")

def run_daily_scheduler():
    # รันทันทีครั้งแรก (เพื่อทดสอบ)
    update_set50_news()

    # ตั้งเวลาให้รันทุกวันตอน 19:00 น. (ถ้าคุณยังใช้ schedule อยู่)
    schedule.every().day.at("19:00").do(update_set50_news)

    print("Scheduler เริ่มทำงานแล้ว รอเวลา 19:00 ทุกวันเพื่ออัพเดตข่าว SET50")

    while True:
        schedule.run_pending()
        time.sleep(60)  # เช็คทุก 1 นาที

if __name__ == "__main__":
    print("โปรแกรมอัพเดตข่าวหุ้น SET50 เริ่มต้น...")
    # ถ้าคุณตั้ง Task Scheduler แล้ว → เรียกแค่ update_set50_news() ก็พอ
    update_set50_news()
    # ถ้ายังอยากใช้ schedule ในโค้ด (กรณีเปิดสคริปต์ค้าง) ให้ uncomment บรรทัดด้านล่าง
    # run_daily_scheduler()