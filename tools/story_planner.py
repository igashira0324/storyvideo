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
      "subtitle": "A short cinematic narration line.",
      "narration": null,
      "t2i_prompt": "<detailed visual prompt for start image generation>",
      "transition": "fade",
      "output": "outputs/shot_001_intro.mp4"
    }}
  ]
}}

Guidelines:
- Each shot should visually follow the previous one.
- Keep the number of shots reasonable: 3-6 shots.
- Use dynamic camera movements and detailed visual prompts.
- Include lighting, camera angle, subject, action, and atmosphere.
- Ensure 'duration_sec' is an integer between 3 and 8.
- Ensure 'seed' is an integer.
- Ensure "output" paths use "outputs/shot_xxx.mp4" format and are unique.
- Output ONLY the JSON object. Do not include markdown formatting or ellipsis.

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

def call_llm_json(model: str, url: str, prompt: str, timeout: int = 300) -> Dict[str, Any]:
    """Calls Ollama and ensures a JSON response."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    response = requests.post(f"{url}/api/generate", json=payload, timeout=timeout)
    response.raise_for_status()
    
    data = response.json()
    response_text = data.get("response") or data.get("thinking")
    if not response_text:
        raise ValueError("Ollama returned an empty response.")

    return json.loads(response_text)

def generate_and_repair_plan(full_brief: str, model: str, url: str, preset: Dict[str, Any], repair_retries: int, timeout: int = 300) -> Dict[str, Any]:
    """Handles the full generation and repair loop."""
    base_prompt = STORY_PLAN_PROMPT.format(brief=full_brief)
    current_prompt = base_prompt
    
    last_error = None
    for attempt in range(repair_retries + 1):
        try:
            logger.info(f"Requesting story plan from LLM ({model})... (Attempt {attempt + 1})")
            plan = call_llm_json(model, url, current_prompt, timeout=timeout)
            
            # Merge and Validate
            merged_plan = merge_preset(plan, preset)
            validated_plan = validate_plan(merged_plan)
            
            return validated_plan
            
        except (json.JSONDecodeError, ValueError, Exception) as e:
            last_error = e
            error_msg = str(e)
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "...[truncated]"
            
            logger.warning(f"Generation attempt {attempt + 1} failed: {error_msg}")
            if attempt < repair_retries:
                current_prompt = f"{base_prompt}\n\nIMPORTANT: Your previous output was invalid or failed validation. Error: {error_msg}. Please fix the structure and provide a valid JSON object ONLY."
            else:
                raise last_error

def main():
    parser = argparse.ArgumentParser(description="Generate a shot plan from a story brief using LLM")
    parser.add_argument("--brief", required=True, help="Path to the brief text file")
    parser.add_argument("--project", required=True, help="Project directory to save the plan")
    parser.add_argument("--preset", default="workflow_presets/ltx23_i2v.json", help="Workflow preset JSON")
    parser.add_argument("--repair-retries", type=int, default=2, help="Number of times to retry on JSON/Validation error")
    parser.add_argument("--model", default="qwen2.5:14b", help="Ollama model name")
    parser.add_argument("--url", default="http://127.0.0.1:11434", help="Ollama API URL")
    parser.add_argument("--timeout", type=int, default=300, help="Ollama request timeout in seconds")
    parser.add_argument("--max-brief-chars", type=int, default=8000, help="Max characters for brief")
    parser.add_argument("--max-bible-chars", type=int, default=4000, help="Max characters per bible file")
    parser.add_argument("--no-bible", action="store_true", help="Disable bible injection")
    args = parser.parse_args()

    if not os.path.exists(args.brief):
        logger.error(f"Brief file not found: {args.brief}")
        sys.exit(1)

    with open(args.brief, 'r', encoding='utf-8') as f:
        brief_content = f.read()
        if len(brief_content) > args.max_brief_chars:
            logger.warning(f"Brief truncated from {len(brief_content)} to {args.max_brief_chars}")
            brief_content = brief_content[:args.max_brief_chars] + "\n...[truncated]"

    # Character and Style Bibles
    bibles_text = ""
    if not args.no_bible:
        char_bible_path = os.path.join(args.project, "character_bible.json")
        style_bible_path = os.path.join(args.project, "style_bible.json")
        
        for label, path in [("Character", char_bible_path), ("Style", style_bible_path)]:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if len(content) > args.max_bible_chars:
                        logger.warning(f"{label} Bible truncated from {len(content)} to {args.max_bible_chars}")
                        content = content[:args.max_bible_chars] + "\n...[truncated]"
                    bibles_text += f"\n{label} Bible:\n{content}\n"
                    logger.info(f"Using {label.lower()} bible for prompt injection.")

    try:
        preset = load_preset(args.preset)
        full_brief = f"{brief_content}\n{bibles_text}"
        
        # Generation & Repair Loop
        plan = generate_and_repair_plan(full_brief, args.model, args.url, preset, args.repair_retries, timeout=args.timeout)

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
