import os
import re
import requests
import dotenv

dotenv.load_dotenv()

def send_job_alerts(matched_jobs: list):
    raw_token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or ""

    # Strip whitespace, quotes, and accidental "bot" prefixes
    token = raw_token.strip().strip("'").strip('"')
    if token.lower().startswith("bot"):
        token = token[3:]

    chat_id = chat_id.strip().strip("'").strip('"')

    if not token or not chat_id:
        print("⚠️ Telegram credentials missing. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for job in matched_jobs:
        title = job.get("title")
        company = job.get("company")
        location = job.get("location")
        job_url = job.get("url")
        fit_score = job.get("fit_score")
        match_reason = job.get("match_reason")

        message = (
            f"🎯 *NEW FRESHER JOB MATCH!*\n\n"
            f"📌 *Role:* {title}\n"
            f"🏢 *Company:* {company}\n"
            f"📍 *Location:* {location}\n"
            f"⚡ *Fit Score:* {fit_score}%\n"
            f"💡 *Reasons:* {match_reason}\n\n"
            f"🔗 [Apply Here]({job_url})"
        )

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                print(f"✅ Telegram alert sent: {title} @ {company}")
            else:
                print(f"❌ Telegram Error ({resp.status_code}): {resp.text}")
                print(f"   [Debug URL Used]: https://api.telegram.org/bot{token[:5]}.../sendMessage")
        except Exception as e:
            print(f"❌ Notification Error: {e}")
