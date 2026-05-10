import os
import sys
import json
import argparse
import subprocess
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_regeneration(project_dir: str, failed_shots: List[str]):
    # Update seeds in shot_plan.json
    import random
    plan_path = os.path.join(project_dir, "shot_plan.json")
    with open(plan_path, 'r', encoding='utf-8') as f:
        shot_plan = json.load(f)
    
    for shot in shot_plan.get("shots", []):
        if shot["id"] in failed_shots:
            old_seed = shot.get("seed", 42)
            # Track history
            history = shot.setdefault("seed_history", [])
            history.append(old_seed)
            
            new_seed = random.randint(1, 2**32 - 1)
            shot["seed"] = new_seed
            logger.info(f"Updated seed for {shot['id']}: {old_seed} -> {new_seed} (History: {history})")
            
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(shot_plan, f, indent=2, ensure_ascii=False)
    
    # Construct the command to run generate_shots.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generate_script = os.path.join(script_dir, "generate_shots.py")

    cmd = [
        sys.executable,
        generate_script,
        "--project", project_dir,
        "--only"
    ] + failed_shots

    logger.info(f"Executing regeneration: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser(description="Regenerate shots marked as 'needs_review' in the review report")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--max-rounds", type=int, default=1, help="Maximum number of regeneration rounds")
    parser.add_argument("--auto-review", action="store_true", help="Automatically run review scripts after regeneration")
    parser.add_argument("--vlm-model", default="minicpm-v", help="VLM model for auto-review")
    parser.add_argument("--only", nargs="+", help="Specific shot IDs to allow for regeneration")
    args = parser.parse_args()

    if args.max_rounds < 1:
        logger.error("--max-rounds must be >= 1")
        sys.exit(1)

    project_dir = os.path.abspath(args.project)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(project_dir, "reports", "review_report.json")
    
    for round_num in range(1, args.max_rounds + 1):
        logger.info(f"--- Regeneration Round {round_num} ---")
        
        if not os.path.exists(report_path):
            logger.error(f"Review report not found: {report_path}")
            sys.exit(1)

        with open(report_path, 'r') as f:
            review_report = json.load(f)

        failed_shots = [shot_id for shot_id, info in review_report.items() if info.get("needs_review")]
        
        if args.only:
            failed_shots = [s for s in failed_shots if s in args.only]

        if not failed_shots:
            logger.info("No shots found that need review (filtered by --only). Loop complete.")
            break

        logger.info(f"Found {len(failed_shots)} shots that need review.")
        run_regeneration(project_dir, failed_shots)

        if args.auto_review:
            logger.info("Running automatic review...")
            subprocess.run([sys.executable, os.path.join(script_dir, "review_shots.py"), "--project", project_dir], check=True)
            subprocess.run([sys.executable, os.path.join(script_dir, "ai_review_shots.py"), "--project", project_dir, "--model", args.vlm_model], check=True)
        else:
            logger.info("Auto-review disabled. Stopping after one regeneration round.")
            logger.info("Note: review_report.json is unchanged. Run review_shots.py and ai_review_shots.py manually, or use --auto-review.")
            break

    # Final quality gate check
    with open(report_path, "r", encoding="utf-8") as f:
        final_report = json.load(f)

    remaining = [sid for sid, info in final_report.items() if info.get("needs_review")]
    if remaining:
        logger.warning(f"Regeneration finished but shots still need review: {remaining}")
        sys.exit(2)
        
    logger.info("Autonomous regeneration process complete. All shots passed review.")

if __name__ == "__main__":
    main()
