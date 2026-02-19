import os
import numpy as np
import onnxruntime as ort
from PIL import Image
from functools import lru_cache
from typing import Any, Dict, List, Optional

# Keep COCO_NAMES here (or import from a constants module)
COCO_NAMES = [
  "person","bicycle","car","motorcycle","airplane","bus","train","truck","boat","traffic light",
  "fire hydrant","stop sign","parking meter","bench","bird","cat","dog","horse","sheep","cow",
  "elephant","bear","zebra","giraffe","backpack","umbrella","handbag","tie","suitcase","frisbee",
  "skis","snowboard","sports ball","kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket","bottle",
  "wine glass","cup","fork","knife","spoon","bowl","banana","apple","sandwich","orange",
  "broccoli","carrot","hot dog","pizza","donut","cake","chair","couch","potted plant","bed",
  "dining table","toilet","tv","laptop","mouse","remote","keyboard","cell phone","microwave","oven",
  "toaster","sink","refrigerator","book","clock","vase","scissors","teddy bear","hair drier","toothbrush"
]


Detection = Dict[str, Any]

@lru_cache(maxsize=8)
def _get_session(model_path: str) -> ort.InferenceSession:
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"ONNX model not found at {model_path}")

    # CPU-only providers
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    # optional sanity check (one-time per model_path)
    inp = sess.get_inputs()[0]
    out = sess.get_outputs()[0]
    if inp.shape and len(inp.shape) != 4:
        raise RuntimeError(f"Unexpected input shape: {inp.shape}")
    # (don’t over-check output since ONNX exports vary)
    return sess


class YOLOOnnxDetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        conf: Optional[float] = None,
        iou: Optional[float] = None,
        input_size: int = 640,
    ):
        # Defaults: args override env; env override fallback
        self.model_path = model_path or os.getenv("YOLO_ONNX", "/app/models/yolov8n.onnx")
        self.conf = float(conf if conf is not None else os.getenv("YOLO_CONF", "0.25"))
        self.iou = float(iou if iou is not None else os.getenv("YOLO_IOU", "0.45"))
        self.input_size = int(input_size)

        # create/load once (cached across instances)
        self.sess = _get_session(self.model_path)
        self.in_name = self.sess.get_inputs()[0].name

    # ---- keep your helpers basically the same ----
    def _letterbox(self, im: Image.Image, new_shape: int):
        w, h = im.size
        scale = new_shape / max(w, h)
        nw, nh = int(w * scale), int(h * scale)
        im_resized = im.resize((nw, nh))
        canvas = Image.new("RGB", (new_shape, new_shape), (114, 114, 114))
        pad_x = (new_shape - nw) // 2
        pad_y = (new_shape - nh) // 2
        canvas.paste(im_resized, (pad_x, pad_y))
        return canvas, scale, pad_x, pad_y, w, h

    def _nms(self, boxes, scores, iou_thres):
        idxs = scores.argsort()[::-1]
        keep = []
        while idxs.size > 0:
            i = idxs[0]
            keep.append(i)
            if idxs.size == 1:
                break
            rest = idxs[1:]
            xx1 = np.maximum(boxes[i, 0], boxes[rest, 0])
            yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
            xx2 = np.minimum(boxes[i, 2], boxes[rest, 2])
            yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
            area_r = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
            union = area_i + area_r - inter + 1e-6
            iou = inter / union
            idxs = rest[iou <= iou_thres]
        return keep

    def detect(self, image_path: str) -> List[Detection]:
        im = Image.open(image_path).convert("RGB")
        im_lb, scale, pad_x, pad_y, orig_w, orig_h = self._letterbox(im, self.input_size)

        x = np.asarray(im_lb).astype(np.float32) / 255.0
        x = np.transpose(x, (2, 0, 1))[None, ...]  # 1x3xSxS

        outputs = self.sess.run(None, {self.in_name: x})
        pred = np.squeeze(outputs[0])

        # Handle common YOLOv8 ONNX layouts
        if pred.ndim == 2 and pred.shape[0] in (84, 85):
            pred = pred.T
        elif pred.ndim == 3:
            pred = np.squeeze(pred)
            if pred.shape[0] in (84, 85):
                pred = pred.T

        xywh = pred[:, 0:4]
        cls_scores = pred[:, 4:]  # 80

        cls_id = np.argmax(cls_scores, axis=1)
        cls_conf = cls_scores[np.arange(cls_scores.shape[0]), cls_id]

        mask = cls_conf >= self.conf
        xywh = xywh[mask]
        cls_id = cls_id[mask]
        cls_conf = cls_conf[mask]

        if xywh.shape[0] == 0:
            return []

        x_c, y_c, w, h = xywh[:, 0], xywh[:, 1], xywh[:, 2], xywh[:, 3]
        x1 = x_c - w / 2
        y1 = y_c - h / 2
        x2 = x_c + w / 2
        y2 = y_c + h / 2
        boxes = np.stack([x1, y1, x2, y2], axis=1)

        keep = self._nms(boxes, cls_conf, self.iou)
        boxes = boxes[keep]
        cls_id = cls_id[keep]
        cls_conf = cls_conf[keep]

        # de-letterbox
        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - pad_x) / scale
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - pad_y) / scale

        # clip
        boxes[:, 0] = np.clip(boxes[:, 0], 0, orig_w)
        boxes[:, 2] = np.clip(boxes[:, 2], 0, orig_w)
        boxes[:, 1] = np.clip(boxes[:, 1], 0, orig_h)
        boxes[:, 3] = np.clip(boxes[:, 3], 0, orig_h)

        dets: List[Detection] = []
        for i in range(boxes.shape[0]):
            cid = int(cls_id[i])
            label = COCO_NAMES[cid] if cid < len(COCO_NAMES) else str(cid)
            dets.append(
                {
                    "label": label,
                    "confidence": float(cls_conf[i]),
                    "bbox_xyxy": [float(v) for v in boxes[i].tolist()],
                }
            )
        return dets
