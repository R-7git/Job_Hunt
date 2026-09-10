# Automated Serverless Data Engineering Job Pipeline

An end-to-end, production-grade serverless data pipeline designed to scrape, clean, model, test, and dispatch real-time alerts for entry-level Data Engineering roles.

## 🏗 Architecture Overview

```
[Web Scraper] ---> [SQLite Storage] ---> [dbt Transformations & Tests] ---> [Telegram Alerts]
                                              |
                               [Modal Cloud Cron (15m)]
```

* **Ingestion Layer:** Python scraper pulling active job listings into SQLite (`data/jobs.db`).
* **Transformation Layer:** dbt models (`stg_jobs`, `dim_active_target_jobs`) filtering senior roles and isolating entry-level DE targets.
* **Data Quality Layer:** Automated schema assertions (`unique`, `not_null`) validating records.
* **Orchestration:** Serverless scheduling hosted on Modal Cloud (15-minute cron).
* **CI/CD Pipeline:** GitHub Actions workflow executing `dbt run` and `dbt test` on Pull Requests.

## 🛠 Tech Stack

* **Language:** Python 3.11
* **Database:** SQLite
* **Transformation:** dbt-core (dbt-sqlite adapter)
* **Serverless Compute:** Modal Cloud
* **CI/CD:** GitHub Actions
* **Alerting:** Telegram Bot API

## 🚀 Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Run dbt transformations locally
dbt run --project-dir dbt_jobs
dbt test --project-dir dbt_jobs

# Deploy pipeline to Modal
modal deploy main.py
```
