import sqlite3
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.job_matcher import evaluate_job_match

DB_PATH = os.getenv("DB_PATH", "data/jobs.db")

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

def process_collected_jobs(job_list):
    """
    Processes a list of job dicts:
    [
        {
            "id": "...",
            "title": "...",
            "company": "...",
            "location": "...",
            "url": "...",
            "description": "..."
        },
        ...
    ]
    """
    init_db()
    
    DATA_ROLE_KEYWORDS = ["data engineer", "data engineering", "analytics engineer", "etl engineer", "database engineer"]

    for job in job_list:
        job_id = job.get("id")
        title = job.get("title", "")
        company = job.get("company", "")
        location = job.get("location", "")
        url = job.get("url", "")
        description = job.get("description", "")

        title_lower = title.lower()

        # Filter out non-DE roles
        if not any(kw in title_lower for kw in DATA_ROLE_KEYWORDS):
            continue

        # Filter out senior roles
        if any(kw in title_lower for kw in ["senior", "sr.", "sr ", "staff", "principal", "lead", "manager"]):
            continue

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
            if cursor.fetchone():
                continue

            score, reason = evaluate_job_match(title, description)

            if score < 60:
                print(f"  [DISCARDED] '{title}' at {company} (Score: {score}/100 - {reason})")
                continue

            cursor.execute("""
                INSERT INTO jobs (id, title, company, location, url, description, match_score, match_reason, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPLY')
            """, (job_id, title, company, location, url, description, score, reason))
            conn.commit()
            print(f"  --> Saved '{title}' at {company} (Score: {score}/100)")

if __name__ == "__main__":
    init_db()
    print("Job collector initialized.")
