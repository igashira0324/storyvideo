import os
import sys
import json
import argparse
import logging
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Add tools to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from providers.comfyui import ComfyUIProvider
import utils

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_node_input(workflow: Dict[str, Any], node_id: str, value: Any, possible_keys: List[str]):
    if node_id not in workflow:
        logger.warning(f"Node ID {node_id} not found in workflow.")
        return False
    
    node = workflow[node_id]
    inputs = node.get("inputs", {})
    
    for key in possible_keys:
        if key in inputs:
            inputs[key] = value
            logger.info(f"Updated node {node_id} input '{key}' to {value}")
            return True
            
    logger.warning(f"None of the possible keys {possible_keys} found in node {node_id} inputs.")
    return False

def process_shot(provider: Any, project_dir: str, shot: Dict[str, Any], dry_run: bool = False, max_retries: int = 1, skip_preflight: bool = False) -> Dict[str, Any]:
    shot_id = shot["id"]
    logger.info(f"Processing shot: {shot_id}")
    
    report = {
        "id": shot_id,
        "status": "pending",
        "retries": 0,
        "error": None,
        "output": shot["output"]
    }

    for attempt in range(max_retries + 1):
        report["retries"] = attempt
        try:
            shot_report = provider.generate_shot(shot, project_dir, dry_run, skip_preflight)
            report.update(shot_report)
            
            if report["status"] != "failed":
                return report
                
            logger.warning(f"Attempt {attempt + 1} failed for shot {shot_id}: {report['error']}")
            if attempt < max_retries:
                logger.info(f"Retrying {shot_id}...")
                
        except Exception as e:
            logger.warning(f"Unexpected error in attempt {attempt + 1} for shot {shot_id}: {e}")
            report["status"] = "failed"
            report["error"] = str(e)
            if attempt < max_retries:
                logger.info(f"Retrying {shot_id}...")
                
    return report

def main():
    parser = argparse.ArgumentParser(description="Generate video shots using ComfyUI API")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--only", nargs="+", help="Only process specific shot ID(s)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip if output file already exists")
    parser.add_argument("--dry-run", action="store_true", help="Prepare workflows without sending to ComfyUI")
    parser.add_argument("--retries", type=int, default=1, help="Max retries per shot")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip ComfyUI node type validation")
    args = parser.parse_args()

    load_dotenv()
    comfy_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    
    project_dir = os.path.abspath(args.project)
    shot_plan_path = os.path.join(project_dir, "shot_plan.json")
    
    if not os.path.exists(shot_plan_path):
        logger.error(f"Shot plan not found: {shot_plan_path}")
        sys.exit(1)
        
    shot_plan = utils.load_json(shot_plan_path)
    provider = ComfyUIProvider(comfy_url)
    
    shots = shot_plan.get("shots", [])
    results = []
    
    import time
    start_time = time.time()
    
    for shot in shots:
        shot_id = shot["id"]
        
        if args.only and shot_id not in args.only:
            continue
            
        output_path = os.path.join(project_dir, shot["output"])
        if args.skip_existing and os.path.exists(output_path):
            logger.info(f"Skipping {shot_id}, output already exists: {output_path}")
            results.append({"id": shot_id, "status": "skipped", "output": shot["output"]})
            continue
            
        report = process_shot(provider, project_dir, shot, args.dry_run, args.retries, args.skip_preflight)
        results.append(report)
        
        if report["status"] == "failed":
            logger.error(f"Failed to process shot: {shot_id}")

    # Generate Report
    total_time = time.time() - start_time
    final_report = {
        "project": shot_plan.get("project_name"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_duration_sec": total_time,
        "results": results
    }
    
    report_dir = os.path.join(project_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "generation_report.json")
    utils.save_json(report_path, final_report)
    logger.info(f"Generation report saved to: {report_path}")
    
    # Summary
    success_count = sum(1 for r in results if r["status"] in ["success", "skipped", "dry_run"])
    logger.info(f"Completed: {success_count}/{len(results)} shots processed successfully.")

if __name__ == "__main__":
    main()
