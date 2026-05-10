# Antigravity Operation Rules (StoryVideo)

This document defines the mandatory operational rules for the Antigravity AI agent to ensure system stability and prevent conversation context bloat.

## 1. Context Safety & Memory Management
- **Conversation Reset**: Start a new conversation after each major project phase (e.g., switching from Planning to Generation, or from Generation to Review).
- **Step Count Monitoring**:
    - **100-200 steps**: Healthy.
    - **300-500 steps**: Warning. Prepare to reset.
    - **500+ steps**: High risk of crash. Reset recommended.
- **Large Data Prohibition**:
    - **DO NOT** paste full logs (> 100 lines). Use `tail -n 20` or similar.
    - **DO NOT** paste full `shot_plan.json` if it has many shots. Use `view_file` with specific line ranges or `pipeline_manager.py` summaries.
    - **DO NOT** paste full `review_report.json` or `generation_report.json`.

## 2. Background Job Management
- **Heavy Job Prohibition**: **DO NOT** run the following commands directly in the interactive Antigravity terminal:
    - `python3 tools/generate_shots.py`
    - `python3 tools/generate_start_images.py`
    - `python3 tools/ai_review_shots.py`
    - `python3 tools/regenerate_failed_shots.py`
    - `npm run build` (Remotion)
- **Mandatory Execution Mode**: Launch all heavy jobs using `skills/safe_run.py` or within a `tmux`/`nohup` session.
- **Monitoring**: Use `python3 skills/pipeline_manager.py --project projects/fallen_miku_mv --status --json` to check project state instead of continuous manual polling.

## 3. Polling & Logging
- **Polling Loop Prohibition**: **DO NOT** use `command_status` in a tight loop for more than 5-10 iterations. If a job is taking longer, inform the user and suggest checking back later.
- **Log Inspection**: When checking logs, always use `tail -n 20` to see only the most recent progress.

## 4. File System Hygiene
- Ensure `.gitignore` is correctly configured to exclude large media files and job logs from IDE indexing.
- Use `PROJECT_STATE.md` within each project directory to track high-level progress and handoff notes.
