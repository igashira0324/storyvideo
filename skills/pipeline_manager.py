import os
import sys
import json
import subprocess
import argparse
import requests
import logging
import shutil
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoSkill:
    def __init__(self, project_dir):
        self.project_dir = os.path.abspath(project_dir)
        self.report_dir = os.path.join(self.project_dir, "reports")
        self.plan_path = os.path.join(self.project_dir, "shot_plan.json")
        
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
            # We use a common default, but in a real scenario we'd read .env
            res = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
            if res.status_code == 200:
                env_status["comfyui"] = "online"
        except:
            pass
            
        # Check Ollama
        try:
            res = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
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
            "assets_exist": os.path.exists(os.path.join(self.project_dir, "assets"))
        }
        
        if status["has_plan"]:
            try:
                with open(self.plan_path, 'r', encoding='utf-8') as f:
                    plan = json.load(f)
                    status["num_shots"] = len(plan.get("shots", []))
            except:
                status["has_plan"] = "error"
                
        gen_report = os.path.join(self.report_dir, "generation_report.json")
        if os.path.exists(gen_report):
            try:
                with open(gen_report, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    status["generated"] = len([s for s in report.values() if s.get("status") == "success"])
            except:
                pass
                
        rev_report = os.path.join(self.report_dir, "review_report.json")
        if os.path.exists(rev_report):
            try:
                with open(rev_report, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    status["reviewed"] = len(report)
                    status["ai_passed"] = len([s for s in report.values() if s.get("ai_review", {}).get("quality_ok")])
                    status["needs_regeneration"] = len([s for s in report.values() if s.get("needs_review")])
            except:
                pass
                
        return status

    def print_summary(self):
        s = self.get_status()
        print(f"\n=== Project Monitor: {s['project']} ===")
        
        print("\n[Environment Check]")
        for k, v in s['env'].items():
            icon = "✅" if v in ["online", "installed"] else "❌"
            print(f"{icon} {k.upper()}: {v}")
            
        print("\n[Pipeline Progress]")
        print(f"Shot Plan:  {'[OK]' if s['has_plan'] is True else '[ERROR]' if s['has_plan'] == 'error' else '[MISSING]'}")
        print(f"Generated:  {s['generated']}/{s['num_shots']} shots")
        print(f"Reviewed:   {s['reviewed']}/{s['num_shots']} shots")
        print(f"AI Passed:  {s['ai_passed']}/{s['num_shots']} shots")
        print(f"To Re-gen:  {s['needs_regeneration']}")
        
        print("\n[Suggested Next Action]")
        if s['env']['comfyui'] != "online" or s['env']['ollama'] != "online":
            print("CRITICAL: Ensure ComfyUI and Ollama servers are running.")
        elif not s['has_plan']:
            print("Action: Run 'tools/story_planner.py' to create a shot plan.")
        elif s['generated'] == 0 and s['num_shots'] > 0:
            print("Action: Run 'tools/generate_start_images.py' followed by 'tools/generate_shots.py'.")
        elif s['generated'] < s['num_shots']:
            print("Action: Resume generation with 'tools/generate_shots.py --skip-existing'.")
        elif s['needs_regeneration'] > 0:
            print("Action: Run 'tools/regenerate_failed_shots.py --max-rounds 3 --auto-review'.")
        else:
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
    args = parser.parse_args()
    
    if not os.path.exists(args.project):
        print(f"Error: Project directory '{args.project}' does not exist.")
        sys.exit(1)
        
    skill = VideoSkill(args.project)
    if args.status:
        skill.print_summary()
    if args.backup:
        skill.backup()

if __name__ == "__main__":
    main()
