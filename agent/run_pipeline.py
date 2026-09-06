import subprocess
import sys
import datetime
import os

# Ensure the root directory is in PYTHONPATH so internal imports like "from agent.xxx import yyy" work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_step(script_path):
    print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running {script_path}...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT

    try:
        result = subprocess.run([sys.executable, script_path], check=True, env=env, cwd=PROJECT_ROOT)
        print(f"Finished {script_path} with exit code {result.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")

if __name__ == "__main__":
    print("=== STARTING FULL JOB PIPELINE CYCLE ===")
    
    # 1. Scrape API Job Boards (Jobicy, Remotive, etc.)
    run_step("agent/job_collector.py")
    
    # 2. Scrape Direct ATS Board Endpoints
    run_step("agent/ats_collector.py")
    
    # 3. Tailor Applications for Matched Roles & Send Alerts
    run_step("agent/tailor.py")
    
    print("\n=== PIPELINE CYCLE COMPLETE ===")
