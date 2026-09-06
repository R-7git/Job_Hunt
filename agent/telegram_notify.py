import os
import requests
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(title: str, company: str, location: str, url: str, score: int, reason: str):
    if not TELEGRAM_TOKEN or "YOUR_BOT_TOKEN" in TELEGRAM_TOKEN:
        print("Telegram alert skipped: Bot credentials not configured.")
        return

    message = f"""🎯 *NEW ENTRY-LEVEL DE MATCH*

📌 *Role:* {title}
🏢 *Company:* {company}
📍 *Location:* {location}
📊 *Match Score:* {score}/100

💡 *LLM Reason:* {reason}

🔗 [Apply Here]({url})
📂 *Document:* Application package generated in `/applications`
"""
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"Telegram notification sent for {title} at {company}")
            return True
        else:
            print(f"Telegram API Error ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False
