import os
import sys
import json
import argparse
import logging
from typing import Any, Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Build Remotion timeline from shot plan and generation report")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--remotion-dir", required=True, help="Remotion project directory")
    args = parser.parse_args()
    
    project_dir = os.path.abspath(args.project)
    remotion_dir = os.path.abspath(args.remotion_dir)
    
    shot_plan_path = os.path.join(project_dir, "shot_plan.json")
    report_path = os.path.join(project_dir, "reports", "generation_report.json")
    
    if not os.path.exists(shot_plan_path):
        logger.error(f"Shot plan not found: {shot_plan_path}")
        sys.exit(1)
        
    shot_plan = json.load(open(shot_plan_path))
    report = {}
    if os.path.exists(report_path):
        report = json.load(open(report_path))
    else:
        logger.warning(f"Generation report not found at {report_path}. Proceeding with all shots from plan.")

    # Prepare public directory and symlink
    public_dir = os.path.join(remotion_dir, "public")
    os.makedirs(public_dir, exist_ok=True)

    project_name = os.path.basename(project_dir)
    target_link = os.path.join(public_dir, project_name)

    if not os.path.exists(target_link):
        os.symlink(project_dir, target_link)
        logger.info(f"Created symlink: {target_link} -> {project_dir}")

    # Prepare shots for Remotion
    remotion_shots = []
    fps = shot_plan.get("fps", 24)
    
    for shot in shot_plan.get("shots", []):
        shot_id = shot["id"]
        
        if report:
            shot_report = next((r for r in report.get("results", []) if r["id"] == shot_id), None)
            if shot_report and shot_report["status"] not in ["success", "skipped"]:
                logger.warning(f"Skipping shot {shot_id} because it failed generation.")
                continue

        # Remotion expects path relative to 'public' folder
        video_rel_path = shot["output"] # e.g. "outputs/shot_001.mp4"
        remotion_path = f"{project_name}/{video_rel_path}"
        
        narration_rel_path = shot.get("narration")
        remotion_narration_path = None
        if narration_rel_path:
            remotion_narration_path = f"{project_name}/{narration_rel_path}"

        remotion_shots.append({
            "id": shot_id,
            "path": remotion_path,
            "duration_frames": int(shot.get("duration_sec", 5) * shot.get("fps", fps)),
            "subtitle": shot.get("subtitle"),
            "narration_path": remotion_narration_path
        })
        
    # Write to remotion/src/shots.json
    src_dir = os.path.join(remotion_dir, "src")
    os.makedirs(src_dir, exist_ok=True)
    
    shots_output_path = os.path.join(src_dir, "shots.json")
    with open(shots_output_path, "w") as f:
        json.dump(remotion_shots, f, indent=2)
    logger.info(f"Remotion shots saved to: {shots_output_path}")

    # Generate Remotion Config
    config = {
        "compositionName": shot_plan.get("composition_name", "FinalVideo"),
        "width": shot_plan.get("width", 1280),
        "height": shot_plan.get("height", 720),
        "fps": shot_plan.get("fps", 24),
        "bgmPath": f"{project_name}/{shot_plan['bgm']}" if shot_plan.get("bgm") else None
    }
    
    config_path = os.path.join(src_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    logger.info(f"Remotion config saved to: {config_path}")

if __name__ == "__main__":
    main()
