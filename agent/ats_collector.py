import requests
import re
from agent.job_matcher import evaluate_job_with_ai

GREENHOUSE_BOARDS = ["gitlab", "cloudflare", "stripe", "canonical"]
LEVER_BOARDS = ["netflix", "spotify", "palantir"]

def is_valid_entry_de(title: str, description: str = "") -> bool:
    title_lower = title.lower()
    desc_lower = description.lower()

    banned_titles = ["senior", "sr.", "sr ", "lead", "staff", "principal", "manager", "director", "head", "architect", "sales", "analyst"]
    if any(banned in title_lower for banned in banned_titles):
        return False

    banned_exp_patterns = [
        r'\b[3-9]\+\s*years',
        r'\b1[0-9]\+\s*years',
        r'\b[3-9]\s*to\s*[0-9]+\s*years',
        r'5\+\s*years\s*of\s*experience',
        r'senior\s*data\s*engineer'
    ]
    
    for pattern in banned_exp_patterns:
        if re.search(pattern, desc_lower):
            return False

    core_keywords = ["data engineer", "etl", "data pipeline", "dbt", "snowflake"]
    return any(keyword in title_lower for keyword in core_keywords)

def fetch_greenhouse():
    print("Scanning Direct Greenhouse ATS Endpoints...")
    for board in GREENHOUSE_BOARDS:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                jobs = resp.json().get('jobs', [])
                for job in jobs:
                    title = job.get('title', '')
                    desc = job.get('content', '')
                    if is_valid_entry_de(title, desc):
                        print(f"\n[GREENHOUSE MATCH] {title} at {board}")
                        evaluate_job_with_ai(
                            title=title,
                            company=board.capitalize(),
                            location=job.get('location', {}).get('name', 'Remote'),
                            url=job.get('absolute_url', ''),
                            description=desc
                        )
        except Exception:
            pass

def fetch_lever():
    print("Scanning Direct Lever ATS Endpoints...")
    for board in LEVER_BOARDS:
        url = f"https://api.lever.co/v0/postings/{board}?mode=json"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                jobs = resp.json()
                for job in jobs:
                    title = job.get('text', '')
                    desc = job.get('descriptionPlain', '')
                    if is_valid_entry_de(title, desc):
                        print(f"\n[LEVER MATCH] {title} at {board}")
                        evaluate_job_with_ai(
                            title=title,
                            company=board.capitalize(),
                            location=job.get('categories', {}).get('location', 'Remote'),
                            url=job.get('hostedUrl', ''),
                            description=desc
                        )
        except Exception:
            pass

def run_ats_collector():
    fetch_greenhouse()
    fetch_lever()

if __name__ == "__main__":
    run_ats_collector()
