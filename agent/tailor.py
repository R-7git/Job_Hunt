import sqlite3
import os
from agent.telegram_notify import send_telegram_alert

DB_PATH = "data/jobs.db"
OUTPUT_DIR = "applications"

def generate_tailored_docs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Process ALL jobs marked APPLY
    cursor.execute("SELECT id, title, company, location, url, description, match_score, match_reason FROM jobs WHERE status = 'APPLY'")
    jobs = cursor.fetchall()
    
    if not jobs:
        print("No pending 'APPLY' jobs to process.")
        conn.close()
        return

    print(f"Found {len(jobs)} job(s) ready for application tailoring...")

    for job in jobs:
        job_id, title, company, location, url, description, score, reason = job
        filename = f"{company}_{title}".replace(" ", "_").replace("/", "_") + ".md"
        filepath = os.path.join(OUTPUT_DIR, filename)

        doc_content = f"""# Tailored Application Package

**Target Role:** {title}
**Company:** {company}
**Location:** {location}
**Match Score:** {score}/100
**URL:** {url}

---

## 1. Tailored Resume Bullets
* Optimized data ingestion pipelines processing high-volume datasets using Python and SQL.
* Designed and executed ETL workflows aligned with modern data engineering stack requirements.

---

## 2. Custom Cover Letter
Dear Hiring Manager at {company},

I am writing to express my strong enthusiasm for the {title} position. With a strong background in Python, SQL, and building modular data pipelines, I am eager to contribute to {company}'s data engineering team.

Sincerely,
Candidate
"""
        with open(filepath, "w") as f:
            f.write(doc_content)
        
        print(f"Saved tailored materials to: {filepath}")

        # Send instant notification to Telegram
        send_telegram_alert(title, company, location, url, score, reason)

    conn.close()

if __name__ == "__main__":
    generate_tailored_docs()
