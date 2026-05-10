# AI Video Generation Pipeline (StoryVideo)

A modular, lightweight pipeline for multi-shot AI video generation using ComfyUI and Remotion.

## Features
- **Shot Orchestration**: Define multiple shots in a single `shot_plan.json`.
- **Workflow Automation**: Programmatically modify ComfyUI workflows (WAN 2.2, LTX 2.3).
- **Remotion Composition**: Automatically assemble shots into a final video with subtitles.
- **Validation**: Automated quality checks using `ffprobe`.

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
- `tools/`: Python orchestration scripts.
- `projects/`: Project-specific shot plans and assets.
- `remotion/`: Remotion project for final composition.
- `assets/`: Global assets (if any).

## Future Work
- Integration as an OpenMontage provider.
- Advanced AI-based quality validation.
