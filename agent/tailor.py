import os
import sys
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.telegram_notify import send_telegram_alert
from agent.job_matcher import clean_html

DB_PATH = "data/jobs.db"
OUTPUT_DIR = "applications"

def generate_tailored_materials(title, company, description):
    clean_desc = clean_html(description)
    
    cover_letter = f"""Dear Hiring Manager at {company},

I am writing to express my strong interest in the {title} position. With a solid foundation in Python, SQL, Snowflake, and building robust ETL pipelines, I am eager to contribute to your data engineering team.

My technical experience aligns directly with designing data workflows, managing data transformations using dbt and SQL, and maintaining reliable data pipelines. I am excited about the opportunity to bring my hands-on knowledge and enthusiasm for data engineering to {company}.

Thank you for your time and consideration.

Best regards,
Candidate"""

    key_points = [
        f"Tailored for {title} at {company}",
        "Highlighted Skills: Python, SQL, Snowflake, ETL/ELT Pipelines, dbt",
        "Focused on data pipeline reliability, clean data modeling, and entry-level execution."
    ]

    content = f"# Application Materials: {title} at {company}\n\n"
    content += "## Target Focus Points\n"
    for pt in key_points:
        content += f"- {pt}\n"
    content += "\n## Tailored Cover Letter\n"
    content += cover_letter

    return content

def process_applications():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sqlite3.connect(DB_PATH, timeout=20.0) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, company, location, url, description, match_score, match_reason
            FROM jobs
            WHERE status = 'APPLY'
        """)
        jobs = cursor.fetchall()

        if not jobs:
            print("No new jobs requiring application tailoring.")
            return

        print(f"Found {len(jobs)} new job(s) ready for application tailoring...")

        for job in jobs:
            job_id, title, company, loc, url, desc, score, reason = job

            safe_company = "".join(c for c in company if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            file_name = f"{safe_company}_{safe_title}.md"
            file_path = os.path.join(OUTPUT_DIR, file_name)

            materials = generate_tailored_materials(title, company, desc)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(materials)

            print(f"Saved tailored materials to: {file_path}")

            sent = send_telegram_alert(title, company, loc, url, score, reason)
            if sent:
                cursor.execute("UPDATE jobs SET status = 'NOTIFIED' WHERE id = ?", (job_id,))
                conn.commit()

if __name__ == "__main__":
    process_applications()
