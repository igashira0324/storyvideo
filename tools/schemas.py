from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, conlist, model_validator

class NodeConfig(BaseModel):
    node_id: str
    input_key: Optional[str] = None

class WorkflowParams(BaseModel):
    # Support for both new structured format and old flat format
    model_config = {"extra": "allow"}
    
    # New structured format keys
    positive: Optional[NodeConfig] = None
    negative: Optional[NodeConfig] = None
    image: Optional[NodeConfig] = None
    seeds: Optional[List[NodeConfig]] = None
    length: Optional[NodeConfig] = None
    save: Optional[NodeConfig] = None
    
    # Old flat format keys (for backward compatibility)
    image_node_id: Optional[str] = None
    positive_node_id: Optional[str] = None
    negative_node_id: Optional[str] = None
    seed_node_ids: Optional[List[str]] = None
    length_node_id: Optional[str] = None
    save_node_id: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def check_unknown_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            allowed_keys = {
                "positive", "negative", "image", "seeds", "length", "save",
                "width", "height", "fps", "frame_count_formula", "workflow", "workflow_params", # common keys in presets
                "image_node_id", "positive_node_id", "negative_node_id",
                "seed_node_ids", "seed_node_id", "length_node_id", "save_node_id"
            }
            extra_keys = set(data.keys()) - allowed_keys
            if extra_keys:
                import logging
                logging.getLogger(__name__).warning(f"Unknown keys in workflow_params: {extra_keys}. This might be a typo.")
        return data

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
    t2i_prompt: Optional[str] = None
    transition: Optional[str] = None
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
