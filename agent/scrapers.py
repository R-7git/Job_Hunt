import json
import re
import xml.etree.ElementTree as ET
import requests

# ---------------------------------------------------------------------------
# 1. ATS ENDPOINT SCRAPERS (Greenhouse, Lever, Ashby, Workable, SmartRecruiters)
# ---------------------------------------------------------------------------

COMPANY_SLUGS = {
    "lever": [
        "cloudflare", "netflix", "spotify", "datadog", "palantir", "figma", 
        "notion", "airtable", "linear", "scale", "docker", "postman"
    ],
    "greenhouse": [
        "gitlab", "stripe", "hashicorp", "datadog", "github", "elastic", 
        "coinbase", "brex", "door-dash", "instacart", "reddit", "discord"
    ],
    "ashby": [
        "openai", "anthropic", "rampnow", "mistral", "replit", "characterai", 
        "cursor", "elevenlabs", "vanta", "retool", "resend"
    ],
    "workable": [
        "canonical", "sentry", "vistas", "kiwi", "duckduckgo"
    ],
    "smartrecruiters": [
        "ubisoft", "visa", "square", "twitter", "bosch"
    ]
}

def scrape_lever_companies():
    """Fetches public jobs directly from Lever ATS endpoints."""
    jobs = []
    for slug in COMPANY_SLUGS["lever"]:
        try:
            url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                for p in res.json():
                    jobs.append({
                        "title": p.get("text", ""),
                        "company": slug.capitalize(),
                        "url": p.get("hostedUrl", ""),
                        "description": p.get("descriptionPlain", ""),
                        "source": f"Lever ({slug})"
                    })
        except Exception:
            continue
    return jobs

def scrape_greenhouse_companies():
    """Fetches public jobs directly from Greenhouse API endpoints."""
    jobs = []
    for slug in COMPANY_SLUGS["greenhouse"]:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                for p in res.json().get("jobs", []):
                    jobs.append({
                        "title": p.get("title", ""),
                        "company": slug.capitalize(),
                        "url": p.get("absolute_url", ""),
                        "description": p.get("content", ""),
                        "source": f"Greenhouse ({slug})"
                    })
        except Exception:
            continue
    return jobs

def scrape_ashby_companies():
    """Fetches public jobs directly from Ashby ATS endpoints."""
    jobs = []
    for slug in COMPANY_SLUGS["ashby"]:
        try:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                for p in res.json().get("jobs", []):
                    jobs.append({
                        "title": p.get("title", ""),
                        "company": slug.capitalize(),
                        "url": p.get("jobUrl", ""),
                        "description": p.get("descriptionHtml", ""),
                        "source": f"Ashby ({slug})"
                    })
        except Exception:
            continue
    return jobs

def scrape_workable_companies():
    """Fetches public jobs directly from Workable ATS endpoints."""
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for slug in COMPANY_SLUGS["workable"]:
        try:
            url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                for p in res.json().get("jobs", []):
                    jobs.append({
                        "title": p.get("title", ""),
                        "company": slug.capitalize(),
                        "url": p.get("shortlink", ""),
                        "description": p.get("description", ""),
                        "source": f"Workable ({slug})"
                    })
        except Exception:
            continue
    return jobs

def scrape_smartrecruiters_companies():
    """Fetches public jobs directly from SmartRecruiters endpoints."""
    jobs = []
    for slug in COMPANY_SLUGS["smartrecruiters"]:
        try:
            url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                for p in res.json().get("content", []):
                    jobs.append({
                        "title": p.get("name", ""),
                        "company": slug.capitalize(),
                        "url": f"https://jobs.smartrecruiters.com/{slug}/{p.get('id')}",
                        "description": p.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", ""),
                        "source": f"SmartRecruiters ({slug})"
                    })
        except Exception:
            continue
    return jobs

# ---------------------------------------------------------------------------
# 2. OPEN GLOBAL REST APIs (Remotive, RemoteOK, Hacker News)
# ---------------------------------------------------------------------------

def scrape_remotive():
    """Fetches jobs from Remotive's open REST API."""
    jobs = []
    try:
        res = requests.get("https://remotive.com/api/remote-jobs", timeout=10)
        if res.status_code == 200:
            for item in res.json().get("jobs", []):
                jobs.append({
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "source": "Remotive API"
                })
    except Exception:
        pass
    return jobs

def scrape_remoteok_api():
    """Fetches jobs from RemoteOK open API endpoint."""
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get("https://remoteok.com/api", headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for item in data[1:] if isinstance(data, list) and len(data) > 1 else []:
                jobs.append({
                    "title": item.get("position", ""),
                    "company": item.get("company", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "source": "RemoteOK API"
                })
    except Exception:
        pass
    return jobs

def scrape_hn_who_is_hiring():
    """Parses Hacker News official Firebase API for 'Who is Hiring' postings."""
    jobs = []
    try:
        search_res = requests.get("https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&query=Who%20is%20hiring", timeout=10)
        if search_res.status_code == 200:
            hits = search_res.json().get("hits", [])
            if hits:
                story_id = hits[0].get("objectID")
                item_res = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=10)
                if item_res.status_code == 200:
                    kids = item_res.json().get("kids", [])[:30]
                    for kid_id in kids:
                        c_res = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json", timeout=5)
                        if c_res.status_code == 200:
                            text = c_res.json().get("text", "")
                            if text:
                                lines = text.split("<p>")[0]
                                parts = lines.split("|")
                                company = parts[0].strip() if len(parts) > 0 else "HN Startup"
                                title = parts[1].strip() if len(parts) > 1 else "Software Engineering Role"
                                jobs.append({
                                    "title": title,
                                    "company": company,
                                    "url": f"https://news.ycombinator.com/item?id={kid_id}",
                                    "description": text,
                                    "source": "HackerNews WhoIsHiring"
                                })
    except Exception:
        pass
    return jobs

# ---------------------------------------------------------------------------
# 3. GLOBAL RSS & XML FEEDS
# ---------------------------------------------------------------------------

def scrape_rss_feeds():
    """Parses free global RSS streams (We Work Remotely, Jobspresso, SkipTheDrive)."""
    jobs = []
    rss_urls = [
        ("https://weworkremotely.com/categories/remote-programming-jobs.rss", "WeWorkRemotely"),
        ("https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss", "WeWorkRemotely"),
        ("https://jobspresso.co/feed/", "Jobspresso"),
        ("https://www.skipthedrive.com/feed/", "SkipTheDrive")
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    for url, source_name in rss_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for item in root.findall("./channel/item"):
                    raw_title = item.findtext("title", "")
                    company = raw_title.split(":")[0] if ":" in raw_title else source_name
                    job_title = raw_title.split(":")[1].strip() if ":" in raw_title else raw_title
                    jobs.append({
                        "title": job_title,
                        "company": company,
                        "url": item.findtext("link", ""),
                        "description": item.findtext("description", ""),
                        "source": f"{source_name} RSS"
                    })
        except Exception:
            continue
    return jobs

# ---------------------------------------------------------------------------
# 4. OPEN-SOURCE GITHUB REPOSITORIES
# ---------------------------------------------------------------------------

def scrape_github_community_repos():
    """Parses raw open-source GitHub repositories for daily maintained tech jobs."""
    jobs = []
    try:
        url = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/main/README.md"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            lines = res.text.split("\n")
            for line in lines:
                if "|" in line and "http" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4:
                        company = parts[1]
                        title = parts[2]
                        urls = re.findall(r'href=[\'"]?([^\'" >]+)', line) or re.findall(r'\((https?://[^\)]+)\)', line)
                        if urls:
                            jobs.append({
                                "title": title,
                                "company": company,
                                "url": urls[0],
                                "description": f"{title} position at {company}",
                                "source": "GitHub SimplifyJobs Repo"
                            })
    except Exception:
        pass
    return jobs

# ---------------------------------------------------------------------------
# CONSOLIDATED MASTER RUNNER
# ---------------------------------------------------------------------------

def scrape_all_sources():
    """Executes all global job scrapers and returns a consolidated array of jobs."""
    all_jobs = []
    
    print("Scraping ATS Endpoints (Lever, Greenhouse, Ashby, Workable, SmartRecruiters)...")
    all_jobs.extend(scrape_lever_companies())
    all_jobs.extend(scrape_greenhouse_companies())
    all_jobs.extend(scrape_ashby_companies())
    all_jobs.extend(scrape_workable_companies())
    all_jobs.extend(scrape_smartrecruiters_companies())

    print("Scraping Global APIs (Remotive, RemoteOK, Hacker News)...")
    all_jobs.extend(scrape_remotive())
    all_jobs.extend(scrape_remoteok_api())
    all_jobs.extend(scrape_hn_who_is_hiring())

    print("Scraping RSS Streams...")
    all_jobs.extend(scrape_rss_feeds())

    print("Scraping Community GitHub Repositories...")
    all_jobs.extend(scrape_github_community_repos())

    return all_jobs
