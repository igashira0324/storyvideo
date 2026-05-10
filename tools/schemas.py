from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, conlist

class NodeConfig(BaseModel):
    node_id: str
    input_key: Optional[str] = None

class WorkflowParams(BaseModel):
    # Allow both old-style flat strings and new-style NodeConfig objects/lists
    # We use Dict[str, Any] to be highly flexible for now, but validate internally if needed.
    # For backward compatibility and new features, we allow arbitrary keys.
    model_config = {"extra": "allow"}
    
    # Common keys for validation if they exist
    image_node_id: Optional[str] = None
    positive_node_id: Optional[str] = None
    negative_node_id: Optional[str] = None
    seed_node_ids: Optional[List[str]] = None
    length_node_id: Optional[str] = None
    save_node_id: Optional[str] = None

class Shot(BaseModel):
    id: str
    workflow: str
    input_image: str
    positive_prompt: str
    negative_prompt: str
    duration_sec: int = Field(ge=1, le=15)
    fps: int = 24
    seed: int
    subtitle: str
    narration: Optional[str] = None
    output: str
    frame_count_formula: Optional[str] = None
    workflow_params: WorkflowParams

class ShotPlan(BaseModel):
    project_name: str
    project_title: str
    composition_name: str = "FinalVideo"
    width: int = 1280
    height: int = 720
    fps: int = 24
    bgm: Optional[str] = None
    shots: conlist(Shot, min_length=1)
