import os
import json
import logging
from typing import Any, Dict, List
from .base import VideoProvider
from ..comfyui_client import ComfyUIClient
from .. import utils

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
                        self._update_node_input(workflow, params.get("image_node_id"), uploaded_name, ["image"])
                else:
                    report["status"] = "failed"
                    report["error"] = f"Input image not found: {input_image_path}"
                    return report

            # Prompts & Params
            self._update_node_input(workflow, params.get("positive_node_id"), shot.get("positive_prompt"), ["text", "string"])
            self._update_node_input(workflow, params.get("negative_node_id"), shot.get("negative_prompt"), ["text", "string"])
            
            seed = shot.get("seed", -1)
            if seed == -1 and not dry_run:
                import random
                seed = random.randint(1, 2**32 - 1)
            self._update_node_input(workflow, params.get("seed_node_id"), seed, ["seed", "noise_seed"])
            
            duration = shot.get("duration_sec", 5)
            fps = shot.get("fps", 24)
            length = int(duration * fps)
            self._update_node_input(workflow, params.get("length_node_id"), length, ["length", "frames", "num_frames"])
            self._update_node_input(workflow, params.get("save_node_id"), f"{shot_id}", ["filename_prefix"])

            if dry_run:
                report["status"] = "dry_run"
                return report

            prompt_id = self.client.queue_prompt(workflow)
            history = self.client.wait_for_completion(prompt_id)
            outputs = self.client.get_output_files(history)
            
            if not outputs:
                raise RuntimeError("No output files found")
                
            output_info = outputs[0]
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
        # This can be implemented by calling the logic in validate_shots.py
        # Or keeping it as a separate tool.
        return {"valid": True} # Placeholder
