import os
import sys
import json
import argparse
import logging
from typing import Any, Dict, List
from providers.comfyui import ComfyUIProvider
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_start_images(project_dir: str, preset_path: str, model: str = None, dry_run: bool = False):
    load_dotenv()
    comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    provider = ComfyUIProvider(comfyui_url)

    plan_path = os.path.join(project_dir, "shot_plan.json")
    if not os.path.exists(plan_path):
        logger.error(f"Shot plan not found: {plan_path}")
        return

    with open(plan_path, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    with open(preset_path, 'r', encoding='utf-8') as f:
        preset = json.load(f)

    shots = plan.get("shots", [])
    for shot in shots:
        shot_id = shot["id"]
        input_image_rel = shot.get("input_image")
        if not input_image_rel:
            continue

        output_path = os.path.join(project_dir, input_image_rel)
        if os.path.exists(output_path):
            logger.info(f"Skipping {shot_id}: image already exists at {input_image_rel}")
            continue

        logger.info(f"Generating start image for {shot_id}...")
        
        # Prepare T2I shot config
        # We reuse the ComfyUIProvider.generate_shot logic by constructing a temporary shot object
        t2i_shot = {
            "id": f"{shot_id}_start",
            "workflow": preset["workflow"],
            "positive_prompt": shot["positive_prompt"],
            "negative_prompt": shot.get("negative_prompt", ""),
            "seed": shot.get("seed", 42),
            "width": plan.get("width", 1280),
            "height": plan.get("height", 720),
            "output": input_image_rel, # We want to save it where the shot plan expects it
            "output_type": "image",
            "workflow_params": preset["workflow_params"]
        }

        try:
            res = provider.generate_shot(t2i_shot, project_dir, dry_run=dry_run)
            if res["status"] == "success":
                logger.info(f"Successfully generated start image: {input_image_rel}")
            else:
                logger.error(f"Failed to generate start image for {shot_id}: {res.get('error')}")
        except Exception as e:
            logger.error(f"Error during T2I generation for {shot_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate start images for shots using T2I")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--preset", required=True, help="T2I workflow preset JSON")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    args = parser.parse_args()

    generate_start_images(args.project, args.preset, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
