import json
import logging
import os
import re
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_PATH = "config/companies.json"

DEFAULT_SEED = {
    "greenhouse": [
        "stripe", "figma", "airbnb", "cloudflare", "discord", "databricks", 
        "hashicorp", "uber", "doordash", "coinbase", "instacart", "roblox"
    ],
    "ashby": [
        "openai", "anthropic", "scaleai", "ramp", "notion", "perplexity", 
        "linear", "vercel", "replit", "characterai", "resend", "sentry"
    ],
    "lever": [
        "palantir", "netflix", "spotify", "datadog", "samsara", "figma", 
        "brex", "kraken", "fivetran", "postman"
    ],
    "workable": ["benchling", "mindtickle", "intercom"],
    "smartrecruiters": ["square", "visa", "ubisoft", "bosch"]
}

SOURCES = [
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2025-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/pittcsc/Summer2025-Internships/dev/data/companies.json"
]

def extract_slug(url, pattern):
    match = re.search(pattern, url, re.IGNORECASE)
    return match.group(1).lower().strip("/").strip() if match else None

def fetch_remote_companies():
    logging.info("Starting company horizon expansion...")
    discovered = {ats: set(DEFAULT_SEED[ats]) for ats in DEFAULT_SEED}

    for url in SOURCES:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list):
                    for entry in data:
                        link = entry.get("url", "") or entry.get("apply_url", "") or entry.get("link", "")
                        if isinstance(entry.get("active_locations"), list) and not link:
                            link = str(entry)

                        gh = extract_slug(link, r"boards\.greenhouse\.io/([^/?#]+)")
                        if gh: discovered["greenhouse"].add(gh)

                        ash = extract_slug(link, r"jobs\.ashbyhq\.com/([^/?#]+)")
                        if ash: discovered["ashby"].add(ash)

                        lev = extract_slug(link, r"jobs\.lever\.co/([^/?#]+)")
                        if lev: discovered["lever"].add(lev)

                        wrk = extract_slug(link, r"apply\.workable\.co/([^/?#]+)")
                        if wrk: discovered["workable"].add(wrk)

        except Exception as e:
            logging.warning(f"Failed to process source {url}: {e}")

    final_data = {ats: sorted(list(slugs)) for ats, slugs in discovered.items()}

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(final_data, f, indent=2)

    total = sum(len(v) for v in final_data.values())
    logging.info(f"Sync complete! Saved {total} total company targets to {CONFIG_PATH}")

if __name__ == "__main__":
    fetch_remote_companies()
