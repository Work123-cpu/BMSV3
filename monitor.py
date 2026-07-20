import os
import time
import random
from datetime import datetime
import cloudscraper

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
    """Utility function to push any log or alert to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests_response = cloudscraper.create_scraper().post(url, data=payload, timeout=10)
        if requests_response.status_code != 200:
            print(f"[!] Telegram API error: {requests_response.status_code}")
    except Exception as e:
        print(f"[!] Failed to send Telegram message: {e}")

def check_availability():
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"--- Running BookMyShow Check at {now} ---")

    status_summary = []

    for target in TARGETS:
        # Add random jitter (3 to 8 seconds delay) to prevent predictable traffic patterns
        time.sleep(random.uniform(3, 8))

        try:
            response = scraper.get(target["url"], timeout=15)
            
            if response.status_code == 200:
                page_text = response.text
                
                if target["keyword"].lower() in page_text.lower():
                    # 🚨 HIGH PRIORITY: Tickets found!
                    alert_msg = (
                        f"🚨 *BOOKINGS OPEN!* 🚨\n\n"
                        f"*Movie:* {target['movie']}\n"
                        f"*Date:* {target['date']}\n"
                        f"*Venue:* Broadway Cinemas, Coimbatore\n\n"
                        f"👉 [Book Now]({target['url']})"
                    )
                    send_telegram_message(alert_msg)
                    status_summary.append(f"✅ {target['movie']}: OPEN!")
                else:
                    print(f"[-] {target['movie']} not open yet.")
                    status_summary.append(f"⏳ {target['movie']}: Not open")

            elif response.status_code in [403, 429, 503]:
                # ⚠️ WARNING: Blocked or rate-limited by Cloudflare
                err_msg = f"⚠️ *Rate Limit / Block Detected!* HTTP {response.status_code} for {target['movie']}."
                print(err_msg)
                send_telegram_message(err_msg)
                status_summary.append(f"❌ {target['movie']}: Blocked ({response.status_code})")
            else:
                print(f"[!] Unexpected status code {response.status_code} for {target['movie']}")
                status_summary.append(f"⚠️ {target['movie']}: HTTP {response.status_code}")

        except Exception as e:
            err_msg = f"❌ *Error checking {target['movie']}:* `{str(e)}`"
            print(err_msg)
            send_telegram_message(err_msg)
            status_summary.append(f"❌ {target['movie']}: Exception occurred")

    # Optional: Send a summary heart-beat log once every few hours or at specific times (e.g. 09:00 UTC)
    # If you want a message on EVERY run, uncomment the line below:
    # send_telegram_message(f"ℹ️ *Status Check ({now}):*\n" + "\n".join(status_summary))

if __name__ == "__main__":
    check_availability()
