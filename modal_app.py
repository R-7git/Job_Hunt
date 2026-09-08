import modal

app = modal.App("job-hunt-pipeline")

image = (
    modal.Image.debian_slim()
    .pip_install("requests", "python-dotenv")
    .add_local_dir(".", remote_path="/root/project")
)

@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("telegram-secrets")
    ],
    schedule=modal.Cron("*/15 * * * *")
)
def run_scheduled_pipeline():
    import sys
    import os

    os.chdir("/root/project")
    sys.path.append("/root/project")

    from agent.run_pipeline import process_pipeline
    
    print("Starting Modal cloud execution...")
    process_pipeline()
    print("Modal cloud execution finished.")
