import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', raw_html)
    return " ".join(clean.split())

def evaluate_job_with_ai(title, company, location, url, description):
    clean_desc = clean_html(description)[:2500]

    prompt = f"""You are an expert tech recruiter evaluating entry-level/fresher Data Engineering positions.
Analyze the following job details and provide a fit score (0-100) and concise reason.

Criteria:
- Must be entry-level, junior, associate, or fresher friendly (<2 years experience).
- Core tech focus: Data Engineering, ETL/ELT, SQL, Python, Snowflake, dbt.
- Heavily penalize roles requiring >2-3 years of experience or senior responsibilities.

Job Title: {title}
Company: {company}
Location: {location}
Description Summary: {clean_desc}

Respond strictly in valid JSON with no extra conversational text or markdown codeblocks:
{{"score": <integer_0_to_100>, "reason": "<one_sentence_explanation>"}}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2
        }
    }

    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=45)
        if res.status_code == 200:
            raw_response = res.json().get("response", "").strip()
            # Clean possible markdown block markers
            cleaned_json = re.sub(r"^```json\s*", "", raw_response, flags=re.MULTILINE)
            cleaned_json = re.sub(r"^```\s*", "", cleaned_json, flags=re.MULTILINE).strip()
            
            data = json.loads(cleaned_json)
            score = int(data.get("score", 0))
            reason = str(data.get("reason", "No reason provided."))
            return score, reason
        else:
            print(f"  [Ollama Error] HTTP {res.status_code}")
            return 0, "Ollama API returned non-200 status."
    except Exception as e:
        print(f"  [Ollama Exception] {e}")
        return 0, f"Error communicating with Ollama: {str(e)}"
