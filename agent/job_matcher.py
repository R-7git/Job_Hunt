import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def clean_html(raw_html):
    if not raw_html:
        return ""
    cleaner = re.compile('<.*?>')
    return re.sub(cleaner, '', raw_html).strip()

def evaluate_job_match(title: str, description: str):
    clean_desc = clean_html(description)

    # 1. Deterministic Hard Filter: Senior titles
    title_lower = title.lower()
    senior_keywords = ["senior", "sr.", "sr ", "staff", "principal", "lead", "manager", "head", "director"]
    if any(kw in title_lower for kw in senior_keywords):
        return 0, "Hard Filter: Senior title detected."

    # 2. Deterministic Hard Filter: Senior experience (3+ years, 5+ years, 8+ years)
    senior_exp = re.search(r'(\b[3-9]|\b1[0-9])\+?\s*years?', clean_desc, re.IGNORECASE)
    if senior_exp:
        # Check if acceptable entry-level range is specified (0-3, 1-3, <=2)
        if not re.search(r'\b(0|1|2)\s*[-–to]+\s*[1-3]\s*years?', clean_desc, re.IGNORECASE) and \
           not re.search(r'([<⩽]=?\s*[1-2]\s*years?)', clean_desc, re.IGNORECASE):
            return 0, f"Hard Filter: Experience requirement ({senior_exp.group(0)}) exceeds entry-level threshold."

    # 3. LLM Matcher with Temperature Set to 0.0 for Deterministic Scoring
    prompt = f"""You are an automated technical recruiter evaluating a job description for an ENTRY-LEVEL / FRESHER Data Engineer.

REQUIREMENTS:
- Evaluate technical relevance to Python, SQL, Snowflake, dbt, ETL/ELT pipelines, or Cloud Data Platforms.
- Candidate has 0-2 years of experience.
- Assign higher scores (60-100) to junior/fresher roles that focus on core data engineering skills.
- Assign low scores (0-59) to overly specialized non-DE roles or those requiring extensive experience.

Job Title: {title}
Job Description Snippet: {clean_desc[:2000]}

Respond strictly in valid JSON format:
{{
  "score": <integer from 0 to 100>,
  "reason": "<one sentence explanation>"
}}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json().get("response", "")
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return int(data.get("score", 0)), data.get("reason", "No reason provided.")
    except Exception as e:
        print(f"Ollama Evaluation Error: {e}")

    return 0, "Evaluation failed or defaulted to 0."