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

def load_bible_prefix(project_dir: str) -> str:
    """Loads character and style bibles and converts them to a prompt prefix."""
    parts = []
    char_path = os.path.join(project_dir, "character_bible.json")
    style_path = os.path.join(project_dir, "style_bible.json")

    if os.path.exists(char_path):
        try:
            with open(char_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert dict to a concise string for the prompt
                parts.append(f"Character Context: {json.dumps(data)}")
        except Exception as e:
            logger.warning(f"Failed to load character bible: {e}")

    if os.path.exists(style_path):
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                parts.append(f"Style Guide: {json.dumps(data)}")
        except Exception as e:
            logger.warning(f"Failed to load style bible: {e}")

    return "\n".join(parts) if parts else ""

def load_character_identity(project_dir: str) -> Dict[str, Any]:
    """Loads character identity configuration."""
    identity_path = os.path.join(project_dir, "character_identity.json")
    if os.path.exists(identity_path):
        try:
            with open(identity_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load character identity: {e}")
    return {}

def generate_start_images(project_dir: str, preset_path: str = None, model: str = None, dry_run: bool = False, no_bible: bool = False, only_shots: List[str] = None):
    load_dotenv()
    
    # Resolve Preset
    if not preset_path:
        config_path = os.path.join(project_dir, "project_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    preset_path = config.get("t2i_preset")
                    if preset_path:
                        logger.info(f"Using T2I preset from project_config: {preset_path}")
            except Exception as e:
                logger.warning(f"Failed to read project_config.json: {e}")
                
    if not preset_path:
        preset_path = "workflow_presets/ernie_image_turbo.json"
        logger.info(f"No preset specified. Using default: {preset_path}")

    if not os.path.exists(preset_path):
        logger.error(f"Preset file not found: {preset_path}")
        return

    comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    provider = ComfyUIProvider(comfyui_url)

    # Load Identity for injection
    identity = load_character_identity(project_dir)
    identity_prefix = ""
    negative_prefix = ""
    if identity and identity.get("enabled"):
        identity_prefix = identity.get("identity_prompt", "")
        negative_prefix = identity.get("negative_identity_prompt", "")
        logger.info(f"Injecting Character Identity: {identity.get('display_name')}")

    # Load Bibles for injection
    bible_prefix = "" if no_bible else load_bible_prefix(project_dir)
    if bible_prefix:
        logger.info("Injecting Bible context into T2I prompts.")
    elif no_bible:
        logger.info("Bible injection disabled by --no-bible.")

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
        
        if only_shots and shot_id not in only_shots:
            continue
            
        input_image_rel = shot.get("input_image")
        if not input_image_rel:
            continue

        output_path = os.path.join(project_dir, input_image_rel)
        if os.path.exists(output_path):
            logger.info(f"Skipping {shot_id}: image already exists at {input_image_rel}")
            continue

        logger.info(f"Generating start image for {shot_id}...")
        
        # Prepare T2I shot config
        base_prompt = shot.get("t2i_prompt") or shot["positive_prompt"]
        positive_prompt = f"{identity_prefix}\n\n{bible_prefix}\n\n{base_prompt}" if identity_prefix or bible_prefix else base_prompt
        
        base_negative = shot.get("negative_prompt", "")
        negative_prompt = f"{negative_prefix}, {base_negative}" if negative_prefix else base_negative

        t2i_shot = {
            "id": f"{shot_id}_start",
            "workflow": preset["workflow"],
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "seed": shot.get("seed", 42),
            "width": plan.get("width", 1280),
            "height": plan.get("height", 720),
            "output": input_image_rel, 
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
    parser.add_argument("--preset", help="T2I workflow preset JSON (optional, reads from project_config if missing)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--no-bible", action="store_true", help="Disable bible injection")
    parser.add_argument("--only", nargs="+", help="Specific shot IDs to generate")
    args = parser.parse_args()

    generate_start_images(args.project, args.preset, dry_run=args.dry_run, no_bible=args.no_bible, only_shots=args.only)

if __name__ == "__main__":
    main()
