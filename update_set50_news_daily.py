import os
import time
import feedparser
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

# ตั้งค่า logging ลงไฟล์ + แสดงบน console
log_file = 'set50_news_log.txt'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# โหลด .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("ไม่พบ SUPABASE_URL หรือ SUPABASE_KEY ใน .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# รายชื่อหุ้น SET50 (อัพเดต ณ ม.ค. 2026 - ถ้ามีปรับดัชนี แก้ list นี้ได้เลย)
SET50_SYMBOLS = [
    "AOT", "ADVANC", "BANPU", "BBL", "BCP", "BDMS", "BEM", "BGRIM", "BTS", "CBG",
    "CPALL", "CPF", "CPN", "DELTA", "EA", "EGCO", "GLOBAL", "GPSC", "GULF", "HMPRO",
    "INTUCH", "IRPC", "IVL", "KBANK", "KCE", "KTB", "KTC", "MINT", "MTC", "OR",
    "OSP", "PTT", "PTTEP", "PTTGC", "SAWAD", "SCB", "SCC", "SCGP", "TISCO", "TOP",
    "TRUE", "TTA", "TU", "VGI", "WHA", "AMATA", "BCH", "CRC", "JMT"
]

def get_news_date(entry):
    published = entry.get("published_parsed")
    if published:
        try:
            dt = datetime.fromtimestamp(time.mktime(published))
            return dt.strftime("%Y-%m-%d")
        except:
            pass
    return datetime.now().strftime("%Y-%m-%d")

def fetch_kaohoon_rss_news(symbol, limit=10):
    rss_url = f"https://www.kaohoon.com/feed/?s={symbol}"
    try:
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            logging.warning(f"Kaohoon RSS Error สำหรับ {symbol}: {feed.bozo_exception}")
            return []

        news_list = []
        symbol_upper = symbol.upper()

        for entry in feed.entries[:limit]:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip() or entry.get("description", "").strip()

            if symbol_upper in title.upper() or symbol_upper in summary.upper():
                news = {
                    "symbol": symbol,
                    "title": title,
                    "summary": summary,
                    "source": "Kaohoon",
                    "url": entry.get("link", ""),
                    "category": "หุ้น"
                }
                news["news_date"] = get_news_date(entry)
                news_list.append(news)

        logging.info(f"Kaohoon: พบ {len(news_list)} ข่าวสำหรับ {symbol}")
        return news_list

    except Exception as e:
        logging.error(f"Kaohoon Error ดึง {symbol}: {e}")
        return []

def fetch_set_rss_news(symbol, limit=5):
    rss_url = "https://www.set.or.th/en/rss/news.rss"
    try:
        feed = feedparser.parse(rss_url)
        news_list = []
        symbol_upper = symbol.upper()

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()

            if symbol_upper in title.upper() or symbol_upper in summary.upper():
                news = {
                    "symbol": symbol,
                    "title": title,
                    "summary": summary,
                    "source": "SET",
                    "url": entry.get("link", ""),
                    "category": "ประกาศบริษัท"
                }
                news["news_date"] = get_news_date(entry)
                news_list.append(news)

                if len(news_list) >= limit:
                    break

        logging.info(f"SET: พบ {len(news_list)} ข่าวสำหรับ {symbol}")
        return news_list

    except Exception as e:
        logging.error(f"SET Error ดึง {symbol}: {e}")
        return []

def fetch_investing_rss_news(symbol, limit=5):
    rss_url = "https://th.investing.com/rss/news_95.rss"
    try:
        feed = feedparser.parse(rss_url)
        news_list = []
        symbol_upper = symbol.upper()

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()

            if symbol_upper in title.upper() or symbol_upper in summary.upper():
                news = {
                    "symbol": symbol,
                    "title": title,
                    "summary": summary,
                    "source": "Investing",
                    "url": entry.get("link", ""),
                    "category": "วิเคราะห์"
                }
                news["news_date"] = get_news_date(entry)
                news_list.append(news)

                if len(news_list) >= limit:
                    break

        logging.info(f"Investing: พบ {len(news_list)} ข่าวสำหรับ {symbol}")
        return news_list

    except Exception as e:
        logging.error(f"Investing Error ดึง {symbol}: {e}")
        return []

def fetch_manager_rss_news(symbol, limit=5):
    rss_url = "https://www.manager.co.th/rss/stock"
    try:
        feed = feedparser.parse(rss_url)
        news_list = []
        symbol_upper = symbol.upper()

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()

            if symbol_upper in title.upper() or symbol_upper in summary.upper():
                news = {
                    "symbol": symbol,
                    "title": title,
                    "summary": summary,
                    "source": "Manager",
                    "url": entry.get("link", ""),
                    "category": "วิเคราะห์หุ้น"
                }
                news["news_date"] = get_news_date(entry)
                news_list.append(news)

                if len(news_list) >= limit:
                    break

        logging.info(f"Manager: พบ {len(news_list)} ข่าวสำหรับ {symbol}")
        return news_list

    except Exception as e:
        logging.error(f"Manager Error ดึง {symbol}: {e}")
        return []

def update_set50_news():
    total_news = 0
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logging.info(f"\n=== เริ่มอัพเดตข่าว SET50 วันที่ {today} ===")

    for symbol in SET50_SYMBOLS:
        logging.info(f"เริ่มดึงข่าว {symbol} จากทุกแหล่ง...")

        kaohoon_list = fetch_kaohoon_rss_news(symbol, limit=10)
        set_list = fetch_set_rss_news(symbol, limit=5)
        investing_list = fetch_investing_rss_news(symbol, limit=5)
        manager_list = fetch_manager_rss_news(symbol, limit=5)

        all_news = kaohoon_list + set_list + investing_list + manager_list

        if all_news:
            try:
                supabase.table('stock_news').upsert(
                    all_news,
                    on_conflict='symbol, news_date, title'
                ).execute()
                inserted = len(all_news)
                total_news += inserted
                logging.info(f"นำเข้า {inserted} ข่าวสำหรับ {symbol} จากทุกแหล่งสำเร็จ")
                # แสดงรายละเอียดข่าวที่เข้า DB (optional)
                for news in all_news:
                    logging.info(f"  - {news['source']}: {news['title']} ({news['news_date']})")
            except Exception as e:
                logging.error(f"Error upsert {symbol}: {e}")

        time.sleep(3)  # Delay ระหว่างหุ้น

    logging.info(f"\nสรุปการอัพเดตวันนี้: นำเข้าข่าวทั้งหมด {total_news} ข่าวจาก {len(SET50_SYMBOLS)} หุ้น")

if __name__ == "__main__":
    logging.info("เริ่มโปรแกรมอัพเดตข่าวหุ้น SET50...")
    update_set50_news()
    logging.info("อัพเดตเสร็จสิ้น")