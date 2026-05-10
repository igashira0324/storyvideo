import os
import json
import time
import uuid
import requests
from typing import Any, Dict, Optional, Tuple

class ComfyUIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client_id = str(uuid.uuid4())

    def upload_image(self, image_path: str, overwrite: bool = True) -> str:
        """Uploads an image to ComfyUI and returns the filename."""
        url = f"{self.base_url}/upload/image"
        with open(image_path, "rb") as f:
            files = {"image": f}
            data = {"overwrite": "true" if overwrite else "false"}
            res = requests.post(url, files=files, data=data)
        res.raise_for_status()
        return res.json()["name"]

    def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """Queues a prompt (workflow) and returns the prompt_id."""
        url = f"{self.base_url}/prompt"
        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }
        res = requests.post(url, json=payload)
        res.raise_for_status()
        data = res.json()

        if "error" in data or "node_errors" in data:
            raise RuntimeError(
                f"ComfyUI prompt validation failed: "
                f"error={data.get('error')}, node_errors={data.get('node_errors')}"
            )

        if "prompt_id" not in data:
            raise RuntimeError(f"ComfyUI did not return prompt_id: {data}")

        return data["prompt_id"]

    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Gets the history for a specific prompt_id."""
        url = f"{self.base_url}/history/{prompt_id}"
        res = requests.get(url)
        res.raise_for_status()
        history = res.json()
        return history.get(prompt_id)

    def wait_for_completion(self, prompt_id: str, timeout_sec: int = 1800, poll_interval: int = 5) -> Dict[str, Any]:
        """Polls for completion of a prompt."""
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            history = self.get_history(prompt_id)
            if history and "outputs" in history:
                return history
            time.sleep(poll_interval)
        raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout_sec} seconds.")

    def get_output_files(self, history: Dict[str, Any]) -> list[Dict[str, str]]:
        """Extracts output file info from history."""
        output_files = []
        outputs = history.get("outputs", {})
        for node_id, node_output in outputs.items():
            for key in ["videos", "gifs", "images"]:
                if key in node_output:
                    for item in node_output[key]:
                        output_files.append(item)
        return output_files

    def download_file(self, filename: str, subfolder: str, type: str, dest_path: str):
        """Downloads a file from ComfyUI."""
        url = f"{self.base_url}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": type
        }
        res = requests.get(url, params=params, stream=True)
        res.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in res.iter_content(chunk_size=8192):
                f.write(chunk)
