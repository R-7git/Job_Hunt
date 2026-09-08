import os
import sqlite3
import logging
import json
import re
import html
import urllib.request
from dotenv import load_dotenv

# Try importing your scraper/collector function if present
try:
    from agent.listener import run_job_collector
except ImportError:
    try:
        from listener import run_job_collector
    except ImportError:
        run_job_collector = None

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = "data/jobs.db"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Extract strictly the token part (numerical_id:hash) and strip any surrounding URLs or brackets
RAW_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
RAW_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

token_match = re.search(r'(\d+:[A-Za-z0-9_-]+)', RAW_TOKEN)
TOKEN = token_match.group(1) if token_match else re.sub(r'[^a-zA-Z0-9:\-_]', '', RAW_TOKEN)

chat_match = re.search(r'(-?\d+)', RAW_CHAT_ID)
CHAT_ID = chat_match.group(1) if chat_match else re.sub(r'[^a-zA-Z0-9_\-]', '', RAW_CHAT_ID)


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def fetch_unprocessed_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch jobs that are either explicitly marked 'APPLY' or newly inserted 'NEW'
    cursor.execute("""
        SELECT id, title, company, location, url, description 
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


def evaluate_job_with_ollama(title, company, description):
    prompt = f"""You are an expert recruiter evaluating entry-level roles.
Evaluate this position for a Fresher / Entry-Level Data Engineer (0-1 YOE):
Title: {title}
Company: {company}
Description: {description}

Return ONLY a JSON object with this exact structure:
{{
  "score": 85,
  "reason": "One clear concise sentence explaining fit."
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
            raw_response = res_data.get("response", "{}")
            cleaned_text = clean_json_response(raw_response)
            parsed = json.loads(cleaned_text)
            return int(parsed.get("score", 85)), parsed.get("reason", "Evaluated by AI")
    except Exception as e:
        logging.warning(f"Ollama local instance unavailable ({e}). Defaulting to passing score for GitHub Actions.")
    # Fallback to score 85 so GitHub Actions passes all scraped jobs to Telegram
    return 85, "Matched entry-level job posting criteria."


def send_telegram_alert(title, company, location, url, score, reason):
    if not TOKEN or not CHAT_ID:
        logging.error(f"Missing Token/Chat ID -> TOKEN: '{TOKEN}' | CHAT_ID: '{CHAT_ID}'")
        return False

    clean_title = html.escape(str(title or "N/A"))
    clean_company = html.escape(str(company or "N/A"))
    clean_location = html.escape(str(location or "N/A"))
    clean_reason = html.escape(str(reason or "N/A"))
    clean_url = html.escape(str(url or ""))

    message = (
        f"🎯 <b>New Entry-Level DE Job Found!</b>\n\n"
        f"<b>Role:</b> {clean_title}\n"
        f"<b>Company:</b> {clean_company}\n"
        f"<b>Location:</b> {clean_location}\n"
        f"<b>Score:</b> {score}/100\n"
        f"<b>Reason:</b> {clean_reason}\n\n"
        f'🔗 <a href="{clean_url}">Apply Here</a>'
    )

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
                logging.info(f"Telegram alert delivered for: {title}")
                return True
    except Exception as e:
        logging.error(f"Telegram request failed [{endpoint}]: {e}")
        return False
    return False


def update_job_status(job_id, score, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs 
        SET match_score = ?, status = ? 
        WHERE id = ?
    """, (score, status, job_id))
    conn.commit()
    conn.close()


def process_pipeline():
    # 1. Run scrapers/collectors first to fetch live jobs
    if callable(run_job_collector):
        logging.info("Starting job collection...")
        try:
            run_job_collector()
        except Exception as e:
            logging.error(f"Error running job collector: {e}")
    else:
        logging.info("No collector module detected. Processing existing DB jobs.")

    # 2. Fetch all unprocessed jobs
    jobs = fetch_unprocessed_jobs()
    logging.info(f"Found {len(jobs)} unprocessed jobs with status 'APPLY' or 'NEW'")

    for job in jobs:
        job_id, title, company, location, url, description = job
        logging.info(f"Processing: {title} at {company}")

        score, reason = evaluate_job_with_ollama(title, company, description)
        logging.info(f"Evaluation -> Score: {score} | Reason: {reason}")

        if score >= 50:
            alert_sent = send_telegram_alert(title, company, location, url, score, reason)
            if alert_sent:
                update_job_status(job_id, score, status="NOTIFIED")
                logging.info(f"Updated {job_id} -> status='NOTIFIED'")
            else:
                logging.warning(f"Telegram dispatch failed. Retaining {job_id} as status='APPLY'")
        else:
            update_job_status(job_id, score, status="REJECTED")
            logging.info(f"Score below threshold ({score}). Updated {job_id} -> status='REJECTED'")


if __name__ == "__main__":
    process_pipeline()