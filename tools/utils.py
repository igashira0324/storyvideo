import os
import json
from typing import Any, Dict

def load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def get_project_path(project_dir: str, sub_path: str) -> str:
    return os.path.join(project_dir, sub_path)
