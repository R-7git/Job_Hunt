import requests
import re
from agent.job_matcher import evaluate_job_with_ai

def is_valid_entry_de(title: str, description: str = "") -> bool:
    title_lower = title.lower()
    desc_lower = description.lower()

    # 1. Reject forbidden titles
    banned_titles = ["senior", "sr.", "sr ", "lead", "staff", "principal", "manager", "director", "head", "architect", "sales", "analyst"]
    if any(banned in title_lower for banned in banned_titles):
        return False

    # 2. Reject high-experience requirements in body text (3+ years, 5+ years, etc.)
    banned_exp_patterns = [
        r'\b[3-9]\+\s*years',          # 3+ years, 5+ years, 8+ years
        r'\b1[0-9]\+\s*years',        # 10+ years, 15+ years
        r'\b[3-9]\s*to\s*[0-9]+\s*years', # 3 to 5 years, 5 to 7 years
        r'5\+\s*years\s*of\s*experience',
        r'senior\s*data\s*engineer'
    ]
    
    for pattern in banned_exp_patterns:
        if re.search(pattern, desc_lower):
            return False

    # 3. Must match core DE role keywords in title
    core_keywords = ["data engineer", "etl", "data pipeline", "dbt", "snowflake"]
    return any(keyword in title_lower for keyword in core_keywords)

def fetch_jobicy():
    print("Checking source: Jobicy Remote API...")
    url = "https://jobicy.com/api/v2/remote-jobs?count=50&industry=dev"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            jobs = resp.json().get('jobs', [])
            for job in jobs:
                title = job.get('jobTitle', '')
                desc = job.get('jobDescription', '')
                if is_valid_entry_de(title, desc):
                    print(f"\n[ENTRY DE MATCH] {title} at {job.get('companyName')}")
                    evaluate_job_with_ai(
                        title=title,
                        company=job.get('companyName', 'Unknown'),
                        location=job.get('jobGeo', 'Remote'),
                        url=job.get('url', ''),
                        description=desc
                    )
    except Exception as e:
        print(f"Jobicy API error: {e}")

def fetch_remotive():
    print("Checking source: Remotive API...")
    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=50"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            jobs = resp.json().get('jobs', [])
            for job in jobs:
                title = job.get('title', '')
                desc = job.get('description', '')
                if is_valid_entry_de(title, desc):
                    print(f"\n[ENTRY DE MATCH] {title} at {job.get('company_name')}")
                    evaluate_job_with_ai(
                        title=title,
                        company=job.get('company_name', 'Unknown'),
                        location=job.get('candidate_required_location', 'Remote'),
                        url=job.get('url', ''),
                        description=desc
                    )
    except Exception as e:
        print(f"Remotive API error: {e}")

def fetch_arbeitnow():
    print("Checking source: Arbeitnow API...")
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            jobs = resp.json().get('data', [])
            for job in jobs:
                title = job.get('title', '')
                desc = job.get('description', '')
                if is_valid_entry_de(title, desc):
                    print(f"\n[ENTRY DE MATCH] {title} at {job.get('company_name')}")
                    evaluate_job_with_ai(
                        title=title,
                        company=job.get('company_name', 'Unknown'),
                        location=job.get('location', 'Remote'),
                        url=job.get('url', ''),
                        description=desc
                    )
    except Exception as e:
        print(f"Arbeitnow API error: {e}")

def run_collector():
    print("Fetching live Entry/Fresher Data Engineering roles globally...")
    fetch_jobicy()
    fetch_remotive()
    fetch_arbeitnow()
    print("\nProcessing complete!")

if __name__ == "__main__":
    run_collector()
