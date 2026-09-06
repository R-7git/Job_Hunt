import sqlite3
import requests
import re
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.job_matcher import evaluate_job_match, clean_html

DB_PATH = "data/jobs.db"

TARGET_BOARDS = {
    "greenhouse": [
        "https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true"
    ],
    "ashby": [
        "https://api.ashbyhq.com/posting-api/job-board/openai",
        "https://api.ashbyhq.com/posting-api/job-board/linear"
    ]
}

DATA_ROLE_KEYWORDS = [
    "data engineer", "data engineering", "analytics engineer", "etl engineer", "database engineer"
]


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                url TEXT,
                description TEXT,
                match_score INTEGER,
                match_reason TEXT,
                status TEXT DEFAULT 'NEW'
            )
        """)
        conn.commit()


def is_valid_experience(description: str) -> bool:
    clean_text = clean_html(description)

    # Catch senior experience requirements
    senior_exp = re.search(r'(\b[3-9]|\b1[0-9])\+?\s*years?', clean_text, re.IGNORECASE)
    if senior_exp:
        # Pass early career ranges
        if re.search(r'\b(0|1|2)\s*[-–to]+\s*[1-3]\s*years?', clean_text, re.IGNORECASE) or \
                re.search(r'([<⩽]=?\s*[1-2]\s*years?)', clean_text, re.IGNORECASE):
            return True
        return False

    return True


def process_and_save_job(job_id, title, company, location, url, description):
    title_lower = title.lower()

    # Title Check
    if not any(kw in title_lower for kw in DATA_ROLE_KEYWORDS):
        return

    # Seniority Title Check
    if any(kw in title_lower for kw in ["senior", "sr.", "sr ", "staff", "principal", "lead", "manager"]):
        return

    # Deterministic Experience Check
    if not is_valid_experience(description):
        return

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
        if cursor.fetchone():
            return

        score, reason = evaluate_job_match(title, description)

        if score < 60:
            print(f"  [DISCARDED] '{title}' at {company} (Score: {score}/100 - {reason})")
            return

        cursor.execute("""
            INSERT INTO jobs (id, title, company, location, url, description, match_score, match_reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPLY')
        """, (job_id, title, company, location, url, description, score, reason))
        conn.commit()
        print(f"  --> Saved '{title}' at {company} (Score: {score}/100)")


def scan_greenhouse():
    print("\n--- Scanning Direct Greenhouse Endpoints ---")
    for endpoint in TARGET_BOARDS["greenhouse"]:
        try:
            res = requests.get(endpoint, timeout=10)
            if res.status_code == 200:
                jobs = res.json().get("jobs", [])
                company = endpoint.split("/")[-2].capitalize()
                for job in jobs:
                    title = job.get("title", "")
                    job_id = f"gh_{job.get('id')}"
                    loc = job.get("location", {}).get("name", "Remote")
                    url = job.get("absolute_url", "")
                    desc = job.get("content", "")
                    process_and_save_job(job_id, title, company, loc, url, desc)
        except Exception as e:
            print(f"Error scanning Greenhouse endpoint {endpoint}: {e}")


def scan_ashby():
    print("\n--- Scanning Direct Ashby Endpoints ---")
    for endpoint in TARGET_BOARDS["ashby"]:
        try:
            res = requests.get(endpoint, timeout=10)
            if res.status_code == 200:
                jobs = res.json().get("jobs", [])
                company = endpoint.split("/")[-1].capitalize()
                for job in jobs:
                    title = job.get("title", "")
                    job_id = f"ashby_{job.get('id')}"
                    loc = job.get("location", "Remote")
                    url = job.get("jobUrl", "")
                    desc = job.get("descriptionHtml", "")
                    process_and_save_job(job_id, title, company, loc, url, desc)
        except Exception as e:
            print(f"Error scanning Ashby endpoint {endpoint}: {e}")


def run_ats_collector():
    init_db()
    scan_greenhouse()
    scan_ashby()


if __name__ == "__main__":
    run_ats_collector()