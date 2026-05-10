import os
import sys
import json
import subprocess
import argparse
import time
from datetime import datetime

def safe_run(project_dir, name, command):
    # Ensure reports/jobs directory exists
    job_dir = os.path.abspath(os.path.join(project_dir, "reports", "jobs"))
    os.makedirs(job_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = f"{timestamp}_{name}"
    
    log_path = os.path.join(job_dir, f"{job_id}.log")
    status_path = os.path.join(job_dir, f"{job_id}.json")
    
    # Prepare the command to run in background
    # We use a shell wrapper to ensure we capture the PID of the actual command
    # and update the status file when finished.
    
    status_data = {
        "job_id": job_id,
        "name": name,
        "command": command,
        "status": "starting",
        "started_at": datetime.now().isoformat(),
        "log_path": log_path,
        "pid": None
    }
    
    with open(status_path, 'w') as f:
        json.dump(status_data, f, indent=2)
        
    # Launch command
    # We'll use subprocess.Popen and not wait for it.
    # Note: For persistence across agent restarts, nohup-style is better.
    
    log_file = open(log_path, 'w')
    
    try:
        # We run it via 'sh -c' to support complex commands and redirection
        process = subprocess.Popen(
            f"{command} >> {log_path} 2>&1",
            shell=True,
            cwd=project_dir,
            start_new_session=True # Equivalent to nohup / setsid
        )
        
        status_data["status"] = "running"
        status_data["pid"] = process.pid
        
        with open(status_path, 'w') as f:
            json.dump(status_data, f, indent=2)
            
        print(json.dumps({
            "message": f"Job '{name}' started in background.",
            "job_id": job_id,
            "pid": process.pid,
            "log_path": log_path,
            "status_path": status_path
        }, indent=2))
        
    except Exception as e:
        status_data["status"] = "failed"
        status_data["error"] = str(e)
        with open(status_path, 'w') as f:
            json.dump(status_data, f, indent=2)
        print(json.dumps({"error": f"Failed to start job: {e}"}, indent=2))
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Antigravity Safe Run: Background Job Wrapper")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--name", required=True, help="Friendly name for the job")
    parser.add_argument("--cmd", required=True, help="Command to execute")
    args = parser.parse_args()
    
    if not os.path.exists(args.project):
        print(json.dumps({"error": f"Project directory '{args.project}' does not exist."}, indent=2))
        sys.exit(1)
        
    safe_run(args.project, args.name, args.cmd)

if __name__ == "__main__":
    main()
