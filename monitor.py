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

def get_telegram_updates(offset: int = None) -> tuple[list, int]:
    """Polls Telegram for incoming commands and returns updates with the next offset."""
    if not TELEGRAM_TOKEN:
        return [], offset

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/getUpdates"
    params = {"timeout": 1, "limit": 100}
    if offset is not None:
        params["offset"] = offset

    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            updates = res.json().get("result", [])
            if updates:
                # Calculate next offset to mark fetched updates as read
                new_offset = updates[-1]["update_id"] + 1
                return updates, new_offset
    except Exception:
        pass

    return [], offset

def flush_old_updates() -> int:
    """Clears pending messages from queue on startup to prevent infinite loops."""
    print("[+] Flushing old Telegram updates...")
    updates, next_offset = get_telegram_updates(offset=-1)
    if updates:
        # Requesting next_offset acknowledges and clears all previous updates
        get_telegram_updates(offset=next_offset)
        print(f"[+] Cleared {len(updates)} pending update(s).")
    return next_offset

# --- BOOKMYSHOW SCRAPING & CHECKING LOGIC ---

def is_specific_movie_available(html_content: str, keyword: str) -> bool:
    """
    1. Verifies showtime UI elements exist on the page.
    2. Verifies the specific movie title keyword is listed under those showtimes.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    showtimes = soup.find_all(class_=lambda c: c and any(
        term in c.lower() for term in ["showtime", "show-time", "session-time", "showtime-pill"]
    ))
    
    if not showtimes:
        return False

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
            response = cffi_requests.get(
                target["url"],
                headers=headers,
                impersonate="chrome124",
                proxies=proxies,
                allow_redirects=False,
                timeout=20
            )

            if response.status_code in [301, 302]:
                status_msg = (
                    f"🔍 *Check Update:*\n"
                    f"• *Movie:* `{target['movie']}` ({target['date']})\n"
                    f"• *Status:* Date NOT released yet (redirected by BMS)."
                )
                send_telegram_message(status_msg)
                print(f"[-] {target['movie']} ({target['date']}): Date not released.")
                continue

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

    # Clear old updates first to prevent infinite execution loop on launch
    current_offset = flush_old_updates()

    # Initial boot check
    run_check_cycle()
    last_auto_check = time.time()

    while True:
        try:
            # 1. Listen for manual Telegram commands
            updates, current_offset = get_telegram_updates(offset=current_offset)
            
            trigger_check = False
            for item in updates:
                message = item.get("message", {})
                text = message.get("text", "").strip()
                if text in ["/check", "/start", "/status"]:
                    print(f"[!] Valid command '{text}' received via Telegram.")
                    trigger_check = True

            # If at least one valid /check command was sent
            if trigger_check:
                send_telegram_message("⏳ Running manual BookMyShow check...")
                run_check_cycle()
                last_auto_check = time.time()  # Reset 10-minute timer

            # 2. Check if 10 minutes have passed since the last check
            if time.time() - last_auto_check >= CHECK_INTERVAL_SECONDS:
                print("[!] 10 minutes elapsed — Running scheduled check.")
                run_check_cycle()
                last_auto_check = time.time()

            time.sleep(2)  # Pauses polling loop to avoid spamming CPU/network

        except KeyboardInterrupt:
            print("\n[!] Stopping monitor...")
            sys.exit(0)
        except Exception as e:
            print(f"[!] Exception in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
