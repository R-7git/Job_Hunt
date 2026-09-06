from flask import Flask, jsonify
import threading
import subprocess

app = Flask(__name__)

def run_pipeline_task():
    print("\n[WORKFLOW TRIGGERED] Starting job collection & tailoring pipeline in background...")
    cmd = "source .venv/bin/activate && export PYTHONPATH=. && python3 agent/job_collector.py && python3 agent/ats_collector.py && python3 agent/tailor.py"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, executable="/bin/bash")
    print("[WORKFLOW COMPLETE] Output:\n", result.stdout)
    if result.stderr:
        print("[WORKFLOW ERRORS]:\n", result.stderr)

@app.route('/run-jobs', methods=['POST', 'GET'])
def run_job_pipeline():
    thread = threading.Thread(target=run_pipeline_task)
    thread.start()
    return jsonify({
        "status": "started",
        "message": "Job collection & tailoring pipeline launched in background."
    }), 200

if __name__ == '__main__':
    print("Listening for n8n triggers on http://localhost:5001/run-jobs ...")
    app.run(host='0.0.0.0', port=5001)
