import os
import sys
import sqlite3
import logging
import json
import re
import html
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from agent.listener import run_job_collector
except ImportError:
    try:
        from listener import run_job_collector
    except ImportError:
        run_job_collector = None

load_dotenv(ROOT_DIR / ".env", override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = ROOT_DIR / "data" / "jobs.db"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

RAW_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
RAW_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

token_match = re.search(r'(\d+:[A-Za-z0-9_-]+)', RAW_TOKEN)
TOKEN = token_match.group(1) if token_match else RAW_TOKEN.strip("[]'\"")

chat_match = re.search(r'(-?\d+)', RAW_CHAT_ID)
CHAT_ID = chat_match.group(1) if chat_match else RAW_CHAT_ID.strip("[]'\"")


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Ensure table has AUTOINCREMENT Primary Key and UNIQUE constraint on url."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT UNIQUE,
            description TEXT,
            source TEXT,
            match_score INTEGER,
            match_reason TEXT,
            status TEXT DEFAULT 'NEW',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def fetch_unprocessed_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(id, rowid), title, company, location, url, description 
        FROM jobs 
        WHERE status IN ('APPLY', 'NEW')
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def clean_json_response(text):
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```$', '', text, flags=re.MULTILINE)
    return text.strip()


def evaluate_job_with_ollama(title, company, location, description):
    prompt = f"""You are an expert tech recruiter evaluating entry-level/fresher roles for a candidate based in Bengaluru, India.
Evaluate this job position according to these EXACT criteria:
1. Target Roles: Data Engineer, ETL Developer, Snowflake Developer, SQL Developer (0-2 YOE max).
2. Location Filter: MUST be Pure Remote, Remote (India), Remote (Worldwide), or located in Bengaluru/Bangalore.
3. Exclusions: On-site or hybrid roles located in US (e.g. New York, NY), EU, or outside India MUST score 0.

Role Details:
- Title: {title}
- Company: {company}
- Location: {location}
- Description: {description}

Return ONLY a JSON object with this exact structure:
{{
  "score": 85,
  "is_remote_eligible": true,
  "reason": "One clear concise sentence explaining role fit and location eligibility."
}}
"""
    try:
        data = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }).encode('utf-8')

        req = urllib.request.Request(OLLAMA_URL, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            cleaned_text = clean_json_response(res_data.get("response", "{}"))
            parsed = json.loads(cleaned_text)
            return int(parsed.get("score", 0)), parsed.get("reason", "Evaluated by AI")
    except Exception as e:
        logging.warning(f"Local Ollama instance unavailable ({e}). Running rule-based fallback evaluation.")

    # Rule-Based Engine (Bengaluru Candidate Focus)
    title_lower = (title or "").lower()
    loc_lower = (location or "").lower()

    valid_roles = ["data engineer", "etl", "snowflake", "sql", "data platform", "pipeline"]
    valid_locations = ["remote", "anywhere", "worldwide", "india", "work from home", "bengaluru", "bangalore"]
    invalid_locations = ["new york", "ny", "san francisco", "london", "uk", "us", "united states", "hybrid"]

    matches_role = any(r in title_lower for r in valid_roles)
    is_disqualified_location = any(loc in loc_lower for loc in invalid_locations) and not any(r in loc_lower for r in ["remote", "india"])
    matches_valid_location = any(l in loc_lower for l in valid_locations)

    if matches_role and matches_valid_location and not is_disqualified_location:
        return 85, "Matched target remote/Bengaluru DE/ETL/SQL fresher criteria."
    elif matches_role:
        return 0, "Rejected: Role matches, but location is non-remote or based outside target region (e.g., NY/US)."

    return 0, "Rejected: Role does not match Data Engineering / ETL / SQL focus."


def send_telegram_alert(job_id, title, company, location, url, score, reason):
    if not TOKEN or not CHAT_ID:
        logging.error(f"Missing Credentials -> TOKEN: '{TOKEN}' | CHAT_ID: '{CHAT_ID}'")
        return False

    clean_title = html.escape(str(title or "N/A"))
    clean_company = html.escape(str(company or "N/A"))
    clean_location = html.escape(str(location or "N/A"))
    clean_reason = html.escape(str(reason or "N/A"))
    clean_url = html.escape(str(url or ""))

    message = (
        f"🎯 <b>New Job Match Found!</b>\n\n"
        f"<b>Job ID:</b> #{job_id}\n"
        f"<b>Role:</b> {clean_title}\n"
        f"<b>Company:</b> {clean_company}\n"
        f"<b>Location:</b> {clean_location}\n"
        f"<b>Score:</b> {score}/100\n"
        f"<b>Reason:</b> {clean_reason}\n\n"
        f'🔗 <a href="{clean_url}">Apply Here</a>'
    )

    # Pure endpoint string without markdown wrappers
    endpoint = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }).encode('utf-8')

    try:
        req = urllib.request.Request(endpoint, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                logging.info(f"Telegram alert delivered for Job #{job_id}: {title}")
                return True
    except Exception as e:
        logging.error(f"Telegram request failed for Job #{job_id}: {e}")
        return False
    return False


def update_job_eval(job_id, score, reason, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs 
        SET match_score = ?, match_reason = ?, status = ? 
        WHERE COALESCE(id, rowid) = ?
    """, (score, reason, status, job_id))
    conn.commit()
    conn.close()


def process_pipeline():
    init_db()

    if callable(run_job_collector):
        logging.info("Starting job collection step...")
        try:
            run_job_collector()
        except Exception as e:
            logging.error(f"Error executing job collector: {e}")

    jobs = fetch_unprocessed_jobs()
    logging.info(f"Found {len(jobs)} unprocessed jobs with status 'APPLY' or 'NEW'")

    for job in jobs:
        job_id, title, company, location, url, description = job
        logging.info(f"Processing Job #{job_id}: {title} at {company} ({location})")

        score, reason = evaluate_job_with_ollama(title, company, location, description)
        logging.info(f"Evaluation -> Score: {score} | Reason: {reason}")

        if score >= 60:
            alert_sent = send_telegram_alert(job_id, title, company, location, url, score, reason)
            if alert_sent:
                update_job_eval(job_id, score, reason, status="NOTIFIED")
                logging.info(f"Updated job #{job_id} -> status='NOTIFIED', match_score={score}")
            else:
                update_job_eval(job_id, score, reason, status="APPLY")
                logging.warning(f"Telegram dispatch failed. Saved score={score} and retained job #{job_id} as status='APPLY'")
        else:
            update_job_eval(job_id, score, reason, status="REJECTED")
            logging.info(f"Score below threshold ({score}). Updated job #{job_id} -> status='REJECTED', match_score={score}")


if __name__ == "__main__":
    process_pipeline()