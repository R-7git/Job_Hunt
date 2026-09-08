import modal

app = modal.App("job-hunt-pipeline")

# Persistent volume for the SQLite DB
data_volume = modal.Volume.from_name("job-hunt-db", create_if_missing=True)

# Container image with dependencies
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
        "/data": data_volume  # Mounts to a dedicated directory
    },
    schedule=modal.Cron("*/15 * * * *"),
    timeout=600
)
def run_scheduled_pipeline():
    import sys
    import os

    os.chdir("/root/project")
    sys.path.append("/root/project")

    # Set database path environment variable to the persistent volume path
    os.environ["DB_PATH"] = "/data/jobs.db"

    # Reload the volume first to pull any existing database state
    data_volume.reload()

    from agent.run_pipeline import fetch_and_evaluate

    print("Starting Modal cloud execution...")
    fetch_and_evaluate()

    # Commit changes to persist SQLite updates to cloud storage
    data_volume.commit()
    print("Modal cloud execution finished and DB saved.")