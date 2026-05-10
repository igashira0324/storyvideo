from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, conlist

class WorkflowParams(BaseModel):
    image_node_id: str
    positive_node_id: str
    negative_node_id: Optional[str] = None
    seed_node_ids: List[str]
    length_node_id: str
    save_node_id: str

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
