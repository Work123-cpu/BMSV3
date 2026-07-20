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

# --- TELEGRAM HELPER FUNCTIONS ---

def send_telegram_message(message: str) -> dict:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID.")
        return {}

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
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

# --- DATABASE / STATE MANAGEMENT (Telegram Pinned Message) ---

def get_db_state() -> dict:
    """Retrieves targets, wizard state, and last_update_id from pinned message."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getChat"
    default_state = {
        "targets": [
            {
                "movie": "Jana Nayagan",
                "date": "2026-07-24",
                "url": "https://in.bookmyshow.com/buytickets/broadway-cinemas-coimbatore/cinema-coim-BWCC-MT/20260724",
                "keyword": "Jana Nayagan"
            }
        ],
        "wizard_step": None,
        "temp_data": {},
        "last_update_id": 0
    }
    
    try:
        res = requests.post(url, data={"chat_id": str(TELEGRAM_CHAT_ID).strip()}, timeout=10)
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
        payload = {
            "chat_id": str(TELEGRAM_CHAT_ID).strip(),
            "message_id": int(msg_id)
        }
        requests.post(pin_url, data=payload, timeout=10)

# --- INTERACTIVE WIZARD & COMMANDS ---

def process_telegram_commands(db: dict) -> dict:
    last_id = db.get("last_update_id", 0)
    updates = get_telegram_updates(offset=last_id + 1 if last_id else None)
    
    if not updates:
        return db

    updated = False
    step = db.get("wizard_step")
    temp = db.get("temp_data", {})
    targets = db.get("targets", [])

    for item in updates:
        update_id = item.get("update_id")
        if update_id:
            db["last_update_id"] = max(db.get("last_update_id", 0), update_id)
            updated = True

        message = item.get("message", {})
        text = message.get("text", "").strip()

        if not text:
            continue

        # Cancel command
        if text.lower() == "/cancel":
            step = None
            temp = {}
            send_telegram_message("🚫 Step-by-step process cancelled.")
            continue

        # Step 0: Initiate /add
        if text.lower() == "/add" and step is None:
            step = "WAITING_MOVIE"
            temp = {}
            send_telegram_message("🎬 *Step 1/4:* Reply with the *Movie Name* (e.g., `Coolie`):")
            continue

        # Wizard Steps
        if step == "WAITING_MOVIE":
            temp["movie"] = text
            step = "WAITING_DATE"
            send_telegram_message("📅 *Step 2/4:* Reply with the *Show Date* (e.g., `2026-08-10`):")
            continue

        elif step == "WAITING_DATE":
            temp["date"] = text
            step = "WAITING_URL"
            send_telegram_message("🔗 *Step 3/4:* Reply with the *BookMyShow Ticket URL*:")
            continue

        elif step == "WAITING_URL":
            clean_url = text.replace("[", "").replace("]", "").split("(")[-1].replace(")", "").strip()
            temp["url"] = clean_url
            step = "WAITING_KEYWORD"
            send_telegram_message("🔑 *Step 4/4:* Reply with the *Search Keyword* (e.g., `Coolie`):")
            continue

        elif step == "WAITING_KEYWORD":
            temp["keyword"] = text
            targets.append(temp.copy())
            send_telegram_message(f"✅ *Success!* Added *{temp['movie']}* to your watchlist!")
            step = None
            temp = {}
            continue

        # Handle /list
        if text.lower() == "/list":
            if not targets:
                send_telegram_message("📁 *Watchlist is empty.*")
            else:
                msg = "🎬 *Current Monitored Movies:*\n\n"
                for idx, t in enumerate(targets, 1):
                    msg += f"{idx}. *{t['movie']}* ({t['date']})\n🔗 `{t['url']}`\n\n"
                send_telegram_message(msg)

        # Handle /del
        elif text.lower().startswith("/del "):
            movie_to_del = text[5:].strip().lower()
            initial_count = len(targets)
            targets = [t for t in targets if t["movie"].lower() != movie_to_del]
            if len(targets) < initial_count:
                send_telegram_message(f"🗑️ Removed *{movie_to_del}* from watchlist!")
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
        time.sleep(random.uniform(1, 3))
        try:
            # Uses cffi_requests specifically for Cloudflare bypass on BookMyShow
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
