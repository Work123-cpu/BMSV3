import os
import json
import time
import random
from datetime import datetime, timedelta
from curl_cffi import requests
from bs4 import BeautifulSoup

# Secrets from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

# --- TELEGRAM HELPER FUNCTIONS ---

def send_telegram_message(message: str) -> dict:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID.")
        return {}

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
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

def get_telegram_updates() -> list:
    if not TELEGRAM_TOKEN:
        return []
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception as e:
        print(f"[!] Telegram update error: {e}")
    return []

# --- DATABASE / STATE MANAGEMENT (Telegram Pinned Message) ---

def get_db_state() -> dict:
    """Retrieves targets and state from the pinned message."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getChat"
    default_state = {
        "targets": [
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
        ],
        "wizard_step": None,
        "temp_data": {}
    }
    
    try:
        res = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, timeout=10)
        chat_info = res.json()
        pinned = chat_info.get("result", {}).get("pinned_message", {}).get("text", "")
        if "=== BMS_BOT_DATABASE ===" in pinned:
            json_str = pinned.split("```")[1].strip()
            return json.loads(json_str)
    except Exception as e:
        print(f"[!] Could not read database state: {e}")

    return default_state

def save_db_state(db: dict) -> None:
    """Saves updated database state back to Telegram pinned message."""
    formatted_json = json.dumps(db, indent=2)
    msg_text = f"=== BMS_BOT_DATABASE ===\n```json\n{formatted_json}\n```"
    
    res = send_telegram_message(msg_text)
    msg_id = res.get("result", {}).get("message_id")
    
    if msg_id:
        pin_url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_TOKEN}/pinChatMessage"
        requests.post(pin_url, data={"chat_id": TELEGRAM_CHAT_ID, "message_id": msg_id}, timeout=10)

# --- INTERACTIVE WIZARD & COMMANDS ---

def process_telegram_commands(db: dict) -> dict:
    updates = get_telegram_updates()
    if not updates:
        return db

    updated = False
    step = db.get("wizard_step")
    temp = db.get("temp_data", {})
    targets = db.get("targets", [])

    for item in updates:
        message = item.get("message", {})
        text = message.get("text", "").strip()

        if not text:
            continue

        # Cancel flow anytime
        if text.lower() == "/cancel":
            step = None
            temp = {}
            send_telegram_message("🚫 Step-by-step process cancelled.")
            updated = True
            continue

        # 1. Start Step-by-Step Addition
        if text.lower() == "/add" and step is None:
            # Check if one-line add was attempted
            step = "WAITING_MOVIE"
            temp = {}
            send_telegram_message("🎬 *Step 1/4:* Please reply with the *Movie Name* (e.g., `Coolie`):")
            updated = True
            continue

        # 2. Wizard Flow Logic
        if step == "WAITING_MOVIE":
            temp["movie"] = text
            step = "WAITING_DATE"
            send_telegram_message("📅 *Step 2/4:* Please reply with the *Show Date* (e.g., `2026-08-10`):")
            updated = True
            continue

        elif step == "WAITING_DATE":
            temp["date"] = text
            step = "WAITING_URL"
            send_telegram_message("🔗 *Step 3/4:* Please reply with the *BookMyShow Ticket URL*:")
            updated = True
            continue

        elif step == "WAITING_URL":
            # Strip markdown links if auto-formatted by Telegram
            clean_url = text.replace("[", "").replace("]", "").split("(")[-1].replace(")", "")
            temp["url"] = clean_url
            step = "WAITING_KEYWORD"
            send_telegram_message("🔑 *Step 4/4:* Please reply with the *Search Keyword* (e.g., `Coolie`):")
            updated = True
            continue

        elif step == "WAITING_KEYWORD":
            temp["keyword"] = text
            targets.append(temp.copy())
            send_telegram_message(f"✅ *Success!* Added *{temp['movie']}* to your watchlist!")
            step = None
            temp = {}
            updated = True
            continue

        # 3. Handle /list
        if text.lower() == "/list":
            if not targets:
                send_telegram_message("📁 *Watchlist is empty.*")
            else:
                msg = "🎬 *Current Monitored Movies:*\n\n"
                for idx, t in enumerate(targets, 1):
                    msg += f"{idx}. *{t['movie']}* ({t['date']})\n🔗 `{t['url']}`\n\n"
                send_telegram_message(msg)

        # 4. Handle /del
        elif text.lower().startswith("/del "):
            movie_to_del = text[5:].strip().lower()
            initial_count = len(targets)
            targets = [t for t in targets if t["movie"].lower() != movie_to_del]
            if len(targets) < initial_count:
                send_telegram_message(f"🗑️ Removed *{movie_to_del}* from watchlist!")
                updated = True
            else:
                send_telegram_message(f"⚠️ Movie *{movie_to_del}* not found.")

    db["targets"] = targets
    db["wizard_step"] = step
    db["temp_data"] = temp

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
    start_time_utc = datetime.utcnow()

    # Load database & process step-by-step messages
    db = get_db_state()
    db = process_telegram_commands(db)

    targets = db.get("targets", [])
    if not targets:
        print("[!] No active targets to check.")
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
        time.sleep(random.uniform(2, 4))
        try:
            response = requests.get(
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
                    f"*Date:* {target['date']}\n\n"
                    f"👉 [Book Now]({target['url']})"
                )
                send_telegram_message(msg)
                print(f"[+] Bookings open for {target['movie']}!")
            else:
                print(f"[-] No showtimes for {target['movie']}.")

        except Exception as e:
            print(f"[!] Error checking {target['movie']}: {e}")

if __name__ == "__main__":
    check_availability()
