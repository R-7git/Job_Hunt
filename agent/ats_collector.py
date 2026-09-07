import sqlite3
import requests
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DB_PATH = "data/jobs.db"

# Sample target boards - extend as needed
GREENHOUSE_BOARDS = ["540", "affirmedrxpbc", "axios", "defenseunicorns", "goodwaygroup"]
ASHBY_BOARDS = ["growthloop", "honehealth", "esource", "ontic", "outmarket"]
LEVER_BOARDS = ["newsela", "srsacquiom", "tebra"]

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=20)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            description TEXT,
            source TEXT,
            match_score INTEGER,
            match_reason TEXT,
            status TEXT DEFAULT 'APPLY'
        )
    """)
    conn.commit()
    conn.close()

def parse_greenhouse(board):
    jobs = []
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("jobs", []):
                jobs.append((
                    f"gh_{item['id']}",
                    item.get("title", ""),
                    board.capitalize(),
                    item.get("location", {}).get("name", "Remote"),
                    item.get("absolute_url", ""),
                    item.get("content", ""),
                    "Greenhouse"
                ))
    except Exception as e:
        logging.error(f"Error fetching Greenhouse board {board}: {e}")
    return jobs

def parse_ashby(board):
    jobs = []
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeDetails=true"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("jobs", []):
                jobs.append((
                    f"ashby_{item['id']}",
                    item.get("title", ""),
                    board.capitalize(),
                    item.get("locationName", "Remote"),
                    item.get("jobUrl", ""),
                    item.get("descriptionHtml", ""),
                    "Ashby"
                ))
    except Exception as e:
        logging.error(f"Error fetching Ashby board {board}: {e}")
    return jobs

def parse_lever(board):
    jobs = []
    url = f"https://api.lever.co/v0/postings/{board}?mode=json"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for item in res.json():
                jobs.append((
                    f"lever_{item['id']}",
                    item.get("text", ""),
                    board.capitalize(),
                    item.get("categories", {}).get("location", "Remote"),
                    item.get("hostedUrl", ""),
                    item.get("descriptionPlain", ""),
                    "Lever"
                ))
    except Exception as e:
        logging.error(f"Error fetching Lever board {board}: {e}")
    return jobs

def is_valid_location(location):
    loc = location.lower().strip()

    # Explicitly allowed global or India locations
    allowed_markers = ["india", "global", "anywhere", "worldwide", "remote - india", "remote, india"]
    if any(m in loc for m in allowed_markers):
        return True

    # Exclude restricted non-India regions
    blocked_regions = [
        "united states", "us", "usa", "canada", "uk", "united kingdom", 
        "emea", "latam", "apac", "europe", "americas", "brazil", "germany"
    ]
    
    # Check for restricted terms using word boundaries where applicable
    for region in blocked_regions:
        pattern = r'\b' + re.escape(region) + r'\b'
        if re.search(pattern, loc):
            return False

    # Allow plain "remote" or unassigned locations
    if "remote" in loc or loc == "":
        return True

    return False

def is_valid_de_role(title, location):
    title_clean = title.lower()

    # Must contain DE keywords
    de_keywords = ["data engineer", "analytics engineer", "database engineer"]
    if not any(k in title_clean for k in de_keywords):
        return False

    # Exclude senior / non-entry roles
    senior_patterns = [r"\bsenior\b", r"\bsr\b", r"\blead\b", r"\bprincipal\b", r"\bii\b", r"\biii\b", r"\bmanager\b"]
    if any(re.search(p, title_clean) for p in senior_patterns):
        return False

    # Check geographical eligibility for India candidates
    return is_valid_location(location)

def save_jobs(jobs):
    conn = get_db_connection()
    cursor = conn.cursor()
    saved_count = 0
    for job in jobs:
        job_id, title, company, location, url, description, source = job
        if is_valid_de_role(title, location):
            try:
                cursor.execute("""
                    INSERT INTO jobs (id, title, company, location, url, description, source, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'APPLY')
                    ON CONFLICT(id) DO NOTHING
                """, (job_id, title, company, location, url, description, source))
                if cursor.rowcount > 0:
                    saved_count += 1
            except Exception as e:
                logging.error(f"DB Error inserting {job_id}: {e}")
    conn.commit()
    conn.close()
    return saved_count

def run_collector():
    init_db()
    all_jobs = []
    
    logging.info("Starting Parallel Board Scanning with India/Global Location Filtering...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for b in GREENHOUSE_BOARDS:
            futures.append(executor.submit(parse_greenhouse, b))
        for b in ASHBY_BOARDS:
            futures.append(executor.submit(parse_ashby, b))
        for b in LEVER_BOARDS:
            futures.append(executor.submit(parse_lever, b))

        for future in as_completed(futures):
            all_jobs.extend(future.result())

    new_jobs = save_jobs(all_jobs)
    logging.info(f"Collector finished. Scraped {len(all_jobs)} listings. Saved {new_jobs} eligible 'APPLY' roles.")

if __name__ == "__main__":
    run_collector()
