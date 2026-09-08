import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import dotenv

dotenv.load_dotenv()

DB_PATH = Path("data/jobs.db")
PROFILE_PATH = Path("data/profile.json")

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            source TEXT,
            summary TEXT,
            fit_score REAL,
            match_reason TEXT,
            scouted_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def load_profile():
    if not PROFILE_PATH.exists():
        return {}
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)

def is_excluded(title: str, summary: str) -> tuple[bool, str]:
    title_lower = title.lower()
    summary_lower = (summary or "").lower()

    # Immediate Exclusions: Senior roles or non-target tech stack (Java)
    senior_terms = ["senior", "sr.", "sr ", "lead", "staff", "principal", "architect", "manager", "director", "head of", "vp"]
    if any(s in title_lower for s in senior_terms):
        return True, "Excluded: Senior/Lead Role"

    if "java" in title_lower or "java developer" in summary_lower:
        return True, "Excluded: Java Tech Stack"

    return False, ""

def evaluate_job(title: str, location: str, summary: str, profile: dict) -> tuple[float, str]:
    title_lower = title.lower()
    loc_lower = (location or "").lower()
    summary_lower = (summary or "").lower()

    # Target Keywords for Data Eng / SQL / Snowflake / ETL
    target_keywords = [
        "data engineer", "data engineering", "sql", "snowflake", 
        "etl", "elt", "data pipeline", "analytics engineer", 
        "data warehouse", "bi engineer"
    ]
    title_matched = any(kw in title_lower for kw in target_keywords)

    if not title_matched:
        return 0.0, "Title not matching target fresher roles."

    score = 60.0
    reasons = ["Matched target data domain."]

    # Check candidate skills
    skills_to_check = ["sql", "snowflake", "etl", "python", "aws", "s3", "azure", "adf", "dbt", "pyspark", "airflow"]
    matched_skills = [skill for skill in skills_to_check if skill in summary_lower or skill in title_lower]

    if matched_skills:
        score += min(len(matched_skills) * 5, 30)
        reasons.append(f"Skills: {', '.join(matched_skills[:5])}")

    if any(e in title_lower or e in summary_lower for e in ["entry", "fresher", "junior", "associate", "intern", "trainee"]):
        score += 10
        reasons.append("Fresher/Entry level indicator found.")

    return round(score, 2), " | ".join(reasons)

def fetch_and_evaluate():
    init_db()
    profile = load_profile()

    from agent.ats_collector import fetch_all_jobs
    fetched_jobs = fetch_all_jobs()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    new_matches = []
    processed_ids = set()

    print(f"\n--- Scraped {len(fetched_jobs)} total job postings ---")

    for job in fetched_jobs:
        job_id = str(job.get("id"))
        if not job_id or job_id in processed_ids:
            continue
        processed_ids.add(job_id)

        title = job.get("title", "")
        company = job.get("company", "")
        location = job.get("location", "Remote")
        url = job.get("url", "")
        source = job.get("source", "ATS")
        summary = job.get("summary", "")

        # Step 1: Immediate Fast-Fail Pre-Filter (Drops Senior and Java jobs instantly)
        excluded, reason = is_excluded(title, summary)
        if excluded:
            print(f"[{source}] {company} - {title} => SKIPPED ({reason})")
            continue

        # Step 2: Database Deduplication Check
        cur.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
        if cur.fetchone():
            continue

        # Step 3: Evaluate & Score
        fit_score, match_reason = evaluate_job(title, location, summary, profile)

        cur.execute("""
            INSERT OR IGNORE INTO jobs (id, title, company, location, url, source, summary, fit_score, match_reason, scouted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, title, company, location, url, source, summary, fit_score, match_reason,
            datetime.now(timezone.utc).isoformat()
        ))

        print(f"[{source}] {company} - {title} => Score: {fit_score} ({match_reason})")

        if fit_score >= 50.0:
            new_matches.append({
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "fit_score": fit_score,
                "match_reason": match_reason
            })

    conn.commit()
    conn.close()

    print(f"\nPipeline execution complete: {len(new_matches)} qualified fresher matches found.")

    if new_matches:
        from agent.telegram_notify import send_job_alerts
        send_job_alerts(new_matches)

if __name__ == "__main__":
    fetch_and_evaluate()
