import os
import time
import random
from datetime import datetime
from curl_cffi import requests

# Retrieve secrets from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")  # Format: http://username:password@ip:port

# Target configurations
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

def send_telegram_message(message: str) -> None:
    """Sends a formatted notification message to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables.")
        return

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        # Telegram API calls do not require proxy routing
        requests.post(telegram_url, data=payload, timeout=10)
    except Exception as e:
        print(f"[!] Failed to send Telegram alert: {e}")

def check_availability() -> None:
    """Performs availability checks for defined movie targets using curl_cffi."""
    now_utc = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"--- Running BookMyShow Check at {now_utc} ---")

    # Configure proxy if available
    proxies = None
    if PROXY_URL:
        formatted_proxy = PROXY_URL if PROXY_URL.startswith("http") else f"http://{PROXY_URL}"
        proxies = {
            "http": formatted_proxy,
            "https": formatted_proxy,
        }
        print("[+] Proxy configured successfully.")
    else:
        print("[!] Warning: PROXY_URL not set. Requesting directly from runner IP.")

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Referer": "https://in.bookmyshow.com/",
    }

    for target in TARGETS:
        # Add a random delay between requests to avoid rate limits
        time.sleep(random.uniform(3, 6))

        try:
            # Impersonate modern Chrome browser TLS fingerprint
            response = requests.get(
                target["url"],
                headers=headers,
                impersonate="chrome120",
                proxies=proxies,
                timeout=25
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
                    print(f"[+] Match found for {target['movie']}! Alert sent.")
                else:
                    print(f"[-] {target['movie']} not open yet.")

            elif response.status_code in (403, 429, 503):
                print(f"[!] Blocked (HTTP {response.status_code}) for {target['movie']}.")
            else:
                print(f"[!] Unexpected status code {response.status_code} for {target['movie']}.")

        except Exception as e:
            print(f"[!] Request error checking {target['movie']}: {e}")

if __name__ == "__main__":
    check_availability()
