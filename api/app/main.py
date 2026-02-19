import os
import uuid
import json
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .db import engine, get_db
from .models import Photo, Run, Step, Base
from .pipeline import PIPELINE_STEPS
from .worker import celery_app
from .schemas import PhotoOut, RunOut, StepOut

app = FastAPI(title="Asset Identification API")

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://assets.brehfamily.com",
        "http://192.168.1.114:3000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from sqlalchemy.exc import OperationalError
import time

@app.on_event("startup")
def startup_db():
    # Create tables on startup (MVP) with retry to avoid postgres cold-start race
    for _ in range(30):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            time.sleep(1)
    raise RuntimeError("Database not ready after waiting")


def step_to_out(step: Step) -> StepOut:
    try:
        details = json.loads(step.details_json or "{}")
    except Exception:
        details = {"raw": step.details_json}
    return StepOut(
        id=step.id,
        name=step.name,
        status=step.status,
        details=details,
        updated_at=step.updated_at,
    )

@app.get("/")
def read_root():
    return {"message": "Asset Identification API is running ??"}

@app.post("/photos/upload", response_model=PhotoOut)
async def upload_photo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}_{file.filename}"
    stored_path = os.path.join("uploads", stored_name)  # stored relative to /app
    abs_path = os.path.join(UPLOAD_DIR, stored_name)

    contents = await file.read()
    with open(abs_path, "wb") as f:
        f.write(contents)

    photo = Photo(
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        stored_path=stored_path,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo

@app.get("/photos", response_model=list[PhotoOut])
def list_photos(db: Session = Depends(get_db)):
    return db.query(Photo).order_by(Photo.id.desc()).all()

@app.get("/photos/{photo_id}", response_model=PhotoOut)
def get_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photo

@app.post("/photos/{photo_id}/run", response_model=RunOut)
def start_run(photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    run = Run(
    photo_id=photo_id,
    status="queued",
    detector_name="yolo_onnx",
    detector_params_json=json.dumps({
        "conf": float(os.getenv("YOLO_CONF", "0.25")),
        "iou": float(os.getenv("YOLO_IOU", "0.45")),
        "input_size": 640
    }),
)

    db.add(run)
    db.commit()
    db.refresh(run)

    # Create step records
    for name in PIPELINE_STEPS:
        step = Step(run_id=run.id, name=name, status="pending", details_json="{}")
        db.add(step)
    db.commit()

    # Enqueue async pipeline
    celery_app.send_task("app.tasks.run_pipeline", args=[run.id])

    # Return run w/ steps
    run = db.query(Run).filter(Run.id == run.id).first()
    steps = db.query(Step).filter(Step.run_id == run.id).order_by(Step.id.asc()).all()

    return RunOut(
        id=run.id,
        photo_id=run.photo_id,
        status=run.status,
        created_at=run.created_at,
        steps=[step_to_out(s) for s in steps],
    )

@app.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    steps = db.query(Step).filter(Step.run_id == run.id).order_by(Step.id.asc()).all()
    return RunOut(
        id=run.id,
        photo_id=run.photo_id,
        status=run.status,
        created_at=run.created_at,
        steps=[step_to_out(s) for s in steps],
    )

@app.post("/photos/{photo_id}/feedback")
def submit_feedback(
    photo_id: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    MVP feedback endpoint.
    Expected JSON example:
    {
      "run_id": 12,
      "correct": false,
      "reasons": ["missed_object", "wrong_class"],
      "notes": "missed insulator; transformer box off"
    }
    """
    # For MVP: store feedback inside the summary step details of the run (cheap + quick).
    # Later: make a real feedback table.
    run_id = payload.get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")

    run = db.query(Run).filter(Run.id == run_id, Run.photo_id == photo_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found for this photo")

    summary_step = db.query(Step).filter(Step.run_id == run_id, Step.name == "summary").first()
    if not summary_step:
        raise HTTPException(status_code=404, detail="Summary step not found")

    try:
        details = json.loads(summary_step.details_json or "{}")
    except Exception:
        details = {}

    details["human_feedback"] = {
        "correct": bool(payload.get("correct")),
        "reasons": payload.get("reasons", []),
        "notes": payload.get("notes", ""),
    }

    summary_step.details_json = json.dumps(details)
    db.commit()

    return JSONResponse({"ok": True})
@app.get("/photos/{photo_id}/runs", response_model=list[RunOut])
def list_runs_for_photo(photo_id: int, db: Session = Depends(get_db)):
    runs = db.query(Run).filter(Run.photo_id == photo_id).order_by(Run.id.desc()).all()
    out = []
    for run in runs:
        steps = db.query(Step).filter(Step.run_id == run.id).order_by(Step.id.asc()).all()
        out.append(RunOut(
            id=run.id,
            photo_id=run.photo_id,
            status=run.status,
            created_at=run.created_at,
            steps=[step_to_out(s) for s in steps],
        ))
    return out

@app.get("/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db), limit: int = 25):
    runs = db.query(Run).order_by(Run.id.desc()).limit(limit).all()
    out = []
    for run in runs:
        steps = db.query(Step).filter(Step.run_id == run.id).order_by(Step.id.asc()).all()
        out.append(RunOut(
            id=run.id,
            photo_id=run.photo_id,
            status=run.status,
            created_at=run.created_at,
            steps=[step_to_out(s) for s in steps],
        ))
    return out

@app.get("/runs/{run_id}/overlay")
def get_run_overlay(run_id: int, db: Session = Depends(get_db)):
    step = db.query(Step).filter(Step.run_id == run_id, Step.name == "asset_detection").first()
    if not step:
        raise HTTPException(status_code=404, detail="asset_detection step not found")

    try:
        details = json.loads(step.details_json or "{}")
    except Exception:
        details = {}

    rel = details.get("overlay_path")
    if not rel:
        raise HTTPException(status_code=404, detail="overlay not available yet")

    abs_path = os.path.join("/app", rel)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="overlay file missing")

    return FileResponse(abs_path, media_type="image/jpeg")

