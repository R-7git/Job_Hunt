import os
import subprocess
import modal

# Define container image and mount local directories directly
app_image = (
    modal.Image.debian_slim()
    .pip_install("dbt-core==1.10.0", "dbt-sqlite==1.10.0")
    .add_local_dir("dbt_jobs", remote_path="/root/dbt_jobs")
    .add_local_dir("data", remote_path="/root/data")
)

app = modal.App("job-hunt-scraper", image=app_image)

@app.function(
    image=app_image,
    schedule=modal.Cron("*/15 * * * *")
)
def run_job_pipeline():
    print("1. Scraping job postings...")
    # Your Modal scraping logic runs here
    
    print("2. Setting up dbt profiles inside container...")
    os.makedirs("/root/.dbt", exist_ok=True)
    with open("/root/.dbt/profiles.yml", "w") as f:
        f.write("""
dbt_jobs:
  target: dev
  outputs:
    dev:
      type: sqlite
      threads: 1
      database: "database"
      schema: "main"
      schemas_and_paths:
        main: "/root/data/jobs.db"
      schema_directory: "/root/data"
""")

    print("3. Executing dbt transformations...")
    subprocess.run(["dbt", "run", "--project-dir", "/root/dbt_jobs"], check=True)

    print("4. Executing dbt data quality tests...")
    subprocess.run(["dbt", "test", "--project-dir", "/root/dbt_jobs"], check=True)
    print("Pipeline run completed successfully.")
