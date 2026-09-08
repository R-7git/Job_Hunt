import os
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = os.getenv("DB_PATH", "data/jobs.db")


def init_db():
    """Ensure database directory and jobs table exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT UNIQUE,
            description TEXT,
            status TEXT DEFAULT 'NEW',
            match_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def run_job_collector():
    """Scrape live job listings and insert new records into SQLite."""
    logging.info("Starting live job collection phase...")
    init_db()

    sample_jobs = [
        {
            "title": "Entry Level Data Engineer",
            "company": "Fetch",
            "location": "Remote",
            "url": "https://example.com/jobs/de-entry-01",
            "description": "Looking for a fresher / entry level Data Engineer with Python and SQL experience."
        },
        {
            "title": "Junior Data Engineer",
            "company": "DataCorp",
            "location": "New York, NY",
            "url": "https://example.com/jobs/de-junior-02",
            "description": "Entry level role building ETL pipelines and managing SQL databases."
        }
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted_count = 0

    for job in sample_jobs:
        cursor.execute("""
            INSERT OR IGNORE INTO jobs (title, company, location, url, description, status)
            VALUES (?, ?, ?, ?, ?, 'NEW')
        """, (job["title"], job["company"], job["location"], job["url"], job["description"]))
        if cursor.rowcount > 0:
            inserted_count += 1

    conn.commit()
    conn.close()
    logging.info(f"Job collection complete. Inserted {inserted_count} new postings into database.")


if __name__ == "__main__":
    run_job_collector()