import os
import json
import logging
import math
from typing import Any, Dict, List
from providers.base import VideoProvider
from comfyui_client import ComfyUIClient
import utils

logger = logging.getLogger(__name__)

class ComfyUIProvider(VideoProvider):
    def __init__(self, comfyui_url: str):
        self.client = ComfyUIClient(comfyui_url)

    def calc_frame_count(self, duration_sec: float, fps: int, formula: str) -> int:
        base = math.ceil(duration_sec * fps)

        if formula == "duration_fps_plus_one":
            return base + 1

        if formula == "ltx_8n_plus_1":
            # LTX-2.3 often prefers (8n + 1) frames
            n = max(1, math.ceil((base - 1) / 8))
            return n * 8 + 1

        return base

    def _update_node_input(self, workflow: Dict[str, Any], node_id: str, value: Any, possible_keys: List[str], input_key: str = None):
        if not node_id or node_id not in workflow:
            return False
        node = workflow[node_id]
        inputs = node.get("inputs", {})
        
        # If input_key is explicitly provided, use it strictly
        if input_key:
            if input_key in inputs:
                inputs[input_key] = value
                return True
            else:
                logger.error(f"Explicit input_key '{input_key}' not found in node {node_id}. Strict mapping failed.")
                return False

        # Heuristic Search for possible keys (only if no explicit input_key)
        for key in possible_keys:
            if key in inputs:
                inputs[key] = value
                return True
        return False

    def _update_param(self, workflow: Dict[str, Any], params: Dict[str, Any], key_name: str, value: Any, possible_keys: List[str], label: str, required: bool = True):
        """Updates a parameter using either the new Dict format or the old string format."""
        config = params.get(key_name)
        if not config:
            if required:
                raise RuntimeError(f"Missing required parameter config for {label} (key: {key_name})")
            return False

        if isinstance(config, dict):
            # New format: {"node_id": "...", "input_key": "..."}
            node_id = config.get("node_id")
            input_key = config.get("input_key")
            ok = self._update_node_input(workflow, node_id, value, possible_keys, input_key)
        else:
            # Old format: "node_id" (string)
            ok = self._update_node_input(workflow, str(config), value, possible_keys)

        if not ok and required:
            raise RuntimeError(
                f"Failed to update {label}: config={config}, possible_keys={possible_keys}. "
                "Check if the node_id and input key are correct in the API workflow JSON."
            )
        return ok

    def _require_update(self, workflow: Dict[str, Any], node_id: str, value: Any, possible_keys: List[str], label: str):
        # This remains for internal use but usually _update_param is preferred now
        ok = self._update_node_input(workflow, node_id, value, possible_keys)
        if not ok:
            raise RuntimeError(
                f"Failed to update {label}: node_id={node_id}, possible_keys={possible_keys}. "
            )

    def select_video_output(self, outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        video_exts = (".mp4", ".webm", ".mov", ".mkv")
        for item in outputs:
            filename = item.get("filename", "")
            if filename.lower().endswith(video_exts):
                return item
        raise RuntimeError(f"No video output found among files: {[o.get('filename') for o in outputs]}")

    def select_image_output(self, outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        image_exts = (".png", ".jpg", ".jpeg", ".webp")
        for item in outputs:
            filename = item.get("filename", "")
            if filename.lower().endswith(image_exts):
                return item
        raise RuntimeError(f"No image output found among files: {[o.get('filename') for o in outputs]}")

    def validate_node_types(self, workflow: Dict[str, Any]):
        """Check if all node types in the workflow are registered on the server."""
        try:
            object_info = self.client.get_object_info()
            available_types = set(object_info.keys())
        except Exception as e:
            logger.warning(f"Could not fetch object_info for preflight validation: {e}")
            return

        missing = []
        for node_id, node in workflow.items():
            class_type = node.get("class_type")
            if class_type not in available_types:
                missing.append({
                    "node_id": node_id,
                    "class_type": class_type
                })

        if missing:
            raise RuntimeError(
                "Workflow contains node types not registered in this ComfyUI server: "
                f"{missing}.\n"
                "Possible reasons:\n"
                "1. Custom nodes are not installed on the server.\n"
                "2. The workflow contains 'Group Nodes' or 'Subgraphs' that are not expanded.\n\n"
                "To fix:\n"
                "- Open the workflow in ComfyUI browser.\n"
                "- Enable 'Dev mode' in settings.\n"
                "- Export using 'Save (API Format)' or 'Export API' to ensure subgraphs are expanded.\n"
                "- Replace the JSON file in your project with the new export."
            )

    def generate_shot(self, shot: Dict[str, Any], project_dir: str, dry_run: bool = False, skip_preflight: bool = False) -> Dict[str, Any]:
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
        
        # Preflight validation
        if not dry_run and not skip_preflight:
            self.validate_node_types(workflow_template)
            
        # API format check (legacy check, redundant if preflight is on but good for dry-run)
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
                        # Try new "image" key first, then fallback to "image_node_id"
                        if "image" in params:
                            self._update_param(workflow, params, "image", uploaded_name, ["image"], "input image")
                        else:
                            self._update_param(workflow, params, "image_node_id", uploaded_name, ["image"], "input image")
                else:
                    report["status"] = "failed"
                    report["error"] = f"Input image not found: {input_image_path}"
                    return report

            # Prompts
            # New format "positive" / "negative" vs old "positive_node_id" / "negative_node_id"
            pos_key = "positive" if "positive" in params else "positive_node_id"
            neg_key = "negative" if "negative" in params else "negative_node_id"
            
            self._update_param(workflow, params, pos_key, shot.get("positive_prompt"), 
                              ["text", "string", "prompt", "positive", "positive_prompt", "value"], "positive prompt")
            
            neg_val = shot.get("negative_prompt")
            if neg_val:
                self._update_param(workflow, params, neg_key, neg_val, 
                                  ["text", "string", "negative", "negative_prompt"], "negative prompt", required=False)
            
            # Seed handling
            seed = shot.get("seed", -1)
            if seed == -1 and not dry_run:
                import random
                seed = random.randint(1, 2**32 - 1)
            
            # Seeds can be a list (new/old) or single
            seeds_config = params.get("seeds") or params.get("seed_node_ids")
            if seeds_config and isinstance(seeds_config, list):
                for i, config in enumerate(seeds_config):
                    s_val = seed + i
                    if isinstance(config, dict):
                        self._update_node_input(workflow, config.get("node_id"), s_val, ["seed", "noise_seed"], config.get("input_key"))
                    else:
                        self._update_node_input(workflow, str(config), s_val, ["seed", "noise_seed"])
            else:
                # Fallback to single seed_node_id
                self._update_param(workflow, params, "seed_node_id", seed, ["seed", "noise_seed"], "seed", required=False)
            
            # Frame count / Length calculation (only for video)
            output_type = shot.get("output_type", "video")
            if output_type != "image":
                duration = shot.get("duration_sec", 5)
                fps = shot.get("fps", 24)
                
                formula = shot.get("frame_count_formula")
                if formula:
                    length = self.calc_frame_count(duration, fps, formula)
                elif shot.get("model", "").lower().startswith("ltx") or "ltx" in shot.get("workflow", "").lower():
                    # Legacy heuristic for LTX
                    length = int(duration * fps) + 1
                else:
                    length = int(duration * fps)

                len_key = "length" if "length" in params else "length_node_id"
                self._update_param(workflow, params, len_key, length, 
                                     ["length", "frames", "num_frames", "value", "value_4"], "video length")
            
            # Width & Height (Optional)
            if "width" in params:
                self._update_param(workflow, params, "width", shot.get("width", 1280), 
                                     ["width", "value"], "image width", required=False)
            if "height" in params:
                self._update_param(workflow, params, "height", shot.get("height", 720), 
                                     ["height", "value"], "image height", required=False)

            save_key = "save" if "save" in params else "save_node_id"
            self._update_param(workflow, params, save_key, f"{shot_id}", 
                                 ["filename_prefix", "filenames_prefix", "filename", "path", "value"], "save node prefix")

            if dry_run:
                report["status"] = "dry_run"
                return report

            prompt_id = self.client.queue_prompt(workflow)
            history = self.client.wait_for_completion(prompt_id)
            outputs = self.client.get_output_files(history)
            
            if not outputs:
                raise RuntimeError("No output files found")
                
            output_type = shot.get("output_type", "video")
            if output_type == "image":
                output_info = self.select_image_output(outputs)
            else:
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
