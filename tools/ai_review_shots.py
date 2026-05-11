import os
import sys
import json
import argparse
import logging
import subprocess
import requests
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
    for i in range(num_frames):
        # Extract frames at 10%, 50%, 90%
        time_pos = duration * (0.1 + 0.4 * i) if num_frames > 1 else duration * 0.5
        frame_filename = f"frame_{i}.jpg"
        frame_path = os.path.join(output_dir, frame_filename)
        
        cmd = [
            "ffmpeg", "-y", "-ss", str(time_pos), "-i", video_path,
            "-frames:v", "1", "-q:v", "2", frame_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        frame_paths.append(frame_path)
    
    return frame_paths

def ask_vlm(image_paths: List[str], prompt: str, model: str, url: str) -> Dict[str, Any]:
    # Encode images to base64 for Ollama
    import base64
    images_base64 = []
    for p in image_paths:
        with open(p, "rb") as f:
            images_base64.append(base64.b64encode(f.read()).decode('utf-8'))
    
    vlm_prompt = f"""
Analyze these frames from an AI-generated video.
Target Prompt: "{prompt}"

Does the video content match the prompt? 
Are there major visual distortions (deformed faces, flickering, logic errors)?

Respond in JSON format:
{{
  "matches_prompt": true/false,
  "prompt_match_score": <float, 0.0 to 1.0>,
  "quality_ok": true/false,
  "visual_quality_score": <float, 0.0 to 1.0>,
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
        # Some models use 'thinking' or 'response'
        text = data.get("response") or data.get("thinking")
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse VLM response: {e}")
        return {
            "matches_prompt": False, 
            "prompt_match_score": 0.0,
            "quality_ok": False, 
            "visual_quality_score": 0.0,
            "reason": f"Failed to parse AI review response: {e}"
        }

def main():
    parser = argparse.ArgumentParser(description="AI Quality Review of generated shots using VLM")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--model", default="minicpm-v", help="Ollama VLM model name")
    parser.add_argument("--url", default="http://127.0.0.1:11434", help="Ollama API URL")
    parser.add_argument("--num-frames", type=int, default=3, help="Number of frames to extract for review")
    parser.add_argument("--prompt-score-threshold", type=float, default=0.7, help="Minimum prompt match score")
    parser.add_argument("--quality-score-threshold", type=float, default=0.7, help="Minimum visual quality score")
    parser.add_argument("--only", nargs="+", help="Specific shot IDs to review")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    report_path = os.path.join(project_dir, "reports", "review_report.json")
    plan_path = os.path.join(project_dir, "shot_plan.json")
    
    if not os.path.exists(report_path) or not os.path.exists(plan_path):
        logger.error("Review report or shot plan not found. Run review_shots.py first.")
        sys.exit(1)

    with open(report_path, 'r') as f:
        review_report = json.load(f)
    with open(plan_path, 'r') as f:
        shot_plan = json.load(f)
    
    shots_map = {s["id"]: s for s in shot_plan.get("shots", [])}
    
    for shot_id, info in review_report.items():
        if args.only and shot_id not in args.only:
            continue
            
        if info["status"] != "ok":
            continue # Already marked for review
            
        shot_data = shots_map.get(shot_id)
        video_rel = shot_data.get("output")
        video_path = os.path.join(project_dir, video_rel)
        
        if not os.path.exists(video_path):
            continue

        logger.info(f"AI Reviewing shot: {shot_id} (frames: {args.num_frames})")
        temp_dir = os.path.join(project_dir, "temp", shot_id)
        frame_paths = extract_frames(video_path, temp_dir, num_frames=args.num_frames)
        
        vlm_res = ask_vlm(frame_paths, shot_data["positive_prompt"], args.model, args.url)
        
        info["ai_review"] = vlm_res
        
        matches_prompt = vlm_res.get("matches_prompt", True)
        prompt_score = vlm_res.get("prompt_match_score", 1.0)
        quality_ok = vlm_res.get("quality_ok", True)
        quality_score = vlm_res.get("visual_quality_score", 1.0)
        
        rejected = (
            not matches_prompt or 
            prompt_score < args.prompt_score_threshold or
            not quality_ok or
            quality_score < args.quality_score_threshold
        )

        if rejected:
            info["status"] = "ai_rejected"
            info["needs_review"] = True
            logger.warning(f"Shot {shot_id} REJECTED by AI (Prompt: {prompt_score}, Quality: {quality_score}): {vlm_res.get('reason')}")
        else:
            logger.info(f"Shot {shot_id} PASSED AI Review (Prompt: {prompt_score}, Quality: {quality_score})")

    # Update report
    with open(report_path, 'w') as f:
        json.dump(review_report, f, indent=2)
    
    logger.info(f"AI Review complete. Updated report at: {report_path}")

if __name__ == "__main__":
    main()
