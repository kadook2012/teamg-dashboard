import os
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: ไม่พบ SUPABASE_URL หรือ SUPABASE_KEY")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TARGET_SYMBOLS = ["SECURE", "TEAMG"]
ONE_YEAR_AGO = (datetime.now() - timedelta(days=365)).date()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

MONTH_TH_TO_NUM = {
    'ม.ค.': 1, 'ก.พ.': 2, 'มี.ค.': 3, 'เม.ย.': 4, 'พ.ค.': 5, 'มิ.ย.': 6,
    'ก.ค.': 7, 'ส.ค.': 8, 'ก.ย.': 9, 'ต.ค.': 10, 'พ.ย.': 11, 'ธ.ค.': 12,
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}

def parse_date(date_str):
    """Parse วันที่แบบไทย/อังกฤษ เช่น '13 Nov', '15 13 Jan', '24 13 พ.ย.' """
    date_str = date_str.strip().lower()
    try:
        # ลอง pattern ทั่วไป: digit + month (อาจมีปี พ.ศ.)
        match = re.search(r'(\d{1,2})\s*(\w{3,})\s*(\d{4})?', date_str)
        if match:
            day = int(match.group(1))
            month_str = match.group(2).capitalize()
            year_str = match.group(3)
            month = MONTH_TH_TO_NUM.get(month_str, None)
            if not month:
                month = MONTH_TH_TO_NUM.get(month_str[:3], None)
            if month:
                year = int(year_str) - 543 if year_str else datetime.now().year
                return datetime(year, month, day).date()
        # fallback วันนี้
        return datetime.now().date()
    except:
        return datetime.now().date()


def fetch_gapfocus_news(symbol):
    url = f"https://stock.gapfocus.com/detail/{symbol}"
    news_list = []
    seen_urls = set()

    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
    except Exception as e:
        print(f"Error ดึง {symbol}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # พยายามหา container ข่าวหลัก (หลาย selector)
    possible_containers = [
        soup.find_all('div', class_=re.compile(r'(talk|news|item|schedule|post|entry)')),
        soup.find_all('li'),
        soup.find_all('article'),
        soup.find_all('div', string=re.compile(r'(Views|ประเด็นข่าว|talk|pdf|youtube)', re.I))
    ]

    blocks = []
    for cont in possible_containers:
        if cont:
            blocks.extend(cont)
            break

    if not blocks:
        # fallback: ดึง text ทั้งหน้า แล้ว split เป็นบรรทัด
        full_text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in full_text.split('\n') if line.strip() and len(line) > 20]
        # สมมติ pattern: symbol + date + title
        current_news = None
        for line in lines:
            if symbol.upper() in line.upper():
                if current_news:
                    news_list.append(current_news)
                current_news = {'title': line, 'url': url, 'source': 'Gapfocus'}
            elif current_news:
                current_news['summary'] = (current_news.get('summary', '') + ' ' + line).strip()
        if current_news:
            news_list.append(current_news)
    else:
        # parse จาก blocks
        for block in blocks:
            title_tag = block.find(['a', 'h3', 'h4', 'strong', 'span'], string=re.compile(r'.{10,}'))
            title = title_tag.get_text(strip=True) if title_tag else block.get_text(strip=True)[:150]

            if not title or len(title) < 15:
                continue

            news_url = title_tag['href'] if title_tag and 'href' in title_tag.attrs else url
            if not news_url.startswith('http'):
                news_url = 'https://stock.gapfocus.com' + news_url
            if news_url in seen_urls:
                continue
            seen_urls.add(news_url)

            # หาวันที่
            date_tag = block.find(['time', 'span', 'small'], string=re.compile(r'\d{1,2}\s*(Jan|Feb|Nov|ม.ค.|พ.ย.)|\d{1,2}\s*\d{1,2}'))
            date_text = date_tag.get_text(strip=True) if date_tag else ''
            news_date = parse_date(date_text) if date_text else datetime.now().date()

            if news_date < ONE_YEAR_AGO:
                continue

            source = 'Gapfocus'
            if 'SET' in title or 'Yuanta' in title:
                source = 'SET/Yuanta'

            summary_tag = block.find(['p', 'div'], class_=re.compile(r'detail|desc|summary'))
            summary = summary_tag.get_text(strip=True) if summary_tag else title[:300]

            news = {
                'symbol': symbol,
                'title': title,
                'url': news_url,
                'news_date': news_date.isoformat(),
                'summary': summary,
                'source': source
            }
            news_list.append(news)

    print(f"พบ {len(news_list)} ข่าวสำหรับ {symbol} (หลัง filter 1 ปี)")
    return news_list


def upsert_gapfocus_news():
    all_news = []
    for symbol in TARGET_SYMBOLS:
        print(f"ดึง {symbol} จาก Gapfocus...")
        news = fetch_gapfocus_news(symbol)
        all_news.extend(news)
        time.sleep(6)  # ช้า ๆ ป้องกัน block

    if all_news:
        try:
            supabase.table('stock_news').upsert(
                all_news,
                on_conflict='url'
            ).execute()
            print(f"นำเข้า {len(all_news)} ข่าวสำเร็จ")
        except Exception as e:
            print(f"Upsert error: {e}")

    return all_news


if __name__ == "__main__":
    print("ดึงข่าว SECURE + TEAMG จาก stock.gapfocus.com ย้อนหลัง 1 ปี...")
    upsert_gapfocus_news()