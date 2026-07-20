import os
import time
import random
import requests  # Standard requests for Telegram API
from curl_cffi import requests as cffi_requests  # cffi_requests strictly for scraping
from bs4 import BeautifulSoup

# Secrets from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

# Monitored movies
TARGETS = [
    {
        "movie": "Jana Nayagan",
        "date": "2026-07-23",
        "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260723",
        "keyword": "Jana Nayagan"
    },
    {
        "movie": "The Odyssey (IMAX)",
        "date": "2026-07-30",
        "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260730",
        "keyword": "The Odyssey"
    },
    {
        "movie": "The Odyssey (IMAX)",
        "date": "2026-07-31",
        "url": "https://in.bookmyshow.com/cinemas/coimbatore/broadway-cinemas-coimbatore/buytickets/BWCB/20260731",
        "keyword": "The Odyssey"
    }
]

def send_telegram_message(message: str) -> dict:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID.")
        return {}

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": str(TELEGRAM_CHAT_ID).strip(),
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, data=payload, timeout=10)
        return res.json()
    except Exception as e:
        print(f"[!] Telegram send error: {e}")
        return {}

def is_booking_available(html_content: str) -> bool:
    soup = BeautifulSoup(html_content, "html.parser")
    showtimes = soup.find_all(class_=lambda c: c and any(
        term in c.lower() for term in ["showtime", "show-time", "session-time", "showtime-pill"]
    ))
    return len(showtimes) > 0

def check_availability() -> None:
    proxies = None
    if PROXY_URL:
        formatted_proxy = PROXY_URL if PROXY_URL.startswith("http") else f"http://{PROXY_URL}"
        proxies = {"http": formatted_proxy, "https": formatted_proxy}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://in.bookmyshow.com/",
    }

    for target in TARGETS:
        time.sleep(random.uniform(1, 3))
        try:
            # allow_redirects=False stops BookMyShow from sending unreleased dates back to today
            response = cffi_requests.get(
                target["url"],
                headers=headers,
                impersonate="chrome124",
                proxies=proxies,
                allow_redirects=False,
                timeout=20
            )

            # 301/302 means showtimes for this date are not open
            if response.status_code in [301, 302]:
                status_msg = f"🔍 *Check Update:* `{target['movie']}` ({target['date']}) — Tickets *NOT* open yet (redirected)."
                send_telegram_message(status_msg)
                print(f"[-] {target['movie']} ({target['date']}): Redirected (not open).")
                continue

            if response.status_code == 200 and is_booking_available(response.text):
                alert_msg = (
                    f"🚨 *BOOKINGS OPEN!* 🚨\n\n"
                    f"*Movie:* {target['movie']}\n"
                    f"*Date:* {target['date']}\n"
                    f"*Location:* Broadway Cinemas, Coimbatore\n\n"
                    f"👉 [Book Tickets on BookMyShow]({target['url']})"
                )
                send_telegram_message(alert_msg)
                print(f"[+] Bookings OPEN for {target['movie']} ({target['date']})!")
            else:
                status_msg = f"🔍 *Check Update:* `{target['movie']}` ({target['date']}) — Page loaded, but no showtimes available yet."
                send_telegram_message(status_msg)
                print(f"[-] {target['movie']} ({target['date']}): No showtimes found.")

        except Exception as e:
            error_msg = f"⚠️ *Check Error:* Could not reach BookMyShow for `{target['movie']}` ({target['date']})."
            send_telegram_message(error_msg)
            print(f"[!] Error checking {target['movie']}: {e}")

if __name__ == "__main__":
    check_availability()
