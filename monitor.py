import os
import json
import time
import random
import requests  # Standard requests for Telegram API
from curl_cffi import requests as cffi_requests  # cffi requests strictly for scraping
from bs4 import BeautifulSoup

# Secrets from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

# Static default watchlist strictly for your requested movies
DEFAULT_TARGETS = [
    {
        "movie": "Jana Nayagan",
        "date": "2026-07-23",
        "url": "https://in.bookmyshow.com/buytickets/broadway-cinemas-coimbatore/cinema-coim-BWCC-MT/20260723",
        "keyword": "Jana Nayagan"
    },
    {
        "movie": "The Odyssey (IMAX)",
        "date": "2026-07-30",
        "url": "https://in.bookmyshow.com/buytickets/broadway-cinemas-coimbatore/cinema-coim-BWCC-MT/20260730",
        "keyword": "The Odyssey"
    },
    {
        "movie": "The Odyssey (IMAX)",
        "date": "2026-07-31",
        "url": "https://in.bookmyshow.com/buytickets/broadway-cinemas-coimbatore/cinema-coim-BWCC-MT/20260731",
        "keyword": "The Odyssey"
    }
]

# --- TELEGRAM HELPER FUNCTIONS ---

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

def get_telegram_updates(offset=None) -> list:
    if not TELEGRAM_TOKEN:
        return []
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/getUpdates"
    params = {"timeout": 5}
    if offset:
        params["offset"] = offset
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception as e:
        print(f"[!] Telegram update error: {e}")
    return []

# --- DATABASE / STATE MANAGEMENT ---

def get_db_state() -> dict:
    """Retrieves state from Telegram updates or defaults to the specified target list."""
    default_state = {
        "targets": DEFAULT_TARGETS,
        "wizard_step": None,
        "temp_data": {},
        "last_update_id": 0
    }
    
    try:
        updates = get_telegram_updates()
        for item in reversed(updates):
            msg = item.get("message", {}) or item.get("channel_post", {})
            text = msg.get("text", "")
            if "=== BMS_BOT_DATABASE ===" in text:
                json_str = text.split("```")[1].replace("json", "").strip()
                parsed_state = json.loads(json_str)
                parsed_state["last_update_id"] = max(
                    parsed_state.get("last_update_id", 0),
                    item.get("update_id", 0)
                )
                return parsed_state
    except Exception as e:
        print(f"[!] Could not read database state: {e}")

    return default_state

def save_db_state(db: dict) -> None:
    formatted_json = json.dumps(db, indent=2)
    msg_text = f"=== BMS_BOT_DATABASE ===\n```json\n{formatted_json}\n```"
    send_telegram_message(msg_text)

# --- COMMAND HANDLING ---

def process_telegram_commands(db: dict) -> dict:
    last_id = db.get("last_update_id", 0)
    updates = get_telegram_updates(offset=last_id + 1 if last_id else None)
    
    if not updates:
        return db

    updated = False
    targets = db.get("targets", DEFAULT_TARGETS)

    for item in updates:
        update_id = item.get("update_id")
        if update_id:
            db["last_update_id"] = max(db.get("last_update_id", 0), update_id)
            updated = True

        message = item.get("message", {})
        text = message.get("text", "").strip()

        if not text:
            continue

        cmd = text.split()[0].lower()

        # Command /list or /start
        if cmd in ["/list", "/start", "/movies"]:
            msg = "🎬 *Monitored Movies Watchlist:*\n\n"
            for idx, t in enumerate(targets, 1):
                msg += f"{idx}. *{t['movie']}*\n📅 Date: `{t['date']}`\n📍 Broadway Cinemas, Coimbatore\n\n"
            send_telegram_message(msg)

    db["targets"] = targets
    if updated:
        save_db_state(db)

    return db

# --- TICKET CHECKING LOGIC ---

def is_booking_available(html_content: str) -> bool:
    soup = BeautifulSoup(html_content, "html.parser")
    showtimes = soup.find_all(class_=lambda c: c and any(
        term in c.lower() for term in ["showtime", "show-time", "session-time", "showtime-pill"]
    ))
    return len(showtimes) > 0

def check_availability() -> None:
    db = get_db_state()
    db = process_telegram_commands(db)

    targets = db.get("targets", DEFAULT_TARGETS)
    if not targets:
        print("[!] No targets found.")
        return

    proxies = None
    if PROXY_URL:
        formatted_proxy = PROXY_URL if PROXY_URL.startswith("http") else f"http://{PROXY_URL}"
        proxies = {"http": formatted_proxy, "https": formatted_proxy}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "[https://in.bookmyshow.com/](https://in.bookmyshow.com/)",
    }

    for target in targets:
        time.sleep(random.uniform(1, 3))
        try:
            response = cffi_requests.get(
                target["url"],
                headers=headers,
                impersonate="chrome124",
                proxies=proxies,
                timeout=20
            )

            if response.status_code == 200 and is_booking_available(response.text):
                msg = (
                    f"🚨 *BOOKINGS OPEN!* 🚨\n\n"
                    f"*Movie:* {target['movie']}\n"
                    f"*Date:* {target['date']}\n"
                    f"*Location:* Broadway Cinemas, Coimbatore\n\n"
                    f"👉 [Book Tickets on BookMyShow]({target['url']})"
                )
                send_telegram_message(msg)
                print(f"[+] Bookings open for {target['movie']} ({target['date']})!")
            else:
                print(f"[-] No showtimes for {target['movie']} ({target['date']}).")

        except Exception as e:
            print(f"[!] Error checking {target['movie']}: {e}")

if __name__ == "__main__":
    check_availability()
