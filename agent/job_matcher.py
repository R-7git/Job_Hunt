import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def clean_html(raw_html):
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html).strip()

def evaluate_job_with_ai(title, company, location, url, description):
    clean_desc = clean_html(description)[:1200]
    
    prompt = f"""
You are an AI recruiting evaluator scoring fit for an Entry-Level / Fresher candidate seeking Data Engineer, ETL Developer, or Snowflake Developer roles (0-2 years experience).

Candidate Profile:
- Target Roles: Entry-Level Data Engineer, Junior ETL Developer, Snowflake Developer, Analytics Engineer
- Core Skills: Python, SQL, Snowflake, ETL/ELT pipelines, dbt, SQL queries, Data Warehousing

Job Details:
- Title: {title}
- Company: {company}
- Location: {location}
- Description: {clean_desc}

Evaluation Criteria:
1. If the job requires 3+ years of experience, score below 40.
2. If the title or description aligns with Entry/Junior/Associate Data Engineer, ETL, or Snowflake roles, score 75-100.
3. Prioritize remote-friendly orentry-friendly descriptions.

Return ONLY a valid JSON object matching this schema:
{{
  "score": <integer from 0 to 100>,
  "match_reason": "<one sentence justification highlighting entry-level data engineer fit>"
}}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            res_data = response.json()
            response_text = res_data.get("response", "")
            data = json.loads(response_text)
            
            score = int(data.get("score", 0))
            reason = str(data.get("match_reason", "Evaluated for Entry-Level Data Engineer fit"))
            return score, reason
        else:
            return 0, f"Ollama HTTP error {response.status_code}"
    except Exception as e:
        return 0, f"Ollama evaluation failed: {str(e)}"
