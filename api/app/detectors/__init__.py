from .yolo_onnx import YOLOOnnxDetector
from .grounding_dino import GroundingDINODetector

def get_detector(name: str, **kwargs):
    if name == "yolo_onnx":
        return YOLOOnnxDetector(**kwargs)
    if name in ("groundingdino", "dino", "grounding_dino"):
        return GroundingDINODetector()
    raise ValueError(f"Unknown detector: {name}")
