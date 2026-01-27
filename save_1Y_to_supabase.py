import os
import time
import feedparser
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

# ตั้งค่า logging ลงไฟล์ + console
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
NEWS_DATA_IO_KEY = os.getenv("NEWS_DATA_IO_KEY")  # ถ้ามี

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("ไม่พบ SUPABASE_URL หรือ SUPABASE_KEY ใน .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# รายชื่อหุ้น SET50 (50 ตัว)
SET50_SYMBOLS = [
    "AOT", "ADVANC", "BANPU", "BBL", "BCP", "BDMS", "BEM", "BGRIM", "BTS", "CBG",
    "CPALL", "CPF", "CPN", "DELTA", "EA", "EGCO", "GLOBAL", "GPSC", "GULF", "HMPRO",
    "INTUCH", "IRPC", "IVL", "KBANK", "KCE", "KTB", "KTC", "MINT", "MTC", "OR",
    "OSP", "PTT", "PTTEP", "PTTGC", "SAWAD", "SCB", "SCC", "SCGP", "TISCO", "TOP",
    "TRUE", "TTA", "TU", "VGI", "WHA", "AMATA", "BCH", "CRC", "JMT"
]

# กำหนดช่วงย้อนหลัง (1 ปี = 365 วัน)
DAYS_BACK = 365
full_backfill = False  # เปลี่ยนเป็น True ถ้าต้องการดึงย้อนหลังเต็ม 1 ปี (ครั้งแรกเท่านั้น)

def get_date_range():
    today = datetime.now()
    from_date = (today - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    return from_date, to_date

def get_news_date(entry):
    published = entry.get("published_parsed")
    if published:
        try:
            dt = datetime.fromtimestamp(time.mktime(published))
            return dt.strftime("%Y-%m-%d")
        except:
            pass
    return datetime.now().strftime("%Y-%m-%d")

def fetch_kaohoon_rss(symbol, limit=50):  # เพิ่ม limit เพื่อดึงย้อนหลังมากขึ้น
    rss_url = f"https://www.kaohoon.com/feed/?s={symbol}"
    try:
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            logging.warning(f"Kaohoon RSS Error {symbol}: {feed.bozo_exception}")
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
                    "category": "หุ้น",
                    "news_date": get_news_date(entry)
                }
                news_list.append(news)

        logging.info(f"Kaohoon: พบ {len(news_list)} ข่าวสำหรับ {symbol}")
        return news_list

    except Exception as e:
        logging.error(f"Kaohoon ดึง {symbol} ล้มเหลว: {e}")
        return []

def fetch_set_rss(symbol, limit=20):
    rss_url = "https://www.set.or.th/en/rss/news.rss"
    try:
        feed = feedparser.parse(rss_url)
        news_list = []
        symbol_upper = symbol.upper()

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip() or ""

            if symbol_upper in title.upper() or symbol_upper in summary.upper():
                news = {
                    "symbol": symbol,
                    "title": title,
                    "summary": summary,
                    "source": "SET",
                    "url": entry.get("link", ""),
                    "category": "ประกาศบริษัท",
                    "news_date": get_news_date(entry)
                }
                news_list.append(news)
                if len(news_list) >= limit:
                    break

        logging.info(f"SET: พบ {len(news_list)} ข่าวสำหรับ {symbol}")
        return news_list

    except Exception as e:
        logging.error(f"SET ดึง {symbol} ล้มเหลว: {e}")
        return []

def fetch_investing_rss(symbol, limit=20):
    rss_url = "https://th.investing.com/rss/news_95.rss"
    try:
        feed = feedparser.parse(rss_url)
        news_list = []
        symbol_upper = symbol.upper()

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip() or ""

            if symbol_upper in title.upper() or symbol_upper in summary.upper():
                news = {
                    "symbol": symbol,
                    "title": title,
                    "summary": summary,
                    "source": "Investing",
                    "url": entry.get("link", ""),
                    "category": "วิเคราะห์",
                    "news_date": get_news_date(entry)
                }
                news_list.append(news)
                if len(news_list) >= limit:
                    break

        logging.info(f"Investing: พบ {len(news_list)} ข่าวสำหรับ {symbol}")
        return news_list

    except Exception as e:
        logging.error(f"Investing ดึง {symbol} ล้มเหลว: {e}")
        return []

def fetch_newsdata_io(symbol, limit=20):
    if not os.getenv("NEWS_DATA_IO_KEY"):
        logging.warning("ไม่มี NEWS_DATA_IO_KEY → ข้าม NewsData.io")
        return []

    api_key = os.getenv("NEWS_DATA_IO_KEY")
    from_date, to_date = get_date_range()
    url = f"https://newsdata.io/api/1/news?apikey={api_key}&q={symbol}&language=th&country=th&size={limit}&from_date={from_date}&to_date={to_date}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        news_list = []
        if data.get("status") == "success" and data.get("results"):
            for item in data["results"]:
                title = item.get("title", "").strip()
                description = item.get("description", "").strip() or ""

                if symbol.upper() in title.upper() or symbol.upper() in description.upper():
                    news = {
                        "symbol": symbol,
                        "title": title,
                        "summary": description,
                        "source": "NewsData.io",
                        "url": item.get("link", ""),
                        "category": "ข่าวหุ้น",
                        "news_date": item.get("pubDate", datetime.now().strftime("%Y-%m-%d"))[:10]
                    }
                    news_list.append(news)

        logging.info(f"NewsData.io: พบ {len(news_list)} ข่าวสำหรับ {symbol} (ย้อนหลัง {DAYS_BACK} วัน)")
        return news_list

    except Exception as e:
        logging.error(f"NewsData.io ดึง {symbol} ล้มเหลว: {e}")
        return []

def update_set50_news():
    total_news = 0
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"\n=== เริ่มอัพเดตข่าว SET50 วันที่ {today} ===")

    for symbol in SET50_SYMBOLS:
        logging.info(f"เริ่มดึง {symbol} จากทุกแหล่ง...")

        kaohoon = fetch_kaohoon_rss(symbol, limit=30)  # เพิ่ม limit เพื่อดึงมากขึ้น
        sett = fetch_set_rss(symbol, limit=10)
        investing = fetch_investing_rss(symbol, limit=10)
        newsdata = fetch_newsdata_io(symbol, limit=20) if NEWS_DATA_IO_KEY else []

        all_news = kaohoon + sett + investing + newsdata

        if all_news:
            try:
                supabase.table('stock_news').upsert(
                    all_news,
                    on_conflict='symbol, news_date, title'
                ).execute()
                count = len(all_news)
                total_news += count
                logging.info(f"นำเข้า {count} ข่าวสำหรับ {symbol} (Kaohoon:{len(kaohoon)}, SET:{len(sett)}, Investing:{len(investing)}, NewsData:{len(newsdata)})")
            except Exception as e:
                logging.error(f"Upsert {symbol} ล้มเหลว: {e}")

        time.sleep(3)  # Delay ระหว่างหุ้น

    logging.info(f"สรุปวันนี้: นำเข้าทั้งหมด {total_news} ข่าวจาก {len(SET50_SYMBOLS)} หุ้น")

if __name__ == "__main__":
    logging.info("เริ่มโปรแกรมอัพเดตข่าวหุ้น SET50...")
    update_set50_news()
    logging.info("อัพเดตเสร็จสิ้น")