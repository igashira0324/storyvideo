# Project State: fallen_miku_mv

Last updated: 2026-05-11

## Current Status
- **Phase**: Quality Review (AI)
- **Shot Plan**: Verified [OK]
- **Workflows**: Corrected and verified in `projects/fallen_miku_mv/comfy_workflows/`
- **Assets**: 4/4 generated [OK]
- **Videos**: 4/4 generated [OK]
- **Integrity Review**: Completed (Job: `review_shots`)
- **AI Review**: In Progress (Job: `ai_review`)

## Known Issues
- Antigravity robustness measures (P0/P1) fully implemented and pushed.
- Ernie Image JSON restored from Downloads.

## Next Actions
1. [x] Verify `shot_plan.json` integrity.
2. [x] Run `tools/generate_start_images.py` (via `safe_run.py`) -> Completed
3. [/] Run `tools/generate_shots.py` (via `safe_run.py`).
4. [ ] Perform quality review.

## Model / Workflow Policy

- **T2I start images**: Ernie Image Turbo
  - Preset: `workflow_presets/ernie_image_turbo.json`
  - Workflow: `comfy_workflows/ernie_image_turbo_api.json`
- **I2V videos**: LTX-2.3
  - Preset: `workflow_presets/ltx23_i2v.json`
  - Workflow: `comfy_workflows/ltx23_i2v_api.json`
- **SDXL**: Legacy/fallback only. Not used in this project.

## Rules
- Launch heavy jobs via `skills/safe_run.py`.
- Do not paste full logs into chat.
- Check progress with `skills/pipeline_manager.py`.
