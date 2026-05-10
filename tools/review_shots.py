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
        return {"status": "missing", "needs_review": True}
    
    try:
        # Get duration using ffprobe
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        duration_out = subprocess.check_output(cmd).decode().strip()
        if not duration_out:
            raise ValueError("No duration found")
        duration = float(duration_out)
        
        # Get resolution
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0", file_path
        ]
        resolution = subprocess.check_output(cmd).decode().strip()
        
        return {
            "status": "ok",
            "needs_review": False,
            "duration": duration,
            "resolution": resolution,
            "size_mb": os.path.getsize(file_path) / (1024 * 1024)
        }
    except Exception as e:
        return {
            "status": "corrupt", 
            "needs_review": True, 
            "error": str(e)
        }

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
        
        # Validation logic for duration
        expected_duration = shot.get("duration_sec", 5)
        if info["status"] == "ok":
            if abs(info["duration"] - expected_duration) > 0.5:
                info["status"] = "warning"
                info["needs_review"] = True
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
    warning_count = sum(1 for r in review_results.values() if r["status"] == "warning")
    missing_count = sum(1 for r in review_results.values() if r["status"] == "missing")
    corrupt_count = sum(1 for r in review_results.values() if r["status"] == "corrupt")

    logger.info("-" * 40)
    logger.info("REVIEW SUMMARY")
    logger.info(f"  OK:      {ok_count}")
    logger.info(f"  WARNING: {warning_count}")
    logger.info(f"  MISSING: {missing_count}")
    logger.info(f"  CORRUPT: {corrupt_count}")
    logger.info(f"  TOTAL:   {len(shots)}")
    logger.info("-" * 40)

if __name__ == "__main__":
    main()
