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
    
    # Construct the command to run generate_shots.py
    # We use space-separated IDs for the --only flag
    cmd = [
        "python3", "tools/generate_shots.py",
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
