import os
import sys
import json
import argparse
import logging
import requests
from typing import Any, Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STORY_PLAN_PROMPT = """
You are a professional film director and storyboard artist. Your task is to take a short "Brief" and transform it into a "Shot Plan" for AI video generation.

Target Workflow: LTX-2.3 Image-to-Video.
Each shot needs:
- Positive Prompt: Descriptive, cinematic, visual focus.
- Subtitle: Narrative or dialogue.
- Duration: 2-5 seconds.

Output Format: A single JSON object that follows this schema:
{{
  "project_name": "string",
  "project_title": "string",
  "composition_name": "FinalVideo",
  "width": 1280,
  "height": 720,
  "fps": 24,
  "shots": [
    {{
      "id": "shot_001_...",
      "workflow": "comfy_workflows/ltx23_i2v_api.json",
      "input_image": "assets/shot_001_start.png",
      "positive_prompt": "string",
      "negative_prompt": "low quality, blurry, distorted, watermark",
      "duration_sec": int,
      "fps": 24,
      "seed": 42,
      "subtitle": "string",
      "workflow_params": {{
        "image_node_id": "269",
        "positive_node_id": "267:266",
        "negative_node_id": "267:247",
        "seed_node_ids": ["267:237", "267:216"],
        "length_node_id": "267:225",
        "save_node_id": "75"
      }}
    }},
    ...
  ]
}}

Guidelines:
1. Break the story into 3-5 logical shots.
2. Maintain character and setting consistency in the positive prompts.
3. Keep prompts descriptive: lighting, camera angle, action.
4. Output ONLY the JSON object.

Brief:
{brief}
"""

def generate_plan(brief_text: str, model: str, url: str) -> Dict[str, Any]:
    prompt = STORY_PLAN_PROMPT.format(brief=brief_text)
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    logger.info(f"Requesting story plan from LLM ({model})...")
    response = requests.post(f"{url}/api/generate", json=payload)
    response.raise_for_status()
    
    data = response.json()
    plan_json = json.loads(data["response"])
    return plan_json

def main():
    parser = argparse.ArgumentParser(description="Generate a shot plan from a story brief using LLM")
    parser.add_argument("--brief", required=True, help="Path to the brief text file")
    parser.add_argument("--project", required=True, help="Project directory to save the plan")
    parser.add_argument("--model", default="qwen3.6:27b", help="Ollama model name")
    parser.add_argument("--url", default="http://127.0.0.1:11434", help="Ollama API URL")
    args = parser.parse_args()

    if not os.path.exists(args.brief):
        logger.error(f"Brief file not found: {args.brief}")
        sys.exit(1)

    with open(args.brief, 'r', encoding='utf-8') as f:
        brief_content = f.read()

    try:
        plan = generate_plan(brief_content, args.model, args.url)
        
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
