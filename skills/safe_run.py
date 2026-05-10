import os
import sys
import json
import subprocess
import argparse
import time
from datetime import datetime

def safe_run(project_dir, name, command, cwd_override=None):
    # Determine repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))
    run_cwd = os.path.abspath(cwd_override) if cwd_override else repo_root
    
    # Ensure reports/jobs directory exists (absolute path)
    job_dir = os.path.abspath(os.path.join(project_dir, "reports", "jobs"))
    os.makedirs(job_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = f"{timestamp}_{name}"
    
    log_path = os.path.join(job_dir, f"{job_id}.log")
    status_path = os.path.join(job_dir, f"{job_id}.json")
    
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
        
    # Launch command with status update wrapper
    # We use python3 skills/update_job_status.py to update the JSON after the command ends
    import shlex
    python_bin = sys.executable or "python3"
    update_script = os.path.join(repo_root, "skills", "update_job_status.py")
    
    # We wrap the command in a subshell and then run the status update
    wrapper_cmd = f"({command}) >> {shlex.quote(log_path)} 2>&1; {shlex.quote(python_bin)} {shlex.quote(update_script)} {shlex.quote(status_path)} $?"
    
    try:
        process = subprocess.Popen(
            wrapper_cmd,
            shell=True,
            cwd=run_cwd,
            start_new_session=True 
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
    parser.add_argument("--cwd", default=None, help="Working directory (defaults to repo root)")
    args = parser.parse_args()
    
    if not os.path.exists(args.project):
        print(json.dumps({"error": f"Project directory '{args.project}' does not exist."}, indent=2))
        sys.exit(1)
        
    safe_run(args.project, args.name, args.cmd, cwd_override=args.cwd)

if __name__ == "__main__":
    main()
