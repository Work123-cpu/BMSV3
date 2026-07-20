import os
import time
import random
from datetime import datetime
from curl_cffi import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

TARGETS = [
    {
        "movie": "Jana Nayagan",
        "date": "2026-07-24",
        "url": "https://in.bookmyshow.com/buytickets/broadway-cinemas-coimbatore/cinema-coim-BWCC-MT/20260724",
        "keyword": "Jana Nayagan"
    },
    {
        "movie": "The Odyssey (IMAX)",
        "date": "2026-07-30/31",
        "url": "https://in.bookmyshow.com/buytickets/broadway-cinemas-coimbatore/cinema-coim-BWCC-MT/20260730",
        "keyword": "Odyssey"
    }
]

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Missing TELEGRAM credentials.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"[!] Telegram send error: {e}")

def check_availability():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"--- Running BookMyShow Check at {now} ---")

    for target in TARGETS:
        # Delays help avoid triggering aggressive IP rate limits
        time.sleep(random.uniform(3, 7))

        try:
            # Impersonate realistic Chrome TLS fingerprints
            response = requests.get(
                target["url"],
                impersonate="chrome120",
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                },
                timeout=20
            )
            
            if response.status_code == 200:
                if target["keyword"].lower() in response.text.lower():
                    msg = (
                        f"🚨 *BOOKINGS OPEN!* 🚨\n\n"
                        f"*Movie:* {target['movie']}\n"
                        f"*Date:* {target['date']}\n"
                        f"*Venue:* Broadway Cinemas, Coimbatore\n\n"
                        f"👉 [Book Now]({target['url']})"
                    )
                    send_telegram_message(msg)
                    print(f"[+] Match found for {target['movie']}!")
                else:
                    print(f"[-] {target['movie']} not open yet.")

            elif response.status_code in [403, 429, 503]:
                print(f"[!] Blocked ({response.status_code}) for {target['movie']}.")
                # Quietly log without spamming Telegram alerts on every block
            else:
                print(f"[!] Unexpected status {response.status_code} for {target['movie']}")

        except Exception as e:
            print(f"[!] Error checking {target['movie']}: {e}")

if __name__ == "__main__":
    check_availability()
