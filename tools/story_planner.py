import os
import sys
import json
import argparse
import logging
import requests
from typing import Any, Dict, List, Optional
from schemas import ShotPlan

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STORY_PLAN_PROMPT = """
You are a professional film director and storyboard artist. Your task is to take a short "Brief" and transform it into a "Shot Plan" for AI video generation.

Target Workflow: LTX-2.3 Image-to-Video.
Each shot needs story-related information only.

Output Format: A single JSON object that follows this schema:
{{
  "project_name": "string",
  "project_title": "string",
  "composition_name": "FinalVideo",
  "width": 1280,
  "height": 720,
  "shots": [
    {{
      "id": "shot_001_...",
      "input_image": "assets/shot_001_start.png",
      "positive_prompt": "string (visual description, cinematic, focus on characters and action)",
      "negative_prompt": "low quality, blurry, distorted, watermark",
      "duration_sec": 4,
      "seed": 42,
      "subtitle": "string (narrative or dialogue)",
      "narration": null,
      "output": "outputs/shot_001.mp4"
    }}
  ]
}}

Guidelines:
1. Break the story into 3-5 logical shots.
2. Maintain character and setting consistency in the positive prompts.
3. Keep prompts descriptive: lighting, camera angle, action.
4. Output ONLY the JSON object. Do not include markdown formatting or ellipsis.
5. Ensure "output" paths use "outputs/shot_xxx.mp4" format and are unique.

Brief:
{brief}
"""

def validate_plan(plan: Dict[str, Any]):
    """Validates the generated plan using Pydantic schema."""
    try:
        validated_plan = ShotPlan(**plan)
        
        # Additional check for duplicate outputs
        seen_outputs = set()
        for shot in validated_plan.shots:
            if shot.output in seen_outputs:
                raise ValueError(f"Duplicate output path found: {shot.output}")
            seen_outputs.add(shot.output)
            
        return validated_plan.model_dump()
    except Exception as e:
        raise ValueError(f"Schema validation failed: {e}")

def load_preset(preset_path: str) -> Dict[str, Any]:
    if not os.path.exists(preset_path):
        # Try relative to the script's directory if not found
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(script_dir, "..", preset_path)
        if os.path.exists(alt_path):
            preset_path = alt_path
        else:
            raise FileNotFoundError(f"Preset file not found: {preset_path}")
            
    with open(preset_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_preset(plan: Dict[str, Any], preset: Dict[str, Any]) -> Dict[str, Any]:
    """Merges workflow preset into the generated plan."""
    # Top-level merge
    if "fps" not in plan:
        plan["fps"] = preset.get("fps", 24)
        
    # Shot-level merge
    for shot in plan.get("shots", []):
        shot["workflow"] = preset.get("workflow")
        shot["workflow_params"] = preset.get("workflow_params")
        shot["frame_count_formula"] = preset.get("frame_count_formula")
        if "fps" not in shot:
            shot["fps"] = plan["fps"]
            
    return plan

def generate_plan(brief_text: str, model: str, url: str, repair_retries: int = 2) -> Dict[str, Any]:
    prompt = STORY_PLAN_PROMPT.format(brief=brief_text)
    
    current_prompt = prompt
    for attempt in range(repair_retries + 1):
        payload = {
            "model": model,
            "prompt": current_prompt,
            "stream": False,
            "format": "json"
        }
        
        logger.info(f"Requesting story plan from LLM ({model})... (Attempt {attempt + 1})")
        response = requests.post(f"{url}/api/generate", json=payload, timeout=300)
        response.raise_for_status()
        
        data = response.json()
        response_text = data.get("response") or data.get("thinking")
        if not response_text:
            logger.warning(f"Ollama returned an empty response fields. Data keys: {list(data.keys())}")
            if attempt < repair_retries:
                continue
            else:
                raise ValueError("Ollama returned an empty response.")

        try:
            plan_json = json.loads(response_text)
            return plan_json
        except json.JSONDecodeError as e:
            if attempt < repair_retries:
                logger.warning(f"JSON decode failed. Retrying... Error: {e}")
                current_prompt = f"{prompt}\n\nIMPORTANT: Your previous output was invalid JSON. Error: {e}. Please provide a valid JSON object ONLY."
                continue
            else:
                raise

def main():
    parser = argparse.ArgumentParser(description="Generate a shot plan from a story brief using LLM")
    parser.add_argument("--brief", required=True, help="Path to the brief text file")
    parser.add_argument("--project", required=True, help="Project directory to save the plan")
    parser.add_argument("--preset", default="workflow_presets/ltx23_i2v.json", help="Workflow preset JSON")
    parser.add_argument("--repair-retries", type=int, default=2, help="Number of times to retry on JSON/Validation error")
    parser.add_argument("--model", default="qwen3.6:27b", help="Ollama model name")
    parser.add_argument("--url", default="http://127.0.0.1:11434", help="Ollama API URL")
    args = parser.parse_args()

    if not os.path.exists(args.brief):
        logger.error(f"Brief file not found: {args.brief}")
        sys.exit(1)

    with open(args.brief, 'r', encoding='utf-8') as f:
        brief_content = f.read()

    # Character and Style Bibles
    bibles_text = ""
    char_bible_path = os.path.join(args.project, "character_bible.json")
    style_bible_path = os.path.join(args.project, "style_bible.json")
    
    if os.path.exists(char_bible_path):
        with open(char_bible_path, 'r', encoding='utf-8') as f:
            bibles_text += f"\nCharacter Bible:\n{f.read()}\n"
            logger.info("Using character bible for prompt injection.")
            
    if os.path.exists(style_bible_path):
        with open(style_bible_path, 'r', encoding='utf-8') as f:
            bibles_text += f"\nStyle Bible:\n{f.read()}\n"
            logger.info("Using style bible for prompt injection.")

    try:
        preset = load_preset(args.preset)
        
        plan = None
        last_error = None
        
        # Inject bibles into the story prompt
        full_brief = f"{brief_content}\n{bibles_text}"
        
        for attempt in range(args.repair_retries + 1):
            try:
                # 1. Generate (or regenerate on failure)
                if plan is None:
                    plan = generate_plan(full_brief, args.model, args.url, repair_retries=0)
                
                # 2. Merge Preset
                merged_plan = merge_preset(plan, preset)
                
                # 3. Validate
                validated_plan = validate_plan(merged_plan)
                
                # If we reach here, everything is good
                plan = validated_plan
                break
                
            except Exception as e:
                last_error = e
                if attempt < args.repair_retries:
                    logger.warning(f"Validation failed (Attempt {attempt + 1}). Retrying... Error: {e}")
                    # Update prompt for repair
                    repair_prompt = f"{STORY_PLAN_PROMPT.format(brief=full_brief)}\n\nIMPORTANT: Your previous output failed validation. Error: {e}. Please fix the structure and provide a valid JSON object ONLY."
                    
                    payload = {
                        "model": args.model,
                        "prompt": repair_prompt,
                        "stream": False,
                        "format": "json"
                    }
                    response = requests.post(f"{args.url}/api/generate", json=payload, timeout=300)
                    response.raise_for_status()
                    data = response.json()
                    response_text = data.get("response") or data.get("thinking")
                    if not response_text:
                        raise ValueError("Ollama returned an empty response during repair.")
                    plan = json.loads(response_text)
                else:
                    raise last_error

        os.makedirs(args.project, exist_ok=True)
        output_path = os.path.join(args.project, "shot_plan.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Successfully generated shot plan: {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate story plan: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
