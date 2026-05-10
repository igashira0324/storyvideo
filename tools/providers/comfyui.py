import os
import json
import logging
from typing import Any, Dict, List
from providers.base import VideoProvider
from comfyui_client import ComfyUIClient
import utils

logger = logging.getLogger(__name__)

class ComfyUIProvider(VideoProvider):
    def __init__(self, comfyui_url: str):
        self.client = ComfyUIClient(comfyui_url)

    def _update_node_input(self, workflow: Dict[str, Any], node_id: str, value: Any, possible_keys: List[str]):
        if node_id not in workflow:
            return False
        node = workflow[node_id]
        inputs = node.get("inputs", {})
        for key in possible_keys:
            if key in inputs:
                inputs[key] = value
                return True
        return False

    def _require_update(self, workflow: Dict[str, Any], node_id: str, value: Any, possible_keys: List[str], label: str):
        ok = self._update_node_input(workflow, node_id, value, possible_keys)
        if not ok:
            raise RuntimeError(
                f"Failed to update {label}: node_id={node_id}, possible_keys={possible_keys}. "
                "Check if the node_id and input key are correct in the API workflow JSON."
            )

    def select_video_output(self, outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        video_exts = (".mp4", ".webm", ".mov", ".mkv")
        for item in outputs:
            filename = item.get("filename", "")
            if filename.lower().endswith(video_exts):
                return item
        raise RuntimeError(f"No video output found among files: {[o.get('filename') for o in outputs]}")

    def generate_shot(self, shot: Dict[str, Any], project_dir: str, dry_run: bool = False) -> Dict[str, Any]:
        shot_id = shot["id"]
        report = {
            "id": shot_id,
            "status": "pending",
            "error": None,
            "output": shot["output"]
        }

        workflow_path = os.path.join(project_dir, shot["workflow"])
        if not os.path.exists(workflow_path):
            report["status"] = "failed"
            report["error"] = f"Workflow file not found: {workflow_path}"
            return report
            
        workflow_template = utils.load_json(workflow_path)
        
        # API format check
        if "nodes" in workflow_template and "links" in workflow_template:
            report["status"] = "failed"
            report["error"] = (
                f"Workflow file appears to be ComfyUI UI format, not API format: {workflow_path}. "
                "Please export workflow as API format from ComfyUI."
            )
            return report

        params = shot.get("workflow_params", {})
        
        try:
            workflow = json.loads(json.dumps(workflow_template))
            
            # Image Upload
            input_image_rel = shot.get("input_image")
            if input_image_rel:
                input_image_path = os.path.join(project_dir, input_image_rel)
                if os.path.exists(input_image_path):
                    if not dry_run:
                        uploaded_name = self.client.upload_image(input_image_path)
                        self._require_update(workflow, params.get("image_node_id"), uploaded_name, ["image"], "input image")
                else:
                    report["status"] = "failed"
                    report["error"] = f"Input image not found: {input_image_path}"
                    return report

            # Prompts & Params
            self._require_update(workflow, params.get("positive_node_id"), shot.get("positive_prompt"), 
                                ["text", "string", "prompt", "positive", "positive_prompt"], "positive prompt")
            
            # Negative prompt is optional in some workflows
            negative_node_id = params.get("negative_node_id")
            positive_node_id = params.get("positive_node_id")
            
            if negative_node_id and negative_node_id != positive_node_id:
                self._update_node_input(workflow, negative_node_id, shot.get("negative_prompt"), 
                                        ["text", "string", "negative", "negative_prompt"])
            elif negative_node_id == positive_node_id:
                logger.warning(f"Skipping negative prompt update for shot {shot_id}: negative_node_id is same as positive_node_id ({negative_node_id})")
            
            # Seed handling
            seed = shot.get("seed", -1)
            if seed == -1 and not dry_run:
                import random
                seed = random.randint(1, 2**32 - 1)
            self._update_node_input(workflow, params.get("seed_node_id"), seed, ["seed", "noise_seed"])
            
            duration = shot.get("duration_sec", 5)
            fps = shot.get("fps", 24)
            
            # LTX length calculation
            if shot.get("model", "").lower().startswith("ltx") or "ltx" in shot.get("workflow", "").lower():
                length = int(duration * fps) + 1
            else:
                length = int(duration * fps)
                
            self._require_update(workflow, params.get("length_node_id"), length, 
                                 ["length", "frames", "num_frames", "value_4"], "video length")
            
            self._require_update(workflow, params.get("save_node_id"), f"{shot_id}", 
                                 ["filename_prefix", "filenames_prefix", "filename", "path", "value"], "save node prefix")

            if dry_run:
                report["status"] = "dry_run"
                return report

            prompt_id = self.client.queue_prompt(workflow)
            history = self.client.wait_for_completion(prompt_id)
            outputs = self.client.get_output_files(history)
            
            if not outputs:
                raise RuntimeError("No output files found")
                
            output_info = self.select_video_output(outputs)
            dest_path = os.path.join(project_dir, shot["output"])
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            self.client.download_file(output_info["filename"], output_info.get("subfolder", ""), output_info.get("type", "output"), dest_path)
            
            report["status"] = "success"
            report["prompt_id"] = prompt_id
            return report

        except Exception as e:
            report["status"] = "failed"
            report["error"] = str(e)
            return report

    def validate_shot(self, shot: Dict[str, Any], project_dir: str) -> Dict[str, Any]:
        return {"valid": True}
