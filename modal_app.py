import modal

app = modal.App("job-hunt-pipeline")

# Create a persistent volume to store jobs.db across cloud runs
data_volume = modal.Volume.from_name("job-hunt-db", create_if_missing=True)

# Install all necessary dependencies for scraping and execution
image = (
    modal.Image.debian_slim()
    .pip_install("requests", "python-dotenv", "beautifulsoup4", "lxml")
    .add_local_dir(".", remote_path="/root/project")
)

@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("telegram-secrets")
    ],
    volumes={
        "/root/project/data": data_volume  # Persists jobs.db
    },
    schedule=modal.Cron("*/15 * * * *"),
    timeout=600  # Sets timeout to 10 minutes
)
def run_scheduled_pipeline():
    import sys
    import os

    os.chdir("/root/project")
    sys.path.append("/root/project")

    from agent.run_pipeline import fetch_and_evaluate
    
    print("Starting Modal cloud execution...")
    fetch_and_evaluate()
    
    # Commit changes to persistent storage
    data_volume.commit()
    print("Modal cloud execution finished and DB saved.")
