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

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": str(TELEGRAM_CHAT_ID).strip(), 
        "text": f"✅ *Proxy: Active*\n{'-'*15}\n{message}", 
        "parse_mode": "Markdown", 
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[!] Critical: Could not send Telegram message: {e}")

def is_specific_movie_available(html_content, keyword):
    """Checks for showtime data specifically within the movie container."""
    soup = BeautifulSoup(html_content, "html.parser")
    # BookMyShow pages are dynamic; checking for the presence of the keyword in the title/showtime containers
    page_text = soup.get_text().lower()
    # If the page contains the movie keyword AND elements that look like showtimes
    if keyword.lower() in page_text:
        # Check for presence of showtime classes or time tags
        showtimes = soup.find_all(['div', 'a'], class_=lambda c: c and 'showtime' in c.lower())
        return len(showtimes) > 0
    return False

def run_check():
    if not all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PROXY_URL]):
        print("[!] Missing environment variables.")
        return
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    proxies = {"http": PROXY_URL, "https": PROXY_URL}
    
    for target in TARGETS:
        time.sleep(random.uniform(5, 10)) # Increased sleep to be safer for proxy
        try:
            resp = cffi_requests.get(
                target["url"], 
                headers=headers, 
                impersonate="chrome124", 
                proxies=proxies, 
                timeout=30
            )
            
            if resp.status_code == 200:
                if is_specific_movie_available(resp.text, target["keyword"]):
                    send_telegram_message(f"🚨 *BOOKINGS OPEN!* 🚨\n\n*Movie:* {target['movie']}\n*Date:* {target['date']}\n👉 [Book Now]({target['url']})")
                else:
                    print(f"[DEBUG] Page loaded for {target['movie']}, but no showtimes found.")
            else:
                print(f"[DEBUG] {target['movie']} returned status code: {resp.status_code}")
                
        except Exception as e:
            # This will now alert you if the proxy is blocked or the request fails
            error_msg = f"⚠️ *Error checking {target['movie']}:*\n`{str(e)}`"
            send_telegram_message(error_msg)

if __name__ == "__main__":
    run_check()
