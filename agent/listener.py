import os
import sqlite3
import logging
import requests
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = Path(__file__).parent.parent / "data" / "jobs.db"


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

    # Sample mock scraper payload / replacement target for live APIs
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
        try:
            cursor.execute("""
                INSERT INTO jobs (title, company, location, url, description, status)
                VALUES (?, ?, ?, ?, ?, 'NEW')
            """, (job["title"], job["company"], job["location"], job["url"], job["description"]))
            inserted_count += 1
        except sqlite3.IntegrityError:
            # Skip duplicates based on unique URL
            pass

    conn.commit()
    conn.close()
    logging.info(f"Job collection complete. Inserted {inserted_count} new postings into database.")


if __name__ == "__main__":
    run_job_collector()