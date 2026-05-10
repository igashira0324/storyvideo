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

### 3. Usage

#### Generate Shots
```bash
python3 tools/generate_shots.py --project projects/exhibition_pr
```
Generated reports will be saved to `projects/exhibition_pr/reports/generation_report.json`.

#### Validate Outputs
```bash
python3 tools/validate_shots.py --project projects/exhibition_pr
```

#### Assemble Video (Remotion)
```bash
python3 tools/build_remotion_timeline.py --project projects/exhibition_pr --remotion-dir remotion
cd remotion
npm install
npm run build
```

## Directory Structure
- `tools/`: Python orchestration scripts and providers.
- `projects/`: Project-specific shot plans, workflows, and outputs.
- `remotion/`: Remotion project for final composition.
- `assets/`: Global assets.

## Future Work
- Integration as an OpenMontage provider.
- Advanced AI-based quality validation.
