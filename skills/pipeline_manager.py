import os
import sys
import json
import subprocess
import argparse
import requests
import logging
import shutil
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoSkill:
    def __init__(self, project_dir):
        load_dotenv(find_dotenv())
        self.project_dir = os.path.abspath(project_dir)
        self.report_dir = os.path.join(self.project_dir, "reports")
        self.plan_path = os.path.join(self.project_dir, "shot_plan.json")
        self.comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
        
    def check_environment(self):
        env_status = {
            "comfyui": "offline",
            "ollama": "offline",
            "ffmpeg": "missing",
            "ffprobe": "missing",
            "node": "missing"
        }
        
        # Check ComfyUI
        try:
            res = requests.get(f"{self.comfyui_url}/system_stats", timeout=2)
            if res.status_code == 200:
                env_status["comfyui"] = "online"
        except:
            pass
            
        # Check Ollama
        try:
            res = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if res.status_code == 200:
                env_status["ollama"] = "online"
        except:
            pass
            
        # Check binaries
        for tool in ["ffmpeg", "ffprobe", "node"]:
            try:
                subprocess.run([tool, "-version"], capture_output=True, check=True)
                env_status[tool] = "installed"
            except:
                pass
                
        return env_status

    def get_status(self):
        status = {
            "project": os.path.basename(self.project_dir),
            "env": self.check_environment(),
            "has_plan": os.path.exists(self.plan_path),
            "num_shots": 0,
            "generated": 0,
            "reviewed": 0,
            "ai_passed": 0,
            "identity_passed": 0,
            "identity_failed": 0,
            "identity_skipped": 0,
            "needs_regeneration": 0,
            "start_images_total": 0,
            "start_images_existing": 0,
            "missing_start_images": [],
            "project_config": self.load_project_config()
        }
        
        plan_data = None
        if status["has_plan"]:
            try:
                with open(self.plan_path, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                    status["num_shots"] = len(plan_data.get("shots", []))
                    
                    # Check individual start images
                    for shot in plan_data.get("shots", []):
                        img = shot.get("input_image")
                        if img:
                            status["start_images_total"] += 1
                            img_path = os.path.join(self.project_dir, img)
                            if os.path.exists(img_path):
                                status["start_images_existing"] += 1
                            else:
                                status["missing_start_images"].append({
                                    "id": shot.get("id"),
                                    "input_image": img
                                })
            except Exception as e:
                logger.warning(f"Failed to read shot plan: {e}")
                status["has_plan"] = "error"
                
        gen_report = os.path.join(self.report_dir, "generation_report.json")
        if os.path.exists(gen_report):
            try:
                with open(gen_report, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    # FIX: report is a dict with "results" list
                    results = report.get("results", [])
                    status["generated"] = len([
                        s for s in results 
                        if s.get("status") in ["success", "skipped", "dry_run"]
                    ])
            except Exception as e:
                logger.warning(f"Failed to read generation report: {e}")
                
        rev_report = os.path.join(self.report_dir, "review_report.json")
        if os.path.exists(rev_report):
            try:
                with open(rev_report, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    if isinstance(report, dict):
                        status["reviewed"] = len(report)
                        status["ai_passed"] = len([s for s in report.values() if isinstance(s, dict) and s.get("ai_review", {}).get("quality_ok")])
                        status["needs_regeneration"] = len([s for s in report.values() if isinstance(s, dict) and s.get("needs_review")])
                    else:
                        logger.warning("Unexpected review_report format (not a dict)")
            except Exception as e:
                logger.warning(f"Failed to read review report: {e}")
                
        cons_report = os.path.join(self.report_dir, "character_consistency_report.json")
        if os.path.exists(cons_report):
            try:
                with open(cons_report, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    status["identity_passed"] = len([
                        s for s in report.values() 
                        if isinstance(s, dict) and s.get("same_character", False)
                    ])
                    status["identity_failed"] = len([
                        s for s in report.values() 
                        if isinstance(s, dict) and not s.get("same_character", False)
                    ])
                    # Count based on shot plan skips
                    status["identity_skipped"] = status["num_shots"] - (status["identity_passed"] + status["identity_failed"])
            except Exception as e:
                logger.warning(f"Failed to read consistency report: {e}")
                
        # Check Background Jobs
        jobs_data = self.check_jobs()
        status["running_jobs"] = jobs_data["running"]
        status["recent_jobs"] = jobs_data["recent"]
        
        # Determine Next Action
        next_action = "unknown"
        if status['env']['comfyui'] != "online" or status['env']['ollama'] != "online":
            next_action = "start_servers"
        elif status["running_jobs"]:
            next_action = "wait_for_jobs"
        elif not status['has_plan']:
            next_action = "create_plan"
        elif status['missing_start_images']:
            next_action = "generate_start_images"
        elif status['generated'] < status['num_shots']:
            next_action = "generate_shots"
        elif status['needs_regeneration'] > 0:
            next_action = "regenerate_failed"
        else:
            next_action = "finalize_timeline"
        
        status["next_action"] = next_action
        return status

    def load_project_config(self):
        config_path = os.path.join(self.project_dir, "project_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read project_config.json: {e}")
        return {}

    def cleanup_stale_jobs(self):
        job_dir = os.path.join(self.project_dir, "reports", "jobs")
        if not os.path.exists(job_dir):
            return 0
            
        stale_count = 0
        for f in os.listdir(job_dir):
            if f.endswith(".json"):
                path = os.path.join(job_dir, f)
                try:
                    with open(path, 'r') as jf:
                        data = json.load(jf)
                    
                    if data.get("status") == "running":
                        pid = data.get("pid")
                        if not pid or not self.is_pid_running(pid):
                            data["status"] = "stale"
                            data["note"] = "PID not found during cleanup"
                            data["finished_at"] = datetime.now().isoformat()
                            
                            with open(path, 'w') as jf:
                                json.dump(data, jf, indent=2)
                            
                            logger.info(f"Cleaned up stale job: {data.get('job_id')}")
                            stale_count += 1
                except Exception as e:
                    logger.error(f"Error cleaning up job file {f}: {e}")
        return stale_count

    def check_jobs(self):
        job_dir = os.path.join(self.project_dir, "reports", "jobs")
        if not os.path.exists(job_dir):
            return {"running": [], "recent": []}
            
        running = []
        recent = []
        
        # Sort files by date (newest first)
        files = sorted(os.listdir(job_dir), reverse=True)
        
        for f in files:
            if f.endswith(".json"):
                path = os.path.join(job_dir, f)
                try:
                    with open(path, 'r') as jf:
                        data = json.load(jf)
                        pid = data.get("pid")
                        status = data.get("status")
                        
                        if status == "running" and pid and self.is_pid_running(pid):
                            # Add log tail
                            log_path = data.get("log_path")
                            data["log_tail"] = self.get_log_tail(log_path)
                            running.append(data)
                        elif status in ["completed", "failed"]:
                            # Only keep a few recent ones
                            if len(recent) < 5:
                                log_path = data.get("log_path")
                                data["log_tail"] = self.get_log_tail(log_path, lines=5)
                                recent.append(data)
                except:
                    pass
        return {"running": running, "recent": recent}

    def is_pid_running(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def get_log_tail(self, path, lines=20):
        if not path or not os.path.exists(path):
            return ""
        try:
            # Use tail command for efficiency
            res = subprocess.run(["tail", "-n", str(lines), path], capture_output=True, text=True)
            return res.stdout
        except:
            return "Could not read log tail."

    def print_summary(self):
        s = self.get_status()
        print(f"\n=== Project Monitor: {s['project']} ===")
        
        print("\n[Environment Check]")
        for k, v in s['env'].items():
            icon = "✅" if v in ["online", "installed"] else "❌"
            print(f"{icon} {k.upper()}: {v}")
            
        print("\n[Pipeline Progress]")
        print(f"Shot Plan:  {'[OK]' if s['has_plan'] is True else '[ERROR]' if s['has_plan'] == 'error' else '[MISSING]'}")
        print(f"Start Imgs: {s['start_images_existing']}/{s['start_images_total']} images")
        print(f"Generated:  {s['generated']}/{s['num_shots']} shots")
        print(f"Reviewed:   {s['reviewed']}/{s['num_shots']} shots")
        print(f"AI Passed:  {s['ai_passed']}/{s['num_shots']} shots")
        print(f"Identity:   {s['identity_passed']} PASSED, {s['identity_failed']} FAILED, {s['identity_skipped']} SKIPPED")
        print(f"To Re-gen:  {s['needs_regeneration']}")
        
        config = s.get("project_config", {})
        if config:
            print("\n[Workflow Policy]")
            if "t2i_preset" in config:
                print(f"T2I Preset: {config['t2i_preset']}")
            if "i2v_preset" in config:
                print(f"I2V Preset: {config['i2v_preset']}")
            if "model" in config:
                print(f"Primary Model: {config['model']}")
        
        if s["running_jobs"]:
            print("\n[Running Background Jobs]")
            for job in s["running_jobs"]:
                print(f"🚀 {job['name']} (PID: {job['pid']})")
                print(f"   Log tail:\n---\n{job['log_tail']}---")
        
        if s["recent_jobs"]:
            print("\n[Recent Jobs]")
            for job in s["recent_jobs"]:
                icon = "✅" if job['status'] == "completed" else "❌"
                print(f"{icon} {job['name']} ({job['status']}) - {job.get('finished_at', 'unknown')}")
                if job['status'] == "failed":
                    print(f"   Log tail (last 5 lines):\n---\n{job['log_tail']}---")
            
        print(f"\n[Suggested Next Action: {s['next_action'].upper()}]")
        if s['next_action'] == "wait_for_jobs":
            print("Action: Background jobs are running. Monitor logs or wait for completion.")
        elif s['next_action'] == "start_servers":
            print("CRITICAL: Ensure ComfyUI and Ollama servers are running.")
        elif s['next_action'] == "create_plan":
            print("Action: Run 'tools/story_planner.py' to create a shot plan.")
        elif s['next_action'] == "generate_start_images":
            print("Action: Run 'tools/generate_start_images.py' followed by 'tools/generate_shots.py'.")
        elif s['next_action'] == "generate_shots":
            print("Action: Resume generation with 'tools/generate_shots.py --skip-existing'.")
        elif s['next_action'] == "regenerate_failed":
            print("Action: Run 'tools/regenerate_failed_shots.py --max-rounds 3 --auto-review'.")
        elif s['next_action'] == "finalize_timeline":
            print("Action: Finalize with 'tools/build_remotion_timeline.py' and render.")

    def print_handoff(self):
        s = self.get_status()
        print(f"=== Session Handoff: {s['project']} ===")
        print(f"Current Phase: {s['next_action'].upper()}")
        print(f"Progress: StartImg={s['start_images_existing']}/{s['start_images_total']}, Videos={s['generated']}/{s['num_shots']}, Reviewed={s['reviewed']}/{s['num_shots']}")
        
        if s["running_jobs"]:
            print("Active Jobs:")
            for j in s["running_jobs"]:
                print(f"- {j['name']} (PID: {j['pid']})")
        
        print("\nLast Log Tails:")
        all_jobs = s["running_jobs"] + s["recent_jobs"]
        for job in all_jobs[:2]:
            print(f"--- {job['name']} ---")
            print(job["log_tail"])
        print("--- END HANDOFF ---")

    def backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"_backup_{timestamp}"
        backup_path = os.path.join(self.project_dir, backup_name)
        
        logger.info(f"Starting backup of {self.project_dir} to {backup_path}...")
        
        # Files and dirs to backup
        targets = ["outputs", "reports", "shot_plan.json", "assets"]
        os.makedirs(backup_path, exist_ok=True)
        
        for item in targets:
            src = os.path.join(self.project_dir, item)
            dst = os.path.join(backup_path, item)
            if os.path.exists(src):
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                logger.info(f"Backed up: {item}")
        
        print(f"\n✅ Backup created successfully at: {backup_path}")
        return backup_path

    def init_state(self):
        state_path = os.path.join(self.project_dir, "PROJECT_STATE.md")
        if os.path.exists(state_path):
            print(f"PROJECT_STATE.md already exists at {state_path}")
            return
            
        project_name = os.path.basename(self.project_dir)
        template = f"""# Project State: {project_name}

Last updated: {datetime.now().strftime("%Y-%m-%d")}

## Current Status
- **Phase**: Setup
- **Shot Plan**: [ ]
- **Workflows**: [ ]
- **Assets**: 0/0 generated
- **Videos**: 0/0 generated

## Next Actions
1. [ ] Finalize brief.txt
2. [ ] Run `tools/story_planner.py`
3. [ ] Run `tools/generate_start_images.py`
4. [ ] Run `tools/generate_shots.py`

## Workflow Policy
- **T2I**: workflow_presets/ernie_image_turbo.json
- **I2V**: workflow_presets/ltx23_i2v.json

## Notes
- Use `skills/safe_run.py` for long jobs.
"""
        with open(state_path, 'w', encoding='utf-8') as f:
            f.write(template)
        print(f"✅ Created PROJECT_STATE.md template at {state_path}")

def main():
    parser = argparse.ArgumentParser(description="Antigravity Pipeline Manager Skill")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--status", action="store_true", help="Print current project status summary")
    parser.add_argument("--handoff", action="store_true", help="Print concise handoff summary")
    parser.add_argument("--backup", action="store_true", help="Create a timestamped backup of project data")
    parser.add_argument("--cleanup-stale-jobs", action="store_true", help="Mark running jobs with no active PID as stale")
    parser.add_argument("--init-state", action="store_true", help="Create a PROJECT_STATE.md template")
    parser.add_argument("--json", action="store_true", help="Output status as JSON")
    args = parser.parse_args()
    
    if not os.path.exists(args.project):
        print(f"Error: Project directory '{args.project}' does not exist.")
        sys.exit(1)
        
    skill = VideoSkill(args.project)
    
    if args.json:
        status = skill.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    elif args.handoff:
        skill.print_handoff()
    elif args.backup:
        skill.backup()
    elif args.cleanup_stale_jobs:
        count = skill.cleanup_stale_jobs()
        print(f"Cleaned up {count} stale jobs.")
    elif args.init_state:
        skill.init_state()
    elif args.status:
        skill.print_summary()
    else:
        skill.print_summary()

if __name__ == "__main__":
    main()
