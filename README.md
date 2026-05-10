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

### Full Pipeline
You can run the entire pipeline with:
```bash
./run_pipeline.sh --project projects/exhibition_pr --skip-existing
```

> [!IMPORTANT]
> **Execution Order**: You MUST run `build_remotion_timeline.py` before running `npm run build` or `npm start`. The script generates `remotion/src/shots.json` and `remotion/src/config.json` which are required for the Remotion project to build.

> [!NOTE]
> **Sample Assets**: Sample input images are included in `projects/exhibition_pr/assets/`. 
> BGM and narration files are optional and not included by default.

## Directory Structure
- `tools/`: Python orchestration scripts and providers.
- `projects/`: Project-specific shot plans, workflows, and outputs.
- `remotion/`: Remotion project for final composition.
- `assets/`: Global assets.
- `workflow_presets/`: Reusable ComfyUI workflow configurations.

## Future Work
- Integration as an OpenMontage provider.
- Advanced AI-based quality validation.
