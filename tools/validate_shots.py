import os
import sys
import json
import argparse
import subprocess
import logging
from typing import Any, Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_video_info(file_path: str) -> Dict[str, Any]:
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration:stream=width,height,avg_frame_rate", 
            "-of", "json", 
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"Error probing file {file_path}: {e}")
        return {}

def validate_shot(shot: Dict[str, Any], project_dir: str) -> Dict[str, Any]:
    shot_id = shot["id"]
    output_path = os.path.join(project_dir, shot["output"])
    
    validation = {
        "id": shot_id,
        "path": output_path,
        "exists": False,
        "valid": False,
        "errors": []
    }
    
    if not os.path.exists(output_path):
        validation["errors"].append("File not found")
        return validation
        
    validation["exists"] = True
    info = get_video_info(output_path)
    
    if not info:
        validation["errors"].append("Could not probe video info")
        return validation
        
    # Check resolution
    stream = info.get("streams", [{}])[0]
    width = stream.get("width")
    height = stream.get("height")
    
    # Check duration
    duration = float(info.get("format", {}).get("duration", 0))
    target_duration = shot.get("duration_sec", 0)
    
    if abs(duration - target_duration) > 0.5: # 0.5s tolerance
        validation["errors"].append(f"Duration mismatch: found {duration:.2f}s, expected {target_duration}s")
        
    if not validation["errors"]:
        validation["valid"] = True
        logger.info(f"Shot {shot_id} is VALID ({width}x{height}, {duration:.2f}s)")
    else:
        logger.error(f"Shot {shot_id} INVALID: {', '.join(validation['errors'])}")
        
    return validation

def main():
    parser = argparse.ArgumentParser(description="Validate generated video shots")
    parser.add_argument("--project", required=True, help="Project directory")
    args = parser.parse_args()
    
    project_dir = os.path.abspath(args.project)
    shot_plan_path = os.path.join(project_dir, "shot_plan.json")
    
    if not os.path.exists(shot_plan_path):
        logger.error(f"Shot plan not found: {shot_plan_path}")
        sys.exit(1)
        
    shot_plan = json.load(open(shot_plan_path))
    shots = shot_plan.get("shots", [])
    
    results = []
    for shot in shots:
        res = validate_shot(shot, project_dir)
        results.append(res)
        
    valid_count = sum(1 for r in results if r["valid"])
    logger.info(f"Validation complete: {valid_count}/{len(results)} shots are valid.")
    
    # Save validation report
    report_path = os.path.join(project_dir, "validation_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Validation report saved to: {report_path}")

if __name__ == "__main__":
    main()
