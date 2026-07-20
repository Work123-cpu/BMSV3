import os
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Target movies and show dates at Broadway Cinemas, Coimbatore
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

def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def check_availability():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for target in TARGETS:
        try:
            response = requests.get(target["url"], headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                page_text = soup.get_text()
                
                if target["keyword"].lower() in page_text.lower():
                    msg = f"🚨 *BOOKINGS OPEN!* 🚨\n\n*Movie:* {target['movie']}\n*Date:* {target['date']}\n*Venue:* Broadway Cinemas, Coimbatore\n\n👉 [Book Now]({target['url']})"
                    print(f"Match found for {target['movie']}!")
                    send_telegram_alert(msg)
                else:
                    print(f"Not open yet: {target['movie']} ({target['date']})")
            else:
                print(f"Failed to fetch page for {target['movie']}, HTTP status: {response.status_code}")
        except Exception as e:
            print(f"Error checking {target['movie']}: {e}")

if __name__ == "__main__":
    check_availability()
