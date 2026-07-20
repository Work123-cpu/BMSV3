import os
import random
import time
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

TARGETS = [
    {"movie": "Jana Nayagan", "date": "2026-07-23", "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260723", "keyword": "Jana Nayagan"},
    {"movie": "The Odyssey (IMAX)", "date": "2026-07-30", "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260730", "keyword": "The Odyssey"},
    {"movie": "The Odyssey (IMAX)", "date": "2026-07-31", "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260731", "keyword": "The Odyssey"}
]

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    payload = {"chat_id": str(TELEGRAM_CHAT_ID).strip(), "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload, timeout=10)

def is_specific_movie_available(html_content, keyword):
    soup = BeautifulSoup(html_content, "html.parser")
    showtimes = soup.find_all(class_=lambda c: c and any(t in c.lower() for t in ["showtime", "show-time", "session-time", "showtime-pill"]))
    return len(showtimes) > 0 and keyword.lower() in soup.get_text().lower()

def run_check():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    
    for target in TARGETS:
        time.sleep(random.uniform(2, 5))
        try:
            resp = cffi_requests.get(target["url"], headers=headers, impersonate="chrome124", proxies=proxies, allow_redirects=False, timeout=20)
            
            if resp.status_code in [301, 302]:
                send_telegram_message(f"🔍 *{target['movie']}* ({target['date']}) — Date NOT released yet.")
            elif resp.status_code == 200 and is_specific_movie_available(resp.text, target["keyword"]):
                send_telegram_message(f"🚨 *BOOKINGS OPEN!* 🚨\n\n*Movie:* {target['movie']}\n*Date:* {target['date']}\n👉 [Book Now]({target['url']})")
            else:
                send_telegram_message(f"🔍 *{target['movie']}* ({target['date']}) — Date is open, but showtimes are not added yet.")
        except Exception as e:
            send_telegram_message(f"⚠️ *Error checking {target['movie']}:* {e}")

if __name__ == "__main__":
    run_check()
