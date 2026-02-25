import os
from typing import List, Dict, Any, Optional

from groundingdino.util.inference import load_model, load_image, predict

_MODEL = None
_DEVICE = None

def _get_device() -> str:
    # Force CPU unless explicitly set otherwise
    return os.getenv("GROUNDINGDINO_DEVICE", "cpu").lower().strip()

def _get_model():
    global _MODEL, _DEVICE
    device = _get_device()

    if _MODEL is not None and _DEVICE == device:
        return _MODEL, _DEVICE

    cfg = os.getenv("GROUNDINGDINO_CONFIG", "/app/models/GroundingDINO_SwinT_OGC.py")
    weights = os.getenv("GROUNDINGDINO_WEIGHTS", "/app/models/groundingdino_swint_ogc.pth")

    model = load_model(cfg, weights)

    # Some GroundingDINO builds will default to cuda internally; force it:
    try:
        model = model.to(device)
    except Exception:
        pass

    _MODEL = model
    _DEVICE = device
    return _MODEL, _DEVICE

class GroundingDINODetector:
    name = "groundingdino"

    def detect(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        box_threshold: Optional[float] = None,
        text_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        model, device = _get_model()

        prompt = prompt or os.getenv(
            "GROUNDINGDINO_PROMPT",
            "pole mounted transformer. distribution transformer. transformer can."
        )
        box_threshold = float(box_threshold) if box_threshold is not None else float(os.getenv("GROUNDINGDINO_BOX_THRESHOLD", "0.35"))
        text_threshold = float(text_threshold) if text_threshold is not None else float(os.getenv("GROUNDINGDINO_TEXT_THRESHOLD", "0.25"))

        image_source, image = load_image(image_path)

        boxes, logits, phrases = predict(
            model=model,
            image=image,
            caption=prompt,
            box_threshold=box_threshold,
            text_threshold=text_threshold,
            device=device,   
        )

        h, w = image_source.shape[:2]
        detections: List[Dict[str, Any]] = []

        # boxes from helper are normalized cxcywh -> convert to pixel xyxy
        for box, logit, phrase in zip(boxes, logits, phrases):
            cx, cy, bw, bh = box.tolist()
            x1 = (cx - bw / 2.0) * w
            y1 = (cy - bh / 2.0) * h
            x2 = (cx + bw / 2.0) * w
            y2 = (cy + bh / 2.0) * h

            detections.append({
                "label": str(phrase).strip(),
                "confidence": float(logit),
                "bbox_xyxy": [float(x1), float(y1), float(x2), float(y2)],
            })

        return detections