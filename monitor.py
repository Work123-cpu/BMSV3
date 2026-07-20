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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
]

def send_telegram_message(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Telegram credentials missing.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID.strip(), "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[!] Telegram error: {e}")

def run_check():
    # Heartbeat to confirm script execution
    send_telegram_message("🤖 Monitor check started.")
    
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    
    for target in TARGETS:
        time.sleep(random.uniform(5, 10))
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        try:
            resp = cffi_requests.get(target["url"], headers=headers, impersonate="chrome124", proxies=proxies, timeout=20)
            
            if resp.status_code != 200:
                print(f"[!] Status {resp.status_code} for {target['movie']}")
                continue
                
            soup = BeautifulSoup(resp.text, "html.parser")
            # If the specific movie keyword is found in the text
            if target["keyword"].lower() in soup.get_text().lower():
                send_telegram_message(f"🚨 *FOUND:* {target['movie']}\nLink: {target['url']}")
            else:
                print(f"[DEBUG] {target['movie']}: Keyword '{target['keyword']}' not found.")
                
        except Exception as e:
            print(f"[!] Error on {target['movie']}: {e}")

if __name__ == "__main__":
    run_check()
