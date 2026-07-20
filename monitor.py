import os
import sys
import time
import random
import requests  # Standard requests for Telegram Bot API
from curl_cffi import requests as cffi_requests  # cffi_requests strictly for scraping BMS
from bs4 import BeautifulSoup

# --- ENVIRONMENT CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

# Set automated check interval strictly to 10 minutes (600 seconds)
CHECK_INTERVAL_SECONDS = 10 * 60

# Target Movies & URLs for Broadway Cinemas, Coimbatore (BWCB)
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

# --- TELEGRAM BOT HELPERS ---

def send_telegram_message(message: str) -> dict:
    """Sends a formatted Markdown message to Telegram Chat."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Error: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables.")
        return {}

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": str(TELEGRAM_CHAT_ID).strip(),
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.json()
    except Exception as e:
        print(f"[!] Telegram send error: {e}")
        return {}

def get_telegram_updates(offset: int = None) -> list:
    """Polls Telegram for incoming slash commands (e.g., /check)."""
    if not TELEGRAM_TOKEN:
        return []
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/getUpdates"
    params = {"timeout": 2}
    if offset:
        params["offset"] = offset
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception:
        pass
    return []

# --- BOOKMYSHOW SCRAPING & CHECKING LOGIC ---

def is_specific_movie_available(html_content: str, keyword: str) -> bool:
    """
    1. Verifies showtime UI elements exist on the page.
    2. Verifies the specific movie title keyword is listed under those showtimes.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Check if showtime elements exist
    showtimes = soup.find_all(class_=lambda c: c and any(
        term in c.lower() for term in ["showtime", "show-time", "session-time", "showtime-pill"]
    ))
    
    if not showtimes:
        return False

    # Check if the specific movie name exists in page text
    page_text = soup.get_text().lower()
    return keyword.lower() in page_text

def run_check_cycle() -> None:
    """Executes a full check across all monitored targets."""
    print("\n[+] Starting BookMyShow availability check cycle...")
    
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
        time.sleep(random.uniform(1.5, 3.0))
        try:
            # allow_redirects=False catches BMS redirects when dates are unreleased
            response = cffi_requests.get(
                target["url"],
                headers=headers,
                impersonate="chrome124",
                proxies=proxies,
                allow_redirects=False,
                timeout=20
            )

            # 301/302 Redirect = Entire date schedule is unreleased
            if response.status_code in [301, 302]:
                status_msg = (
                    f"🔍 *Check Update:*\n"
                    f"• *Movie:* `{target['movie']}` ({target['date']})\n"
                    f"• *Status:* Date NOT released yet (redirected by BMS)."
                )
                send_telegram_message(status_msg)
                print(f"[-] {target['movie']} ({target['date']}): Date not released.")
                continue

            # Check if specific movie has showtimes on this date
            if response.status_code == 200 and is_specific_movie_available(response.text, target["keyword"]):
                alert_msg = (
                    f"🚨 *BOOKINGS OPEN!* 🚨\n\n"
                    f"*Movie:* {target['movie']}\n"
                    f"*Date:* {target['date']}\n"
                    f"*Location:* Broadway Cinemas, Coimbatore\n\n"
                    f"👉 [Book Tickets on BookMyShow]({target['url']})"
                )
                send_telegram_message(alert_msg)
                print(f"[+] SUCCESS: Bookings open for {target['movie']} ({target['date']})!")
            else:
                status_msg = (
                    f"🔍 *Check Update:*\n"
                    f"• *Movie:* `{target['movie']}` ({target['date']})\n"
                    f"• *Status:* Date is open, but *{target['movie']}* showtimes are not added yet."
                )
                send_telegram_message(status_msg)
                print(f"[-] {target['movie']} ({target['date']}): Movie showtimes not added yet.")

        except Exception as e:
            error_msg = f"⚠️ *Check Error:* Could not check `{target['movie']}` ({target['date']}). Exception: {e}"
            send_telegram_message(error_msg)
            print(f"[!] Error checking {target['movie']}: {e}")

# --- MAIN EXECUTION LOOP ---

def main():
    print("[+] Monitor active in Continuous Mode.")
    print("[+] Automated checks scheduled every 10 minutes.")
    print("[+] Listening for '/check' command in Telegram...\n")

    # Run initial check immediately on launch
    run_check_cycle()

    last_update_id = None
    last_auto_check = time.time()

    while True:
        try:
            # 1. Listen for manual Telegram commands (/check, /start, /status)
            updates = get_telegram_updates(offset=last_update_id)
            for item in updates:
                last_update_id = item.get("update_id", 0) + 1

                message = item.get("message", {})
                text = message.get("text", "").strip()
                
                if text in ["/check", "/start", "/status"]:
                    print(f"[!] Command '{text}' received via Telegram.")
                    send_telegram_message("⏳ Running manual BookMyShow check...")
                    run_check_cycle()
                    last_auto_check = time.time()  # Reset 10-minute timer on command check

            # 2. Check if 10 minutes have passed since the last check
            if time.time() - last_auto_check >= CHECK_INTERVAL_SECONDS:
                print("[!] 10 minutes elapsed — Running scheduled check.")
                run_check_cycle()
                last_auto_check = time.time()

            time.sleep(2)  # Short sleep to keep loop efficient

        except KeyboardInterrupt:
            print("\n[!] Stopping monitor...")
            sys.exit(0)
        except Exception as e:
            print(f"[!] Exception in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
