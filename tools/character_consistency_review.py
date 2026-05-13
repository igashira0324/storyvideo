import os
import sys
import json
import argparse
import logging
import subprocess
import requests
import base64
from typing import Any, Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_frames(video_path: str, output_dir: str, num_frames: int = 3) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    
    # Get duration
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    duration = float(subprocess.check_output(cmd).decode().strip())
    
    frame_paths = []
    if num_frames <= 1:
        time_positions = [duration * 0.5]
    else:
        # Sample frames from 10% to 90% of duration
        time_positions = [duration * (0.1 + 0.8 * i / (num_frames - 1)) for i in range(num_frames)]
    
    for i, time_pos in enumerate(time_positions):
        # Ensure time_pos is within valid range [0.1, duration - 0.1]
        time_pos = min(max(time_pos, 0.1), max(duration - 0.1, 0.1))
        
        frame_filename = f"frame_cons_{i}.jpg"
        frame_path = os.path.join(output_dir, frame_filename)
        
        cmd = [
            "ffmpeg", "-y", "-ss", str(time_pos), "-i", video_path,
            "-frames:v", "1", "-q:v", "2", frame_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        frame_paths.append(frame_path)
    
    return frame_paths

def ask_vlm_consistency(ref_image_path: str, shot_image_paths: List[str], identity_info: Dict[str, Any], model: str, url: str) -> Dict[str, Any]:
    images_base64 = []
    
    # Add reference image first
    with open(ref_image_path, "rb") as f:
        images_base64.append(base64.b64encode(f.read()).decode('utf-8'))
        
    # Add shot frames
    for p in shot_image_paths:
        with open(p, "rb") as f:
            images_base64.append(base64.b64encode(f.read()).decode('utf-8'))
    
    vlm_prompt = f"""
You are reviewing character identity consistency in an AI-generated music video.

Reference character details:
- Display Name: {identity_info.get('display_name', 'Subject')}
- Identity Description: {identity_info.get('identity_prompt', 'Same character as reference')}

The first image provided is the REFERENCE image.
The subsequent images are frames from a generated video shot.

Compare the reference image and the video frames. 
Do these frames depict the SAME character identity? Focus on face, hair, and costume consistency.

Respond in JSON format:
{{
  "same_character": true/false,
  "identity_score": <float, 0.0 to 1.0>,
  "hair_consistency": <float, 0.0 to 1.0>,
  "face_consistency": <float, 0.0 to 1.0>,
  "costume_consistency": <float, 0.0 to 1.0>,
  "reason": "short explanation"
}}
"""

    payload = {
        "model": model,
        "prompt": vlm_prompt,
        "images": images_base64,
        "stream": False,
        "format": "json"
    }
    
    response = requests.post(f"{url}/api/generate", json=payload, timeout=300)
    response.raise_for_status()
    data = response.json()
    
    try:
        text = data.get("response") or data.get("thinking")
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse VLM response: {e}")
        return {
            "same_character": False,
            "identity_score": 0.0,
            "reason": f"Failed to parse AI consistency response: {e}"
        }

def main():
    parser = argparse.ArgumentParser(description="Character Consistency Review using VLM")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--model", default="minicpm-v", help="Ollama VLM model name")
    parser.add_argument("--url", default="http://127.0.0.1:11434", help="Ollama API URL")
    parser.add_argument("--num-frames", type=int, default=2, help="Number of frames per shot to review")
    parser.add_argument("--threshold", type=float, help="Minimum identity score (overrides character_identity.json)")
    parser.add_argument("--only", nargs="+", help="Specific shot IDs to review")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    identity_path = os.path.join(project_dir, "character_identity.json")
    report_path = os.path.join(project_dir, "reports", "review_report.json")
    plan_path = os.path.join(project_dir, "shot_plan.json")
    cons_report_path = os.path.join(project_dir, "reports", "character_consistency_report.json")
    
    if not os.path.exists(identity_path):
        logger.error("character_identity.json not found.")
        sys.exit(1)

    with open(identity_path, 'r') as f:
        identity_info = json.load(f)
    
    if not identity_info.get("enabled"):
        logger.info("Character identity review disabled in config.")
        return

    ref_img_rel = identity_info["reference_images"][0]
    ref_img_path = os.path.join(project_dir, ref_img_rel)
    
    if not os.path.exists(ref_img_path):
        logger.error(f"Reference image not found: {ref_img_path}")
        sys.exit(1)

    if not os.path.exists(report_path) or not os.path.exists(plan_path):
        logger.error("Review report or shot plan not found. Run review_shots.py first.")
        sys.exit(1)

    with open(report_path, 'r') as f:
        review_report = json.load(f)
    with open(plan_path, 'r') as f:
        shot_plan = json.load(f)
    
    shots_map = {s["id"]: s for s in shot_plan.get("shots", [])}
    consistency_results = {}
    
    # Resolve threshold
    threshold = args.threshold
    if threshold is None:
        threshold = float(identity_info.get("identity_score_threshold", 0.75))
    logger.info(f"Using identity score threshold: {threshold}")

    for shot_id, info in review_report.items():
        if args.only and shot_id not in args.only:
            continue
            
        shot_data = shots_map.get(shot_id)
        if not shot_data:
            continue
            
        if shot_data.get("identity_review") is False:
            logger.info(f"Skipping identity review for {shot_id} (identity_review: false)")
            continue

        video_rel = shot_data.get("output")
        video_path = os.path.join(project_dir, video_rel)
        
        if not os.path.exists(video_path):
            continue

        logger.info(f"Checking character consistency for shot: {shot_id}")
        temp_dir = os.path.join(project_dir, "temp", shot_id)
        frame_paths = extract_frames(video_path, temp_dir, num_frames=args.num_frames)
        
        res = ask_vlm_consistency(ref_img_path, frame_paths, identity_info, args.model, args.url)
        consistency_results[shot_id] = res
        
        # Embed result into review report
        info["character_consistency"] = res
        
        score = res.get("identity_score", 0.0)
        passed = res.get("same_character", False) and score >= threshold
        
        if not passed:
            info["status"] = "identity_rejected"
            info["needs_review"] = True
            logger.warning(f"Shot {shot_id} REJECTED by Character Identity Review (Score: {score}): {res.get('reason')}")
        else:
            info["needs_review"] = False
            if info.get("status") == "identity_rejected":
                info["status"] = "ok"
            logger.info(f"Shot {shot_id} PASSED Character Identity Review (Score: {score})")

    # Save reports
    with open(cons_report_path, 'w') as f:
        json.dump(consistency_results, f, indent=2)
    
    with open(report_path, 'w') as f:
        json.dump(review_report, f, indent=2)
    
    logger.info(f"Character consistency review complete. Saved to: {cons_report_path}")

if __name__ == "__main__":
    main()
