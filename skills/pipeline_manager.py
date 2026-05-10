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
            "needs_regeneration": 0,
            "start_images_total": 0,
            "start_images_existing": 0,
            "missing_start_images": []
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
                
        # Check Background Jobs
        status["running_jobs"] = self.check_jobs()
        
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

    def check_jobs(self):
        job_dir = os.path.join(self.project_dir, "reports", "jobs")
        if not os.path.exists(job_dir):
            return []
            
        jobs = []
        for f in os.listdir(job_dir):
            if f.endswith(".json"):
                path = os.path.join(job_dir, f)
                try:
                    with open(path, 'r') as jf:
                        data = json.load(jf)
                        pid = data.get("pid")
                        if pid and self.is_pid_running(pid):
                            # Add log tail
                            log_path = data.get("log_path")
                            data["log_tail"] = self.get_log_tail(log_path)
                            jobs.append(data)
                except:
                    pass
        return jobs

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
        print(f"To Re-gen:  {s['needs_regeneration']}")
        
        if s["running_jobs"]:
            print("\n[Running Background Jobs]")
            for job in s["running_jobs"]:
                print(f"🚀 {job['name']} (PID: {job['pid']})")
                print(f"   Log tail:\n---\n{job['log_tail']}---")
            
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

def main():
    parser = argparse.ArgumentParser(description="Antigravity Pipeline Manager Skill")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--status", action="store_true", help="Print current project status summary")
    parser.add_argument("--backup", action="store_true", help="Create a timestamped backup of project data")
    parser.add_argument("--json", action="store_true", help="Output status as JSON")
    args = parser.parse_args()
    
    if not os.path.exists(args.project):
        print(f"Error: Project directory '{args.project}' does not exist.")
        sys.exit(1)
        
    skill = VideoSkill(args.project)
    
    if args.status:
        skill.print_summary()

    if args.backup:
        skill.backup()

    if args.json:
        status = skill.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
