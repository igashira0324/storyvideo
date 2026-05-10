import os
import sys
import json
import argparse
import subprocess
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Regenerate shots marked as 'needs_review' in the review report")
    parser.add_argument("--project", required=True, help="Project directory")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    report_path = os.path.join(project_dir, "reports", "review_report.json")
    
    if not os.path.exists(report_path):
        logger.error(f"Review report not found: {report_path}")
        sys.exit(1)

    with open(report_path, 'r') as f:
        review_report = json.load(f)

    failed_shots = [shot_id for shot_id, info in review_report.items() if info.get("needs_review")]

    if not failed_shots:
        logger.info("No shots found that need review. Skipping regeneration.")
        return

    logger.info(f"Found {len(failed_shots)} shots that need review: {failed_shots}")
    
    # Update seeds in shot_plan.json
    import random
    plan_path = os.path.join(project_dir, "shot_plan.json")
    with open(plan_path, 'r', encoding='utf-8') as f:
        shot_plan = json.load(f)
    
    for shot in shot_plan.get("shots", []):
        if shot["id"] in failed_shots:
            old_seed = shot.get("seed", 42)
            new_seed = random.randint(1, 2**32 - 1)
            shot["seed"] = new_seed
            logger.info(f"Updated seed for {shot['id']}: {old_seed} -> {new_seed}")
            
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(shot_plan, f, indent=2, ensure_ascii=False)
    
    # Construct the command to run generate_shots.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generate_script = os.path.join(script_dir, "generate_shots.py")

    cmd = [
        sys.executable,
        generate_script,
        "--project", args.project,
        "--only"
    ] + failed_shots

    logger.info(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        logger.info("Regeneration complete.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Regeneration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
