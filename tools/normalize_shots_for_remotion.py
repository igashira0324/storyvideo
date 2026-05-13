import os
import sys
import json
import argparse
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Normalize AI-generated shots to CFR 24fps for Remotion")
    parser.add_argument("--project", required=True, help="Project directory")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    shot_plan_path = os.path.join(project_dir, "shot_plan.json")
    
    if not os.path.exists(shot_plan_path):
        logger.error(f"Shot plan not found: {shot_plan_path}")
        sys.exit(1)

    with open(shot_plan_path, 'r', encoding='utf-8') as f:
        shot_plan = json.load(f)

    norm_dir = os.path.join(project_dir, "outputs", "remotion_norm")
    os.makedirs(norm_dir, exist_ok=True)

    fps = shot_plan.get("fps", 24)
    width = shot_plan.get("width", 720)
    height = shot_plan.get("height", 1280)

    for shot in shot_plan.get("shots", []):
        shot_id = shot["id"]
        input_path = os.path.join(project_dir, shot["output"])
        
        if not os.path.exists(input_path):
            logger.warning(f"Input video not found: {input_path}")
            continue

        output_name = os.path.basename(input_path)
        norm_path = os.path.join(norm_dir, output_name)
        
        duration_sec = shot.get("duration_sec", 6)
        shot_fps = shot.get("fps", fps)
        target_frames = int(duration_sec * shot_fps)

        logger.info(f"Normalizing {shot_id}: {width}x{height}, {shot_fps}fps CFR, {target_frames} frames")
        
        # ffmpeg command to normalize video for Remotion
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"fps={shot_fps},scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},tpad=stop_mode=clone:stop_duration=1,trim=start_frame=0:end_frame={target_frames},setpts=N/({shot_fps}*TB)",
            "-frames:v", str(target_frames),
            "-an",  # Remove audio to avoid issues in Remotion if unused
            "-r", str(shot_fps),
            "-fps_mode", "cfr",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            norm_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Successfully normalized {shot_id} -> {norm_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to normalize {shot_id}: {e.stderr.decode()}")

    logger.info("Normalization complete.")

if __name__ == "__main__":
    main()
