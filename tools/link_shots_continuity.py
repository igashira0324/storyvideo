import os
import sys
import json
import argparse
import subprocess
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_last_frame(video_path: str, output_path: str):
    # Extract the very last frame using ffmpeg
    # We use -sseof -0.1 to jump to the end and take one frame
    cmd = [
        "ffmpeg", "-y", "-sseof", "-0.1", "-i", video_path,
        "-update", "1", "-q:v", "2", "-frames:v", "1", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

def main():
    parser = argparse.ArgumentParser(description="Link shots by using the last frame of the previous shot as the start of the next")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing start images")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    plan_path = os.path.join(project_dir, "shot_plan.json")
    
    if not os.path.exists(plan_path):
        logger.error(f"Shot plan not found: {plan_path}")
        sys.exit(1)

    with open(plan_path, 'r') as f:
        shot_plan = json.load(f)
    
    shots = shot_plan.get("shots", [])
    
    for i in range(1, len(shots)):
        prev_shot = shots[i-1]
        curr_shot = shots[i]
        
        prev_video_rel = prev_shot.get("output")
        prev_video_path = os.path.join(project_dir, prev_video_rel)
        
        curr_start_rel = curr_shot.get("input_image")
        curr_start_path = os.path.join(project_dir, curr_start_rel)
        
        if not os.path.exists(prev_video_path):
            logger.warning(f"Previous video not found for {curr_shot['id']}: {prev_video_rel}. Skipping continuity.")
            continue
            
        if os.path.exists(curr_start_path) and not args.force:
            logger.info(f"Start image already exists for {curr_shot['id']}. Use --force to overwrite with continuity frame.")
            continue

        logger.info(f"Linking {prev_shot['id']} -> {curr_shot['id']} (extracting continuity frame)")
        try:
            os.makedirs(os.path.dirname(curr_start_path), exist_ok=True)
            extract_last_frame(prev_video_path, curr_start_path)
            logger.info(f"Saved continuity frame to: {curr_start_rel}")
        except Exception as e:
            logger.error(f"Failed to extract continuity frame: {e}")

if __name__ == "__main__":
    main()
