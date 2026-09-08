import os
import requests
import dotenv

dotenv.load_dotenv()

def send_job_alerts(matched_jobs: list) -> list:
    raw_token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or ""

    token = raw_token.strip().strip("'").strip('"')
    if token.lower().startswith("bot"):
        token = token[3:]

    chat_id = chat_id.strip().strip("'").strip('"')

    if not token or not chat_id:
        print("⚠️ Telegram credentials missing or invalid in .env file.")
        return []

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    successful_ids = []

    for job in matched_jobs:
        job_id = job.get("id")
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
                print(f"✅ Telegram alert delivered: {title} @ {company}")
                successful_ids.append(job_id)
            else:
                print(f"❌ Telegram Delivery Error ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"❌ Notification Request Exception: {e}")

    return successful_ids
