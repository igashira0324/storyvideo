import os
import sys
import json
import argparse
import logging
import subprocess
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_video(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {"status": "missing"}
    
    try:
        # Get duration using ffprobe
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        duration = float(subprocess.check_output(cmd).decode().strip())
        
        # Get resolution
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0", file_path
        ]
        resolution = subprocess.check_output(cmd).decode().strip()
        
        return {
            "status": "ok",
            "duration": duration,
            "resolution": resolution,
            "size_mb": os.path.getsize(file_path) / (1024 * 1024)
        }
    except Exception as e:
        return {"status": "corrupt", "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Review generated shots for a project")
    parser.add_argument("--project", required=True, help="Project directory")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    plan_path = os.path.join(project_dir, "shot_plan.json")
    
    if not os.path.exists(plan_path):
        logger.error(f"Shot plan not found: {plan_path}")
        sys.exit(1)

    shot_plan = json.load(open(plan_path, 'r'))
    shots = shot_plan.get("shots", [])
    
    review_results = {}
    
    for shot in shots:
        shot_id = shot["id"]
        output_rel = shot.get("output")
        output_path = os.path.join(project_dir, output_rel)
        
        logger.info(f"Reviewing shot: {shot_id}")
        info = check_video(output_path)
        
        # Validation logic
        expected_duration = shot.get("duration_sec", 5)
        if info["status"] == "ok":
            if abs(info["duration"] - expected_duration) > 0.5:
                info["warning"] = f"Duration mismatch: expected {expected_duration}s, got {info['duration']}s"
        
        review_results[shot_id] = info

    # Save review report
    report_path = os.path.join(project_dir, "reports", "review_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(review_results, f, indent=2)
    
    logger.info(f"Review report saved to: {report_path}")
    
    # Print summary
    ok_count = sum(1 for r in review_results.values() if r["status"] == "ok")
    logger.info(f"Summary: {ok_count}/{len(shots)} shots are OK.")

if __name__ == "__main__":
    main()
