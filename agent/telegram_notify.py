import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(title: str, company: str, location: str, url: str, score: int, reason: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram Debug] Credentials missing from .env context.")
        return False

    message = f"""🎯 *NEW ENTRY-LEVEL DE MATCH*

🏢 *Company:* {company}
📌 *Role:* {title}
📍 *Location:* {location}
⭐ *Match Score:* {score}/100
💡 *Reason:* {reason}

🔗 [View Job Posting]({url})"""

    endpoint = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        res = requests.post(endpoint, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"Telegram notification sent for {title} at {company}")
            return True
        else:
            print(f"Telegram API Error ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"[Telegram Exception] {e}")
        return False
