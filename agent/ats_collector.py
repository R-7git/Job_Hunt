import json
import requests
from pathlib import Path

COMPANIES_CONFIG = Path("config/companies.json")

def load_companies():
    if not COMPANIES_CONFIG.exists():
        return []
    with open(COMPANIES_CONFIG, "r") as f:
        data = json.load(f)
        return data.get("companies", [])

def fetch_greenhouse_jobs(board_token: str, company_name: str) -> list:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for j in data.get("jobs", []):
                jobs.append({
                    "id": f"gh_{j.get('id')}",
                    "title": j.get("title"),
                    "company": company_name,
                    "location": j.get("location", {}).get("name", "Remote"),
                    "url": j.get("absolute_url"),
                    "source": "Greenhouse",
                    "summary": j.get("content", "")
                })
    except Exception:
        pass
    return jobs

def fetch_lever_jobs(board_token: str, company_name: str) -> list:
    url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            for j in resp.json():
                jobs.append({
                    "id": f"lever_{j.get('id')}",
                    "title": j.get("text"),
                    "company": company_name,
                    "location": j.get("categories", {}).get("location", "Remote"),
                    "url": j.get("hostedUrl"),
                    "source": "Lever",
                    "summary": j.get("descriptionPlain", "")
                })
    except Exception:
        pass
    return jobs

def fetch_ashby_jobs(board_token: str, company_name: str) -> list:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for j in data.get("jobs", []):
                jobs.append({
                    "id": f"ashby_{j.get('id')}",
                    "title": j.get("title"),
                    "company": company_name,
                    "location": j.get("location", "Remote"),
                    "url": j.get("jobUrl"),
                    "source": "Ashby",
                    "summary": j.get("descriptionPlain", "")
                })
    except Exception:
        pass
    return jobs

def fetch_search_jobs(query: str) -> list:
    """Fetch jobs matching specific query terms like 'data engineer', 'sql', 'snowflake'"""
    url = f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={query}"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for j in data.get("jobs", []):
                jobs.append({
                    "id": f"jobicy_{query}_{j.get('id')}",
                    "title": j.get("jobTitle"),
                    "company": j.get("companyName"),
                    "location": j.get("jobGeo", "Remote"),
                    "url": j.get("url"),
                    "source": f"Jobicy ({query})",
                    "summary": j.get("jobDescription", "")
                })
    except Exception:
        pass
    return jobs

def fetch_all_jobs() -> list:
    companies = load_companies()
    all_jobs = []

    for comp in companies:
        name = comp.get("name")
        ats = comp.get("ats")
        board = comp.get("board_token")

        if ats == "greenhouse":
            all_jobs.extend(fetch_greenhouse_jobs(board, name))
        elif ats == "lever":
            all_jobs.extend(fetch_lever_jobs(board, name))
        elif ats == "ashby":
            all_jobs.extend(fetch_ashby_jobs(board, name))

    # Targeted searches for core skills
    for term in ["data-engineer", "sql", "snowflake", "etl", "python"]:
        all_jobs.extend(fetch_search_jobs(term))

    return all_jobs

if __name__ == "__main__":
    jobs = fetch_all_jobs()
    print(f"Scouted {len(jobs)} total jobs across target queries.")
