import json
import os
import time
import exifread
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Run, Step, Photo

from .detectors import get_detector
from .overlay import render_overlay
from .pipeline import PIPELINE_STEPS


def _db() -> Session:
    return SessionLocal()

def _enabled_detectors() -> list[str]:
    raw = os.getenv("DETECTORS", "yolo_onnx")
    return [x.strip() for x in raw.split(",") if x.strip()]

def _set_step(db: Session, run_id: int, step_name: str, status: str, details: dict | None = None):
    step = db.query(Step).filter(Step.run_id == run_id, Step.name == step_name).one()
    step.status = status
    if details is not None:
        step.details_json = json.dumps(details)
    db.commit()

def _set_run_status(db: Session, run_id: int, status: str):
    run = db.query(Run).filter(Run.id == run_id).one()
    run.status = status
    db.commit()

def _get_photo_path(db: Session, run_id: int) -> str:
    run = db.query(Run).filter(Run.id == run_id).one()
    photo = db.query(Photo).filter(Photo.id == run.photo_id).one()
    return os.path.join("/app", photo.stored_path)

def _extract_exif(file_path: str) -> dict:
    exif_data = {}
    try:
        with open(file_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
        # keep it a bit smaller for now
        for k, v in tags.items():
            exif_data[k] = str(v)
    except Exception as e:
        exif_data = {"error": str(e)}
    return exif_data

def _fake_utility_gate() -> dict:
    # placeholder � later we swap in a real classifier
    return {"is_utility_infrastructure": True, "confidence": 0.73, "notes": "stub result"}

def _fake_asset_detection() -> dict:
    # placeholder � later we swap in YOLO output
    return {
        "detections": [
            {"label": "pole", "confidence": 0.81, "bbox": [0.12, 0.08, 0.35, 0.92]},
            {"label": "transformer", "confidence": 0.64, "bbox": [0.40, 0.25, 0.62, 0.55]},
            {"label": "conductor", "confidence": 0.58, "bbox": [0.05, 0.15, 0.95, 0.20]},
        ],
        "notes": "stub detections (normalized xyxy)",
    }

def _fake_condition_assessment() -> dict:
    return {
        "overall": "unknown",
        "confidence": 0.42,
        "reasons": ["no real model yet"],
    }

def _fake_summary(exif: dict, gate: dict, det: dict, cond: dict) -> dict:
    return {
        "headline": "Likely utility infrastructure (stub)",
        "gps": exif.get("GPS GPSLatitude", None),
        "timestamp": exif.get("EXIF DateTimeOriginal", None),
        "detected_counts": {
            "pole": sum(1 for d in det.get("detections", []) if d["label"] == "pole"),
            "transformer": sum(1 for d in det.get("detections", []) if d["label"] == "transformer"),
        },
        "condition": cond,
    }

from .worker import celery_app

@celery_app.task(bind=True)
def run_pipeline(self, run_id: int):
    db = _db()
    try:
        _set_run_status(db, run_id, "running")

        # Step 1: ingest
        _set_step(db, run_id, "ingest", "running", {"message": "verifying file exists"})
        time.sleep(0.5)
        photo_path = _get_photo_path(db, run_id)
        exists = os.path.exists(photo_path)
        if not exists:
            _set_step(db, run_id, "ingest", "failed", {"error": f"file not found: {photo_path}"})
            _set_run_status(db, run_id, "failed")
            return
        _set_step(db, run_id, "ingest", "complete", {"path": photo_path})

        # Step 2: EXIF
        _set_step(db, run_id, "extract_exif", "running", {"message": "extracting EXIF"})
        time.sleep(0.5)
        exif = _extract_exif(photo_path)
        _set_step(db, run_id, "extract_exif", "complete", {"exif": exif})

        # Step 3: utility gate
        _set_step(db, run_id, "utility_gate", "running", {"message": "running utility classifier (stub)"})
        time.sleep(0.8)
        gate = _fake_utility_gate()
        _set_step(db, run_id, "utility_gate", "complete", gate)

        # Step 4: detection (MULTI-MODEL: YOLO + GroundingDINO, etc.)
        enabled = _enabled_detectors()
        _set_step(
            db,
            run_id,
            "asset_detection",
            "running",
            {"message": f"running detectors: {', '.join(enabled)}"},
        )

        detectors_out: dict[str, dict] = {}
        base_dir_rel = f"uploads/overlays/run_{run_id}"
        base_dir_abs = os.path.join("/app", base_dir_rel)
        os.makedirs(base_dir_abs, exist_ok=True)

        for det_name in enabled:
            started = time.time()
            try:
                detector = get_detector(det_name)

                # Run detection
                detections = detector.detect(photo_path)

                # Save overlay image (unique per detector)
                overlay_rel = f"{base_dir_rel}/{det_name}.jpg"
                overlay_abs = os.path.join("/app", overlay_rel)
                render_overlay(photo_path, detections, overlay_abs)

                detectors_out[det_name] = {
                    "model": os.getenv("YOLO_MODEL", "yolov8n.pt") if det_name == "yolo_onnx" else det_name,
                    "count": len(detections),
                    "detections": detections[:200],  # avoid huge payloads
                    "overlay_path": overlay_rel,
                    "duration_s": round(time.time() - started, 3),
                }

            except Exception as e:
                detectors_out[det_name] = {
                    "error": str(e),
                    "duration_s": round(time.time() - started, 3),
                }

        # Keep backward-compatible fields for your existing summary step:
        # - "det" will represent YOLO if present; otherwise first available detector.
        if "yolo_onnx" in detectors_out and "detections" in detectors_out["yolo_onnx"]:
            det = detectors_out["yolo_onnx"]
        else:
            # pick first detector that succeeded
            det = next((v for v in detectors_out.values() if "detections" in v), {"count": 0, "detections": []})

        _set_step(
            db,
            run_id,
            "asset_detection",
            "complete",
            {
                "enabled": enabled,
                "detectors": detectors_out,
                "primary": "yolo_onnx" if "yolo_onnx" in detectors_out else (enabled[0] if enabled else None),
            },
        )

        # Step 5: condition
        _set_step(db, run_id, "condition_assessment", "running", {"message": "assessing condition (stub)"})
        time.sleep(0.8)
        cond = _fake_condition_assessment()
        _set_step(db, run_id, "condition_assessment", "complete", cond)

        # Step 6: summary
        _set_step(db, run_id, "summary", "running", {"message": "building summary"})
        time.sleep(0.3)
        summary = _fake_summary(exif=exif, gate=gate, det=det, cond=cond)
        _set_step(db, run_id, "summary", "complete", summary)

        _set_run_status(db, run_id, "done")

    except Exception as e:
        try:
            _set_run_status(db, run_id, "failed")
        except Exception:
            pass
        raise e
    finally:
        db.close()
