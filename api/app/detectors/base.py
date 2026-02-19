from abc import ABC, abstractmethod
from typing import List, Dict, Any

Detection = Dict[str, Any]  # {"label": str, "score": float, "bbox_xyxy": [x1,y1,x2,y2]}

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, image_path: str) -> List[Detection]:
        pass
