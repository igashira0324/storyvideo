from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class VideoProvider(ABC):
    @abstractmethod
    def generate_shot(self, shot_data: Dict[str, Any], project_dir: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Generate a single video shot.
        Returns a report dictionary with status, output path, etc.
        """
        pass

    @abstractmethod
    def validate_shot(self, shot_data: Dict[str, Any], project_dir: str) -> Dict[str, Any]:
        """
        Validate a generated shot.
        """
        pass
