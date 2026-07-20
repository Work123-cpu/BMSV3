import os
import sys
import time
import random
import traceback
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
PROXY_URL = os.environ.get("PROXY_URL", "")

TARGETS = [
    {"movie": "Jana Nayagan", "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260723", "keyword": "Jana Nayagan"},
    {"movie": "The Odyssey", "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260730", "keyword": "Odyssey"},
    {"movie": "The Odyssey", "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260731", "keyword": "Odyssey"}
]

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Telegram failed: {e}")

def run():
    print("--- Script Starting ---")
    
    # 1. Test Telegram Connection
    send_telegram("🚀 Monitor script successfully started.")

    # 2. Check each target
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    
    for target in TARGETS:
        print(f"Checking: {target['movie']}...")
        try:
            # Using impersonate to bypass cloudflare/403 blocks
            resp = cffi_requests.get(
                target["url"], 
                impersonate="chrome124", 
                proxies=proxies, 
                timeout=30
            )
            
            if resp.status_code == 200:
                if target["keyword"].lower() in resp.text.lower():
                    send_telegram(f"✅ Tickets found for: {target['movie']}\n{target['url']}")
                else:
                    print(f"No showtimes for {target['movie']}.")
            else:
                print(f"Request failed for {target['movie']} with status: {resp.status_code}")
                
        except Exception as e:
            print(f"Error checking {target['movie']}: {e}")
        
        time.sleep(random.randint(5, 10))

if __name__ == "__main__":
    try:
        run()
    except Exception:
        print("CRITICAL CRASH:")
        print(traceback.format_exc())
        sys.exit(1)
