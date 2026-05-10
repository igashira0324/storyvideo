# Project State: fallen_miku_mv

Last updated: 2026-05-11

## Current Status
- **Phase**: Initialization / Recovery
- **Shot Plan**: Generated (needs verification/regeneration)
- **Assets**: 0/4 generated
- **Videos**: 0/4 generated
- **AI Review**: Not started

## Known Issues
- Antigravity crashed during previous session due to context bloat and long polling.
- Project was in the middle of shot planning/initialization.

## Next Actions
1. [ ] Verify `shot_plan.json` integrity.
2. [ ] Run `tools/generate_start_images.py` (via `safe_run.py`).
3. [ ] Run `tools/generate_shots.py` (via `safe_run.py`).
4. [ ] Perform quality review.

## Rules
- Launch heavy jobs via `skills/safe_run.py`.
- Do not paste full logs into chat.
- Check progress with `skills/pipeline_manager.py`.
