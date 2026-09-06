import os
import sys
import sqlite3
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.job_matcher import clean_html

DB_PATH = "data/jobs.db"
OUTPUT_DIR = "applications"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(title, company, score, match_reason, url, file_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"Telegram credentials not configured. Skipping alert for {title}.")
        return False

    message = (
        f"🎯 *New Entry-Level Job Match!*\n\n"
        f"🏢 *Company:* {company}\n"
        f"📌 *Role:* {title}\n"
        f"⭐ *Score:* {score}/100\n"
        f"💡 *Reason:* {match_reason}\n\n"
        f"🔗 [Apply Here]({url})\n"
        f"📄 Materials generated at `{file_path}`"
    )

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        res = requests.post(telegram_url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")
        return False

def generate_tailored_materials(title, company, description):
    clean_desc = clean_html(description)
    
    cover_letter = f"""
Dear Hiring Manager at {company},

I am writing to express my strong interest in the {title} position. With a solid foundation in Python, SQL, Snowflake, and building robust ETL pipelines, I am eager to contribute to your data engineering team.

My technical experience aligns directly with designing data workflows, managing data transformations using dbt and SQL, and maintaining reliable data pipelines. I am excited about the opportunity to bring my hands-on knowledge and enthusiasm for data engineering to {company}.

Thank you for your time and consideration.

Best regards,
Candidate
"""

    key_points = [
        f"Tailored for {title} at {company}",
        "Highlighted Skills: Python, SQL, Snowflake, ETL/ELT Pipelines, dbt",
        "Focused on data pipeline reliability, clean data modeling, and entry-level execution."
    ]

    content = f"# Application Materials: {title} at {company}\n\n"
    content += "## Target Focus Points\n"
    for pt in key_points:
        content += f"- {pt}\n"
    content += "\n## Tailored Cover Letter\n"
    content += cover_letter

    return content

def process_applications():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sqlite3.connect(DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        
        # Only query jobs waiting to be applied/notified
        cursor.execute("""
            SELECT id, title, company, location, url, description, match_score, match_reason
            FROM jobs
            WHERE status = 'APPLY'
        """)
        jobs = cursor.fetchall()

        if not jobs:
            print("No new jobs requiring application tailoring.")
            return

        print(f"Found {len(jobs)} new job(s) ready for application tailoring...")

        for job in jobs:
            job_id, title, company, loc, url, desc, score, reason = job

            safe_company = "".join(c for c in company if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            file_name = f"{safe_company}_{safe_title}.md"
            file_path = os.path.join(OUTPUT_DIR, file_name)

            materials = generate_tailored_materials(title, company, desc)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(materials)

            print(f"Saved tailored materials to: {file_path}")

            # Send Telegram Alert
            sent = send_telegram_alert(title, company, score, reason, url, file_path)
            if sent:
                print(f"Telegram notification sent for {title} at {company}")

            # UPDATE STATUS to 'NOTIFIED' so it's never processed again
            cursor.execute("UPDATE jobs SET status = 'NOTIFIED' WHERE id = ?", (job_id,))
            conn.commit()

if __name__ == "__main__":
    process_applications()
