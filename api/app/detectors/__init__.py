from .yolo_onnx import YOLOOnnxDetector

def get_detector(name: str, **kwargs):
    if name == "yolo_onnx":
        return YOLOOnnxDetector(**kwargs)
    raise ValueError(f"Unknown detector: {name}")
