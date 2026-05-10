import os
import sys
import json
import argparse
import subprocess
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_video_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except:
        return 0.0

def extract_frame(video_path: str, output_path: str, timestamp: float):
    # Extract frame at specific timestamp
    cmd = [
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path,
        "-update", "1", "-q:v", "2", "-frames:v", "1", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

def main():
    parser = argparse.ArgumentParser(description="Link shots by using the last frame of the previous shot as the start of the next")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing continuity images")
    parser.add_argument("--suffix", default="continuity", help="Suffix for the new start image file")
    parser.add_argument("--no-update-plan", action="store_true", help="Do not update shot_plan.json")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    plan_path = os.path.join(project_dir, "shot_plan.json")
    
    if not os.path.exists(plan_path):
        logger.error(f"Shot plan not found: {plan_path}")
        sys.exit(1)

    with open(plan_path, 'r', encoding='utf-8') as f:
        shot_plan = json.load(f)
    
    shots = shot_plan.get("shots", [])
    plan_updated = False
    
    for i in range(1, len(shots)):
        prev_shot = shots[i-1]
        curr_shot = shots[i]
        
        prev_video_rel = prev_shot.get("output")
        prev_video_path = os.path.join(project_dir, prev_video_rel)
        
        if not os.path.exists(prev_video_path):
            logger.warning(f"Previous video not found for {curr_shot['id']}: {prev_video_rel}. Skipping continuity.")
            continue

        # Determine new filename (non-destructive)
        orig_start_rel = curr_shot.get("input_image")
        base, ext = os.path.splitext(orig_start_rel)
        # Avoid double suffixing if already linked
        if f"_{args.suffix}" in base:
            new_start_rel = orig_start_rel
        else:
            new_start_rel = f"{base}_{args.suffix}{ext}"
            
        new_start_path = os.path.join(project_dir, new_start_rel)
        
        if os.path.exists(new_start_path) and not args.force:
            logger.info(f"Continuity image already exists for {curr_shot['id']}: {new_start_rel}. Use --force to update.")
            if not args.no_update_plan and curr_shot.get("input_image") != new_start_rel:
                 curr_shot["input_image"] = new_start_rel
                 plan_updated = True
            continue

        logger.info(f"Linking {prev_shot['id']} -> {curr_shot['id']} (extracting continuity frame)")
        try:
            duration = get_video_duration(prev_video_path)
            seek_pos = max(0, duration - 0.05)
            
            os.makedirs(os.path.dirname(new_start_path), exist_ok=True)
            extract_frame(prev_video_path, new_start_path, seek_pos)
            logger.info(f"Saved continuity frame to: {new_start_rel}")
            
            if not args.no_update_plan:
                curr_shot["input_image"] = new_start_rel
                plan_updated = True
        except Exception as e:
            logger.error(f"Failed to extract continuity frame: {e}")

    if plan_updated and not args.no_update_plan:
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(shot_plan, f, indent=2, ensure_ascii=False)
        logger.info("Updated shot_plan.json with continuity image paths.")

if __name__ == "__main__":
    main()
