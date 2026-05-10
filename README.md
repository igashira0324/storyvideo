# StoryVideo
A lightweight multi-shot AI video generation pipeline using ComfyUI and Remotion.

## Important: ComfyUI Workflow Format
The pipeline requires ComfyUI workflows in **API Format** (exported via "Save API Format" or "Export API").
- **UI Format**: Contains `nodes` and `links` arrays. This is NOT compatible with the `/prompt` endpoint.
- **API Format**: A flat JSON where each key is a `node_id`. This is what the pipeline uses.

When defining `workflow_params` in `shot_plan.json`, the `node_id` must match the keys in the **API Format** JSON.

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- ffmpeg & ffprobe
- Access to a ComfyUI server

### 2. Installation
```bash
pip install -r requirements.txt
cp .env.example .env  # Edit COMFYUI_URL in .env
```

## Usage

### 1. Generate Shot Plan from Brief
Use the LLM-powered story planner to create a multi-shot plan from a text description.
```bash
# Requires local Ollama server running
python3 tools/story_planner.py \
  --brief projects/exhibition_pr/brief.md \
  --project projects/exhibition_pr \
  --model qwen3.6:27b
```

### 2. Generate Shots
Generate videos based on the shot plan.
```bash
python3 tools/generate_shots.py --project projects/exhibition_pr
```
Generated reports will be saved to `projects/exhibition_pr/reports/generation_report.json`.

### 3. Validate Outputs
Run verification on the generated video files.
```bash
python3 tools/validate_shots.py --project projects/exhibition_pr
```

### 4. Review Generated Shots
Check video integrity, duration, and metadata.
```bash
python3 tools/review_shots.py --project projects/exhibition_pr
```

### 5. Assemble Video (Remotion)
Final composition and rendering.
```bash
python3 tools/build_remotion_timeline.py --project projects/exhibition_pr --remotion-dir remotion
cd remotion
npm install
npm run build
```

### 6. Generate Shots via helper script
Generate videos based on the shot plan using the shortcut script.
```bash
./run_pipeline.sh --project projects/exhibition_pr --skip-existing
```

### Full Pipeline Example
To run the complete process from planning to final rendering, including autonomous self-healing:

```bash
# 1. Shot plan generation
python3 tools/story_planner.py \
  --brief projects/exhibition_pr/brief.md \
  --project projects/exhibition_pr \
  --preset workflow_presets/ltx23_i2v.json

# 2. T2I start image generation
python3 tools/generate_start_images.py \
  --project projects/exhibition_pr \
  --preset workflow_presets/sdxl_t2i.json

# 3. I2V video generation
python3 tools/generate_shots.py \
  --project projects/exhibition_pr \
  --skip-existing

# 4. Basic integrity check
python3 tools/review_shots.py \
  --project projects/exhibition_pr

# 5. AI quality review
python3 tools/ai_review_shots.py \
  --project projects/exhibition_pr \
  --model minicpm-v

# 6. Autonomous self-healing loop (regenerate, re-review)
python3 tools/regenerate_failed_shots.py \
  --project projects/exhibition_pr \
  --max-rounds 3 \
  --auto-review \
  --vlm-model minicpm-v

# 7. Continuity linking (optional, for smooth transitions)
# Note: Since this modifies input images, you may need to regenerate subsequent shots if used.
python3 tools/link_shots_continuity.py \
  --project projects/exhibition_pr \
  --force

# 8. Final assembly & rendering (Remotion)
python3 tools/build_remotion_timeline.py \
  --project projects/exhibition_pr \
  --remotion-dir remotion

cd remotion
npm install
npm run build
```

> [!IMPORTANT]
> **Execution Order**: You MUST run `build_remotion_timeline.py` before running `npm run build` or `npm start`. The script generates `remotion/src/shots.json` and `remotion/src/config.json` which are required for the Remotion project to build.

> [!NOTE]
> **Sample Assets**: Sample input images are included in `projects/exhibition_pr/assets/`. 
> BGM and narration files are optional and not included by default.

## Advanced Features

### 1. Workflow Parameter Mapping
You can explicitly map node IDs and input keys in your workflow presets. This is more robust than the default heuristic search.
```json
"workflow_params": {
  "positive": { "node_id": "267:266", "input_key": "value" },
  "negative": { "node_id": "267:247", "input_key": "text" },
  "image": { "node_id": "269", "input_key": "image" },
  "seeds": [
    { "node_id": "267:237", "input_key": "noise_seed" },
    { "node_id": "267:216", "input_key": "noise_seed" }
  ]
}
```

### 2. Automated Start Image Generation (T2I)
Automatically generate the initial images (`input_image`) for your shots using a T2I workflow.
```bash
python3 tools/generate_start_images.py \
  --project projects/exhibition_pr \
  --preset workflow_presets/sdxl_t2i.json
```

### 3. Character & Style Bibles
Maintain visual consistency by providing character and style definitions. If `character_bible.json` or `style_bible.json` exist in your project directory, they will be injected into the story planner's prompt.
```json
// projects/exhibition_pr/character_bible.json
{
  "main_character": {
    "name": "Spark-chan",
    "description": "Short blue hair, VR goggles, silver tactical suit"
  }
}
```

### 4. AI Quality Review (VLM)
Use a Vision-Language Model (VLM) to automatically check if the generated videos match the prompt and meet quality standards.
```bash
# 1. Standard Review (Integrity check)
python3 tools/review_shots.py --project projects/exhibition_pr

# 2. AI Review (Visual check)
python3 tools/ai_review_shots.py --project projects/exhibition_pr --model minicpm-v

# 3. Autonomous self-healing loop (up to 3 rounds, auto re-review)
python3 tools/regenerate_failed_shots.py \
  --project projects/exhibition_pr \
  --max-rounds 3 \
  --auto-review \
  --vlm-model minicpm-v
```

> [!NOTE]
> **Without `--auto-review`**: The script regenerates files but does **not** update `review_report.json`.
> Run `review_shots.py` and `ai_review_shots.py` manually afterward, or use `--auto-review`.
> If shots still fail after all rounds, the script exits with code **2** (for CI integration).

### 5. Shot Continuity Linking
Use the last frame of each shot as the start image of the next shot for seamless visual continuity.
```bash
# Apply continuity (modifies input images of subsequent shots)
python3 tools/link_shots_continuity.py --project projects/exhibition_pr --force

# Then regenerate the subsequent shots that now have new start images
python3 tools/generate_shots.py \
  --project projects/exhibition_pr \
  --only shot_002 shot_003 shot_004
```

> [!WARNING]
> Running `link_shots_continuity.py --force` overwrites the input images for subsequent shots.
> Existing generated videos remain unchanged — you **must** regenerate those shots afterward.

## Troubleshooting

### ComfyUI Workflow: Missing Node Types
If you see `missing_node_type` errors, the API workflow contains node types not installed in your ComfyUI instance.

**Fix: Re-export the workflow from ComfyUI**
1. Enable Dev Mode in ComfyUI settings
2. Open the workflow in the browser
3. Expand any Group Nodes / Subgraphs
4. **Save (API Format)** — not the regular save
5. Replace `projects/<project>/comfy_workflows/<name>_api.json`

**Check installed custom nodes:**
```bash
ls ComfyUI/custom_nodes/
```

### ComfyUI Not Responding
Make sure ComfyUI is running and accessible:
```bash
# Start ComfyUI
cd /path/to/ComfyUI && python main.py --listen 0.0.0.0 --port 8188

# Test connection
curl http://127.0.0.1:8188/system_stats
```

Set the URL in your environment:
```bash
export COMFYUI_URL=http://127.0.0.1:8188
```
