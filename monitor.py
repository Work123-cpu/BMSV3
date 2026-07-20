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
    {"movie": "The Odyssey (IMAX)", "date": "2026-07-30", "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260730", "keyword": "Odyssey"},
    {"movie": "The Odyssey (IMAX)", "date": "2026-07-31", "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260731", "keyword": "Odyssey"}
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": str(TELEGRAM_CHAT_ID).strip(), 
        "text": f"✅ *Proxy: Active*\n{'-'*15}\n{message}", 
        "parse_mode": "Markdown", 
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"[!] Telegram error: {e}")

def is_specific_movie_available(html_content, keyword):
    soup = BeautifulSoup(html_content, "html.parser")
    # Search for showtime-related elements
    showtimes = soup.find_all(lambda tag: tag.name in ['div', 'a'] and tag.get('class') and any('showtime' in c.lower() for c in tag['class']))
    return len(showtimes) > 0 and keyword.lower() in soup.get_text().lower()

def run_check():
    if not all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PROXY_URL]):
        print("[!] Missing environment variables.")
        return
    
    proxies = {"http": PROXY_URL, "https": PROXY_URL}
    
    for target in TARGETS:
        # Increased wait time to prevent 403 blocks
        time.sleep(random.uniform(15, 30))
        
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        try:
            resp = cffi_requests.get(
                target["url"], 
                headers=headers, 
                impersonate="chrome124", 
                proxies=proxies, 
                timeout=30
            )
            
            if resp.status_code == 403:
                print(f"[!] Access Forbidden (403) for {target['movie']}. Proxy may be flagged.")
            elif resp.status_code == 200:
                if is_specific_movie_available(resp.text, target["keyword"]):
                    send_telegram_message(f"🚨 *BOOKINGS OPEN!* 🚨\n\n*Movie:* {target['movie']}\n👉 [Book Now]({target['url']})")
                else:
                    print(f"[DEBUG] Page live for {target['movie']}, but showtimes not yet released.")
            else:
                print(f"[!] Received status {resp.status_code} for {target['movie']}")
                
        except Exception as e:
            error_msg = f"⚠️ *Error checking {target['movie']}:*\n`{str(e)}`"
            send_telegram_message(error_msg)

if __name__ == "__main__":
    run_check()
