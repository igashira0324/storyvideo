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

## 4. Harness Design Concepts (Stateless Orchestration)
The StoryVideo "Harness" is the orchestration layer that decouples the AI Agent (Director) from the heavy execution engines (ComfyUI/Tools).

### Core Principles
- **Director vs. Engine Separation**: Antigravity is the "Director" who makes decisions. `safe_run.py` and tools are the "Engine" that does the work.
- **Context-Free Persistence**: The "ground truth" of the project state must reside in the filesystem (`PROJECT_STATE.md`, `reports/jobs/*.json`), NOT in the agent's memory.
- **Telemetry-based Monitoring**: The agent should only see the "tail" of logs. If a job is running, the agent should return `WAIT_FOR_JOBS` and exit or move to another task.
- **Handoff Readiness**: Every step should produce a "Session Handoff" state. If the agent crashes or the conversation is reset, the next agent should be able to resume immediately by reading the project state.

### Harness Implementation Checklist
- [ ] Use `safe_run.py` for all jobs > 30 seconds.
- [ ] Maintain `PROJECT_STATE.md` with current phase and next actions.
- [ ] Use `pipeline_manager.py` to get a structured overview before making decisions.
- [ ] Use `shlex.quote()` for all shell command generation in `safe_run.py`.

## 5. File System Hygiene
- Ensure `.gitignore` is correctly configured to exclude large media files and job logs from IDE indexing.
- Use `PROJECT_STATE.md` within each project directory to track high-level progress and handoff notes.
