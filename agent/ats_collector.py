import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
import sqlite3
from agent.job_matcher import evaluate_job_with_ai

DB_PATH = "data/jobs.db"

GREENHOUSE_COMPANIES = ["gitlab", "stripe", "airtable", "coinbase"]
LEVER_COMPANIES = ["postman", "vercel", "palantir", "figma"]
ASHBY_COMPANIES = ["notion", "ramp", "replit", "linear", "openai"]
WORKABLE_COMPANIES = ["sentry", "monzo", "cloudflare"]

TARGET_DATA_KEYWORDS = [
    "data engineer", "data engineering", "etl developer", "etl engineer",
    "snowflake developer", "snowflake engineer", "analytics engineer",
    "junior data engineer", "entry level data engineer", "associate data engineer"
]

EXCLUDE_TITLES = [
    "senior", "sr", "sr.", "staff", "principal", "lead", "manager", "director",
    "head of", "architect", "account executive", "sales", "recruiter", "vp",
    "iii", "iv", "v"
]

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                url TEXT,
                description TEXT,
                source TEXT,
                match_score INTEGER,
                match_reason TEXT,
                status TEXT DEFAULT 'APPLY'
            )
        """)
        conn.commit()

def is_job_saved(job_id):
    with sqlite3.connect(DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE id = ?", (str(job_id),))
        return cursor.fetchone() is not None

def save_job(job_id, title, company, location, url, description, source):
    # GUARANTEE: Skip immediately if job is already present in DB
    if is_job_saved(job_id):
        return False

    title_lower = title.lower()

    if any(ex in title_lower for ex in EXCLUDE_TITLES):
        return False

    if not any(k in title_lower for k in TARGET_DATA_KEYWORDS):
        return False

    print(f"[{source.upper()}] Evaluating NEW match for '{title}' at {company}...")
    score, reason = evaluate_job_with_ai(title, company, location, url, description)

    try:
        score = int(score)
    except (ValueError, TypeError):
        score = 0

    status = "APPLY" if score >= 60 else "REJECTED"

    with sqlite3.connect(DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO jobs (id, title, company, location, url, description, source, match_score, match_reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(job_id), str(title), str(company), str(location), str(url), str(description), str(source), score, str(reason), str(status)))
        conn.commit()

    print(f"  --> Saved '{title}' (Score: {score}/100)")
    return True

def fetch_greenhouse():
    print("\n--- Scanning Direct Greenhouse Endpoints ---")
    for company in GREENHOUSE_COMPANIES:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                jobs = res.json().get("jobs", [])
                for j in jobs:
                    job_id = f"gh_{j.get('id')}"
                    title = j.get("title", "")
                    loc = j.get("location", {}).get("name", "Remote")
                    job_url = j.get("absolute_url", "")
                    content = j.get("content", "")
                    save_job(job_id, title, company.capitalize(), loc, job_url, content, "greenhouse")
        except Exception as e:
            print(f"Greenhouse error for {company}: {e}")

def fetch_lever():
    print("\n--- Scanning Direct Lever Endpoints ---")
    for company in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                jobs = res.json()
                for j in jobs:
                    job_id = f"lever_{j.get('id')}"
                    title = j.get("text", "")
                    loc = j.get("categories", {}).get("location", "Remote")
                    job_url = j.get("hostedUrl", "")
                    desc = j.get("descriptionPlain", "")
                    save_job(job_id, title, company.capitalize(), loc, job_url, desc, "lever")
        except Exception as e:
            print(f"Lever error for {company}: {e}")

def fetch_ashby():
    print("\n--- Scanning Direct Ashby Endpoints ---")
    for company in ASHBY_COMPANIES:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                jobs = res.json().get("jobs", [])
                for j in jobs:
                    job_id = f"ashby_{j.get('id')}"
                    title = j.get("title", "")
                    loc = j.get("location", "Remote")
                    job_url = j.get("jobUrl", f"https://jobs.ashbyhq.com/{company}/{j.get('id')}")
                    desc = j.get("descriptionPlain", j.get("descriptionHtml", ""))
                    save_job(job_id, title, company.capitalize(), loc, job_url, desc, "ashby")
        except Exception as e:
            print(f"Ashby error for {company}: {e}")

def fetch_workable():
    print("\n--- Scanning Direct Workable Endpoints ---")
    for company in WORKABLE_COMPANIES:
        url = f"https://apply.workable.com/api/v1/widget/accounts/{company}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                jobs = res.json().get("jobs", [])
                for j in jobs:
                    job_id = f"workable_{j.get('shortcode')}"
                    title = j.get("title", "")
                    loc = f"{j.get('city', '')}, {j.get('country', '')}".strip(", ") or "Remote"
                    job_url = f"https://apply.workable.com/{company}/j/{j.get('shortcode')}/"
                    desc = j.get("description", "")
                    save_job(job_id, title, company.capitalize(), loc, job_url, desc, "workable")
        except Exception as e:
            print(f"Workable error for {company}: {e}")

if __name__ == "__main__":
    init_db()
    fetch_greenhouse()
    fetch_lever()
    fetch_ashby()
    fetch_workable()
