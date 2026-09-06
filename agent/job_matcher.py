import requests
import sqlite3
import json
import re

DB_PATH = "data/jobs.db"
OLLAMA_URL = "http://localhost:11434/api/generate"

def is_url_processed(url: str) -> bool:
    """Check if the job URL already exists in SQLite."""
    if not url:
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM jobs WHERE url = ?", (url,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def evaluate_job_with_ai(title: str, company: str, location: str, url: str, description: str):
    # 1. Deduplication Check
    if is_url_processed(url):
        print(f"  --> [SKIPPED DUP] '{title}' at {company} (Already in database)")
        return

    # 2. Secondary Python safety check before calling Ollama
    desc_lower = description.lower()
    if re.search(r'\b[3-9]\+\s*years', desc_lower) or "senior data engineer" in desc_lower:
        print(f"  --> [SKIPPED EXP] '{title}' at {company} (Failed body experience check: 3+ years required)")
        return

    prompt = f"""
You are a strict HR screener evaluating jobs for an ENTRY-LEVEL / FRESHER Data Engineer (0-2 years max experience).

Job Title: {title}
Job Description: {description}

CRITICAL RULES:
1. If the job description requires 3+, 5+, or 8+ years of experience, set match_score to 0 and status to IGNORE.
2. If the title indicates Senior, Lead, Staff, or Manager, set match_score to 0 and status to IGNORE.
3. Candidate Skills: Python, SQL, PostgreSQL, Snowflake, dbt, Apache Airflow, Docker.

Respond STRICTLY with a JSON object in this exact format:
{{
  "match_score": <number between 0 and 100>,
  "status": "<APPLY or IGNORE>",
  "reason": "<one sentence justification>"
}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result_text = response.json().get('response', '')
            
            # Extract JSON payload
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                score = int(data.get("match_score", 0))
                status = str(data.get("status", "IGNORE")).upper()
                reason = str(data.get("reason", ""))
            else:
                score, status, reason = 0, "IGNORE", "Failed to parse LLM JSON"

            # Save to SQLite database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (title, company, location, url, description, match_score, status, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, company, location, url, description, score, status, reason))
            conn.commit()
            conn.close()

            print(f"Saved: '{title}' at {company} [{location}] -> Score: {score} ({status})")

    except Exception as e:
        print(f"Ollama scoring error for {title}: {e}")
