import os
import time
import random
from datetime import datetime, timedelta
from curl_cffi import requests

# Secrets from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

# Targets to check
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
    """Sends notification to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID.")
        return

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(telegram_url, data=payload, timeout=10)
    except Exception as e:
        print(f"[!] Failed to send Telegram alert: {e}")

def test_proxy(proxies: dict) -> tuple[bool, str]:
    """Tests if the proxy is functioning and returns the exit IP."""
    try:
        # Request IP echo service through the proxy
        res = requests.get(
            "https://api.ipify.org?format=json",
            proxies=proxies,
            impersonate="chrome124",
            timeout=10
        )
        if res.status_code == 200:
            ip = res.json().get("ip", "Unknown IP")
            return True, ip
    except Exception as e:
        return False, str(e)
    return False, f"HTTP {res.status_code}"

def check_availability() -> None:
    """Checks ticket availability with proxy testing and 10-min schedule logic."""
    start_time_utc = datetime.utcnow()
    next_check_utc = start_time_utc + timedelta(minutes=10)
    
    start_str = start_time_utc.strftime("%H:%M:%S UTC")
    next_str = next_check_utc.strftime("%H:%M:%S UTC")

    print(f"--- Running BookMyShow Check at {start_str} ---")

    # Configure Proxy
    proxies = None
    proxy_status_msg = "No proxy configured (using Runner IP)."
    
    if PROXY_URL:
        formatted_proxy = PROXY_URL if PROXY_URL.startswith("http") else f"http://{PROXY_URL}"
        proxies = {
            "http": formatted_proxy,
            "https": formatted_proxy,
        }
        
        # --- PROXY HEALTH CHECK HINT ---
        is_working, ip_or_error = test_proxy(proxies)
        if is_working:
            proxy_status_msg = f"✅ Proxy Active | Exit IP: `{ip_or_error}`"
            print(f"[+] Proxy Test Passed! Exit IP: {ip_or_error}")
        else:
            proxy_status_msg = f"❌ Proxy Failed! Error: `{ip_or_error}`"
            print(f"[!] Proxy Test Failed: {ip_or_error}")
    else:
        print("[!] Warning: PROXY_URL not set in secrets.")

    # 1. Send Start Notification with Proxy Status
    startup_msg = (
        f"🤖 *BookMyShow Monitor Started*\n\n"
        f"🕒 *Current Check:* `{start_str}`\n"
        f"⏳ *Next Check:* `{next_str}`\n"
        f"🌐 *Proxy Status:* {proxy_status_msg}\n\n"
        f"🔍 *Status:* Checking targets now..."
    )
    send_telegram_message(startup_msg)

    # Browser Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Referer": "https://in.bookmyshow.com/",
    }

    found_any = False
    blocked_any = False

    for target in TARGETS:
        time.sleep(random.uniform(2, 5))

        try:
            response = requests.get(
                target["url"],
                headers=headers,
                impersonate="chrome124",
                proxies=proxies,
                timeout=20
            )

            print(f"[*] Response for {target['movie']}: HTTP {response.status_code}")

            if response.status_code == 200:
                if target["keyword"].lower() in response.text.lower():
                    found_any = True
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

            elif response.status_code in (403, 429, 503):
                blocked_any = True
                print(f"[!] HTTP {response.status_code} Blocked for {target['movie']}.")

        except Exception as e:
            print(f"[!] Error checking {target['movie']}: {e}")

    # Send status summary if blocked
    if blocked_any and not found_any:
        summary_msg = (
            f"⚠️ *Check Completed (Blocked - HTTP 403)*\n\n"
            f"The site returned 403 Forbidden.\n"
            f"🕒 *Next Check:* `{next_str}`"
        )
        send_telegram_message(summary_msg)

if __name__ == "__main__":
    check_availability()
