# Project State: fallen_miku_mv

Last updated: 2026-05-11

## Current Status
- **Phase**: Start Image Generation (Background)
- **Shot Plan**: Verified [OK]
- **Workflows**: Restored to `projects/fallen_miku_mv/comfy_workflows/`
- **Assets**: 0/4 generated (Job running: `generate_start_images`)
- **Videos**: 0/4 generated
- **AI Review**: Not started

## Known Issues
- Antigravity crashed during previous session; recovered with AGENT_RUNBOOK rules.
- Git push resolved using proxy bypass (`env -u http_proxy ...`).

## Next Actions
1. [x] Verify `shot_plan.json` integrity.
2. [/] Run `tools/generate_start_images.py` (via `safe_run.py`) -> Running: `99404`
3. [ ] Run `tools/generate_shots.py` (via `safe_run.py`).
4. [ ] Perform quality review.

## Rules
- Launch heavy jobs via `skills/safe_run.py`.
- Do not paste full logs into chat.
- Check progress with `skills/pipeline_manager.py`.
