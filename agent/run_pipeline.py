import json
import os
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import dotenv

from agent.scrapers import scrape_all_sources
from agent.ats_collector import fetch_all_jobs

dotenv.load_dotenv()

DB_PATH = Path(os.getenv("DB_PATH", "data/jobs.db"))
PROFILE_PATH = Path("data/profile.json")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create main table with status tracking column
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
            status TEXT DEFAULT 'REJECTED',
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

    senior_terms = ["senior", "sr.", "sr ", "lead", "staff", "principal", "architect", "manager", "director", "head of",
                    "vp"]
    if any(s in title_lower for s in senior_terms):
        return True, "Excluded: Senior/Lead Role"

    if "java" in title_lower or "java developer" in summary_lower:
        return True, "Excluded: Java Tech Stack"

    return False, ""


def evaluate_job(title: str, location: str, summary: str, profile: dict) -> tuple[float, str]:
    title_lower = title.lower()
    summary_lower = (summary or "").lower()

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

    skills_to_check = ["sql", "snowflake", "etl", "python", "aws", "s3", "azure", "adf", "dbt", "pyspark", "airflow"]
    matched_skills = [skill for skill in skills_to_check if skill in summary_lower or skill in title_lower]

    if matched_skills:
        score += min(len(matched_skills) * 5, 30)
        reasons.append(f"Skills: {', '.join(matched_skills[:5])}")

    if any(e in title_lower or e in summary_lower for e in
           ["entry", "fresher", "junior", "associate", "intern", "trainee"]):
        score += 10
        reasons.append("Fresher/Entry level indicator found.")

    return round(score, 2), " | ".join(reasons)


def prune_old_rejected_jobs():
    """Wipes heavy text descriptions (summary) for REJECTED jobs older than 30 days to save cloud space without breaking scraper deduplication."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs 
            SET summary = NULL 
            WHERE status = 'REJECTED' 
              AND scouted_at < datetime('now', '-30 days')
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cleanup warning: {e}")


def fetch_and_evaluate():
    init_db()
    profile = load_profile()

    # Collect jobs from existing ATS collector + new global sources
    fetched_jobs = fetch_all_jobs()
    global_jobs = scrape_all_sources()

    # Map global jobs to match pipeline dict structure
    for job in global_jobs:
        raw_url = job.get("url", "")
        # Generate a unique hash ID if no native ID exists
        job_id = hashlib.md5(raw_url.encode("utf-8")).hexdigest() if raw_url else None

        fetched_jobs.append({
            "id": job_id,
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", "Remote"),
            "url": raw_url,
            "source": job.get("source", "Global Scraper"),
            "summary": job.get("description", "")
        })

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    processed_ids = set()
    print(f"\n--- Scraped {len(fetched_jobs)} total job postings ---")

    for job in fetched_jobs:
        job_id = str(job.get("id"))
        if not job_id or job_id == "None" or job_id in processed_ids:
            continue
        processed_ids.add(job_id)

        # Optimization: Skip evaluation entirely if job ID already exists in DB
        cur.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        if cur.fetchone():
            continue

        title = job.get("title", "")
        company = job.get("company", "")
        location = job.get("location", "Remote")
        url = job.get("url", "")
        source = job.get("source", "ATS")
        summary = job.get("summary", "")

        # Fast-Fail Filter: Instantly drop senior/java roles
        excluded, reason = is_excluded(title, summary)
        if excluded:
            print(f"[{source}] {company} - {title} => SKIPPED ({reason})")
            cur.execute("""
                INSERT OR IGNORE INTO jobs (id, title, company, location, url, source, summary, fit_score, match_reason, status, scouted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'REJECTED', ?)
            """, (job_id, title, company, location, url, source, summary, 0.0, reason,
                  datetime.now(timezone.utc).isoformat()))
            continue

        # Evaluate score
        fit_score, match_reason = evaluate_job(title, location, summary, profile)
        status = "PENDING" if fit_score >= 50.0 else "REJECTED"

        cur.execute("""
            INSERT OR IGNORE INTO jobs (id, title, company, location, url, source, summary, fit_score, match_reason, status, scouted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, title, company, location, url, source, summary, fit_score, match_reason, status,
            datetime.now(timezone.utc).isoformat()
        ))

        print(f"[{source}] {company} - {title} => Score: {fit_score} | Status: {status}")

    conn.commit()

    # Query only jobs that need to be notified
    cur.execute("SELECT id, title, company, location, url, fit_score, match_reason FROM jobs WHERE status = 'PENDING'")
    pending_jobs = cur.fetchall()

    if pending_jobs:
        print(f"\nFound {len(pending_jobs)} new matching jobs to send to Telegram...")
        from agent.telegram_notify import send_job_alerts

        # Convert tuple query results into standard dict format for notifier
        jobs_to_notify = [
            {
                "id": row[0],
                "title": row[1],
                "company": row[2],
                "location": row[3],
                "url": row[4],
                "fit_score": row[5],
                "match_reason": row[6]
            }
            for row in pending_jobs
        ]

        # Send alerts and receive list of successfully notified IDs
        notified_ids = send_job_alerts(jobs_to_notify)

        # Update status to NOTIFIED in database
        for j_id in notified_ids:
            cur.execute("UPDATE jobs SET status = 'NOTIFIED' WHERE id = ?", (j_id,))
        conn.commit()

    # Execute database maintenance routine
    prune_old_rejected_jobs()

    conn.close()
    print("\nPipeline execution complete.")


if __name__ == "__main__":
    fetch_and_evaluate()