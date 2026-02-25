
🏗️ Asset Identification Platform
=================================

An extensible, async, infrastructure-focused computer vision pipeline
for detecting, analyzing, and evaluating utility assets from field photographs.

=====================================================================
🚀 OVERVIEW
=====================================================================

Asset Identification is a full-stack, containerized ML experimentation
platform designed to:

• 📸 Accept field photo uploads
• 🔁 Execute structured multi-step async pipelines
• 🤖 Run MULTIPLE detection models per photo (YOLO + GroundingDINO)
• 🖼 Render per-model bounding box overlays
• 📊 Track step-by-step execution state
• 🧠 Compare model outputs side-by-side
• 👨‍🔬 Capture structured human feedback
• 🌍 Expose securely via Cloudflare Tunnel

This system is built as a scalable foundation for utility infrastructure
inspection and ML experimentation.

=====================================================================
🧱 SYSTEM ARCHITECTURE
=====================================================================

                        Cloudflare Tunnel
                     assets.brehfamily.com
                                │
                                ▼
                          WEB (Vite + React)
                                │
                                ▼
                          API (FastAPI)
                                │
        ┌───────────────┬───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
     Postgres         Redis           MinIO        Celery Worker
  (metadata DB)   (task queue)    (future object)   (async ML pipeline)

=====================================================================
📂 REPOSITORY STRUCTURE
=====================================================================

.
├── api/
│   ├── app/
│   │   ├── main.py                # FastAPI routes
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── schemas.py             # Pydantic schemas
│   │   ├── tasks.py               # Celery pipeline execution
│   │   ├── worker.py              # Celery app config
│   │   ├── pipeline.py            # Ordered pipeline steps
│   │   ├── overlay.py             # Overlay rendering logic
│   │   ├── db.py                  # Database connection
│   │   └── detectors/             # Pluggable detector backends
│   │        ├── __init__.py
│   │        ├── yolo_onnx.py
│   │        └── grounding_dino.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── web/
│   ├── src/
│   │   ├── App.jsx                # Multi-model comparison UI
│   │   └── styles.css
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml
└── README.txt

=====================================================================
🔁 END‑TO‑END EXECUTION FLOW
=====================================================================

1️⃣ Upload Photo
----------------
POST /photos/upload

• Image saved to /app/uploads
• Photo row created in Postgres

2️⃣ Start Pipeline Run
----------------------
POST /photos/{photo_id}/run

API:
• Creates Run record (status = queued)
• Creates Step records (pending)
• Enqueues Celery async task

3️⃣ Async Pipeline Execution
----------------------------
Worker executes:

    run_pipeline(run_id)

Pipeline steps:

1. ingest
2. extract_exif
3. utility_gate
4. asset_detection (MULTI-MODEL)
5. condition_assessment
6. summary

Each step:
• Updates DB status
• Stores structured JSON output
• Becomes visible live in UI

=====================================================================
🔍 MULTI-MODEL DETECTION
=====================================================================

The platform now supports running multiple detectors per image.

Enabled detectors (example):

{
  "enabled": ["yolo_onnx", "groundingdino"],
  "primary": "yolo_onnx"
}

Each detector returns:

{
  "model": "...",
  "count": X,
  "detections": [...],
  "overlay_path": "...",
  "duration_s": ...
}

Overlays are generated per model:

uploads/overlays/run_{id}/yolo_onnx.jpg
uploads/overlays/run_{id}/groundingdino.jpg

The UI allows switching between detector overlays.

=====================================================================
🤖 SUPPORTED DETECTORS
=====================================================================

YOLO (ONNX Runtime)
-------------------
• Fast
• Fixed label set
• Lightweight
• Great for baseline comparisons

GroundingDINO (CPU Mode)
------------------------
• Prompt-driven zero-shot detection
• Flexible label sets
• Slower on CPU (~10–15s per image)
• Ideal for experimentation

GroundingDINO runs in CPU mode unless CUDA-enabled Torch is installed.

=====================================================================
🖼 OVERLAY RENDERING
=====================================================================

overlay.py:

• Draws bounding boxes
• Renders readable labels
• Saves per-model overlay image
• Uses DejaVu font (fonts-dejavu-core required)

Served via:

GET /runs/{run_id}/overlay?model={detector_name}

=====================================================================
🗄 DATABASE SCHEMA
=====================================================================

Photo
• id
• filename
• content_type
• stored_path
• uploaded_at

Run
• id
• photo_id
• status (queued / running / done / failed)
• created_at

Step
• id
• run_id
• name
• status
• details_json
• updated_at

=====================================================================
🌐 CLOUDFLARE TUNNEL
=====================================================================

Public URLs:

https://assets.brehfamily.com  → Web UI
https://api-assets.brehfamily.com → API

Example config:

tunnel: <TUNNEL_ID>
credentials-file: /etc/cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: assets.brehfamily.com
    service: http://127.0.0.1:3000
  - hostname: api-assets.brehfamily.com
    service: http://127.0.0.1:8000
  - service: http_status:404

=====================================================================
🔧 ENVIRONMENT VARIABLES
=====================================================================

API:
• DATABASE_URL
• REDIS_URL

YOLO:
• YOLO_MODEL
• YOLO_CONF
• YOLO_IOU

WEB:
• VITE_API_URL

=====================================================================
🧠 DESIGN PHILOSOPHY
=====================================================================

• Async-first architecture
• Pluggable detector registry
• Multi-model comparison
• Structured step tracking
• Cloud-native deployment
• Feedback loop ready for retraining
• Built for ML experimentation velocity

=====================================================================
🛣 ROADMAP
=====================================================================

• Replace stub condition model
• Replace stub utility gate
• Add formal detector registry
• Add Feedback table
• Move uploads to MinIO
• Add authentication
• Add model version tracking
• Add metrics dashboard
• Add multimodal transformer experiments

=====================================================================
🏁 RUNNING THE SYSTEM
=====================================================================

docker compose up -d --build

Web UI:
http://localhost:3000

API Docs:
http://localhost:8000/docs

=====================================================================
👨‍🔬 Author: Steven Brehmer

Modular infrastructure ML experimentation platform.
