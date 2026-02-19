# AssetIdentification

🏗️ Asset Identification Platform

An extensible, async, utility-focused computer vision pipeline for detecting, analyzing, and evaluating infrastructure assets from field photographs.

🚀 Overview

Asset Identification is a full-stack, containerized system designed to:

📸 Accept field photo uploads

🔍 Run structured multi-step ML pipelines

📦 Detect infrastructure assets (poles, transformers, conductors, etc.)

🧠 Assess condition (extensible)

🖼️ Render visual overlays

👨‍🔬 Capture structured human feedback

🌍 Be safely exposed via Cloudflare Tunnel

This project is intentionally built with production architecture patterns, even though it is currently MVP-level in scope.

🧱 System Architecture

The system is fully containerized via Docker Compose.

                        ┌────────────────────────┐
                        │   Cloudflare Tunnel    │
                        │ assets.brehfamily.com  │
                        └────────────┬───────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │        WEB (Vite)      │
                        │ React UI (port 3000)   │
                        └────────────┬───────────┘
                                     │ REST
                                     ▼
                        ┌────────────────────────┐
                        │        API (FastAPI)   │
                        │       (port 8000)      │
                        └────────────┬───────────┘
                                     │ DB + Tasks
           ┌─────────────────────────┼──────────────────────────┐
           ▼                         ▼                          ▼
   ┌──────────────┐         ┌──────────────┐           ┌──────────────┐
   │  Postgres    │         │   Redis      │           │   MinIO      │
   │ (metadata)   │         │ (task queue) │           │ (future S3)  │
   └──────────────┘         └──────────────┘           └──────────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │      Celery Worker     │
                        │   Async ML Pipeline    │
                        └────────────────────────┘

📂 Repository Structure
.
├── api/
│   ├── app/
│   │   ├── main.py          # FastAPI routes
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic response models
│   │   ├── tasks.py         # Celery pipeline execution
│   │   ├── worker.py        # Celery app config
│   │   ├── pipeline.py      # Ordered pipeline steps
│   │   ├── vision.py        # YOLO detection logic
│   │   ├── overlay.py       # Bounding box rendering
│   │   ├── db.py            # Database connection
│   │   └── detectors/       # Pluggable detector backends
│   └── Dockerfile
│
├── web/
│   ├── src/
│   │   ├── App.jsx          # Main React UI
│   │   └── styles.css
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml
└── README.md

🔁 End-to-End Flow
1️⃣ Upload

User uploads image via React UI.

POST /photos/upload


File saved to /app/uploads

Photo row created in Postgres

2️⃣ Start Run
POST /photos/{photo_id}/run


API:

Creates Run record (status=queued)

Creates Step records (pending)

Enqueues Celery task

3️⃣ Async Pipeline (Worker)

Celery executes:

run_pipeline(run_id)


Pipeline steps:

ingest

extract_exif

utility_gate (future classifier)

asset_detection (YOLO ONNX)

condition_assessment

summary

Each step:

Updates DB status

Stores JSON details

Is visible live in UI

4️⃣ Detection

vision.py:

Loads YOLO ONNX model (lazy load, singleton)

Runs inference

Returns normalized bounding boxes

5️⃣ Overlay Rendering

overlay.py:

Draws bounding boxes

Saves rendered image

Stored in uploads/overlays/

Served via:

GET /runs/{run_id}/overlay

6️⃣ Live Polling UI

React:

Polls /runs/{run_id} every 1s

Displays:

Step progress

JSON output

Overlay image

🗄️ Data Model
Photo
Field	Purpose
id	Primary key
filename	Original filename
stored_path	Local storage path
uploaded_at	Timestamp
Run
Field	Purpose
id	Primary key
photo_id	FK to Photo
status	queued/running/done/failed
created_at	Timestamp
Step
Field	Purpose
run_id	FK to Run
name	ingest / asset_detection / etc
status	pending/running/complete
details_json	JSON results
updated_at	Timestamp
🌍 Public Access via Cloudflare Tunnel

Two hostnames are configured:

Hostname	Service
assets.brehfamily.com	React Web UI
api-assets.brehfamily.com	FastAPI backend

Cloudflare config:

ingress:
  - hostname: assets.brehfamily.com
    service: http://127.0.0.1:3000
  - hostname: api-assets.brehfamily.com
    service: http://127.0.0.1:8000
  - service: http_status:404

🔐 CORS Configuration

API explicitly allows:

allow_origins=[
    "http://localhost:3000",
    "http://192.168.1.114:3000",
    "https://assets.brehfamily.com",
]

🧠 Detector Architecture

Detectors are pluggable.

Current:

YOLO ONNX

Future:

Grounding DINO (zero-shot)

Custom utility-trained model

Fine-tuned ONNX export

Each run stores:

{
  "detector_name": "yolo_onnx",
  "detector_params": {
    "conf": 0.25,
    "iou": 0.45
  }
}

🏃 Running Locally
docker compose up -d --build


Access:

http://localhost:3000

🌐 Running via Tunnel

Ensure:

VITE_API_URL=https://api-assets.brehfamily.com


Then:

https://assets.brehfamily.com

🧪 Development Philosophy

This system is intentionally built with:

Async execution model

Persistent step tracking

Model abstraction

Explicit metadata storage

Production-style separation of concerns

Even though the models are MVP-level, the architecture is production-ready.

🔮 Roadmap
Phase 1 (Current)

Basic detection

Overlay rendering

Feedback capture

Phase 2

Real utility classifier

Structured feedback table

Model metrics dashboard

Phase 3

Fine-tuning loop

Semi-supervised learning

Active learning selection

Phase 4

Multi-tenant support

Role-based access

S3-backed image storage

Scalable worker pool

🎯 Long-Term Vision

The goal is to evolve into:

A structured, ML-powered infrastructure intelligence platform capable of assisting utilities with asset identification, condition scoring, and data validation workflows.

🧰 Tech Stack

FastAPI

React (Vite)

Celery

Redis

Postgres

Docker

YOLO (ONNX)

Cloudflare Tunnel

👤 Author

Built as a structured ML + infrastructure platform prototype.