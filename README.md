# 🏗️ Asset Identification Platform

An extensible, async, infrastructure-focused computer vision pipeline
for detecting, analyzing, and evaluating utility assets from field
photographs.

------------------------------------------------------------------------

# 🚀 Overview

Asset Identification is a full-stack, containerized system designed to:

-   📸 Accept field photo uploads
-   🔍 Run structured multi-step ML pipelines
-   🧠 Detect infrastructure assets (poles, transformers, conductors,
    etc.)
-   🖼️ Render visual overlays with bounding boxes
-   📊 Track step-by-step execution state
-   👨‍🔬 Capture structured human feedback
-   🌍 Be securely exposed to the internet via Cloudflare Tunnel

This system is built as a scalable foundation for utility infrastructure
inspection, ML experimentation, and future production deployment.

------------------------------------------------------------------------

# 🧱 System Architecture

The system is fully containerized via Docker Compose.

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

(metadata DB) (task queue) (future object (async ML storage) pipeline)

------------------------------------------------------------------------

# 📂 Repository Structure

. ├── api/ │ ├── app/ │ │ ├── main.py \# FastAPI routes │ │ ├──
models.py \# SQLAlchemy models │ │ ├── schemas.py \# Pydantic response
models │ │ ├── tasks.py \# Celery pipeline execution │ │ ├── worker.py
\# Celery app config │ │ ├── pipeline.py \# Ordered pipeline steps │ │
├── vision.py \# YOLO detection logic │ │ ├── overlay.py \# Bounding box
rendering │ │ ├── db.py \# Database connection │ │ │ │ │ └── detectors/
\# Pluggable detector backends │ └── Dockerfile │ ├── web/ │ ├── src/ │
│ ├── App.jsx \# Main React UI │ │ └── styles.css │ ├── vite.config.js │
└── Dockerfile │ ├── docker-compose.yml └── README.md

------------------------------------------------------------------------

# 🔁 End-to-End Execution Flow

## 1️⃣ Upload Photo

POST /photos/upload

-   Image saved to /app/uploads
-   Photo row created in Postgres

## 2️⃣ Start Pipeline Run

POST /photos/{photo_id}/run

API: - Creates Run record (status = queued) - Creates Step records
(pending) - Enqueues Celery async task

## 3️⃣ Async Pipeline Execution

Worker executes:

run_pipeline(run_id)

Pipeline steps:

1.  ingest\
2.  extract_exif\
3.  utility_gate\
4.  asset_detection (YOLO ONNX)\
5.  condition_assessment\
6.  summary

Each step: - Updates DB status - Stores structured JSON output - Becomes
visible live in UI

------------------------------------------------------------------------

# 🔍 Object Detection

vision.py:

-   Loads YOLO ONNX model (lazy-loaded singleton)
-   Runs inference
-   Applies confidence + NMS filtering
-   Returns bounding boxes

------------------------------------------------------------------------

# 🖼 Overlay Rendering

overlay.py:

-   Draws bounding boxes
-   Saves overlay image
-   Path stored in DB

Served via:

GET /runs/{run_id}/overlay

------------------------------------------------------------------------

# 🗄 Database Schema

Photo - id - filename - content_type - stored_path - uploaded_at

Run - id - photo_id - status (queued / running / done / failed) -
detector_name - detector_params_json - created_at

Step - id - run_id - name - status - details_json - updated_at

------------------------------------------------------------------------

# 🌐 Cloudflare Tunnel Setup

Public URLs:

-   https://assets.brehfamily.com → Web UI
-   https://api-assets.brehfamily.com → API

Tunnel configuration (example):

tunnel: `<TUNNEL_ID>`{=html} credentials-file:
/etc/cloudflared/`<TUNNEL_ID>`{=html}.json

ingress: - hostname: assets.brehfamily.com service:
http://127.0.0.1:3000

-   hostname: api-assets.brehfamily.com service: http://127.0.0.1:8000

-   service: http_status:404

------------------------------------------------------------------------

# 🔧 Environment Variables

API: - DATABASE_URL - REDIS_URL

WEB: - VITE_API_URL

YOLO: - YOLO_ONNX - YOLO_CONF - YOLO_IOU

------------------------------------------------------------------------

# 🧠 Design Philosophy

-   Async-first architecture
-   Pluggable detectors
-   Structured step tracking
-   Cloud-native deployment
-   Feedback loop ready for ML retraining

------------------------------------------------------------------------

# 🛣 Roadmap

-   Replace stub condition model
-   Replace stub utility gate
-   Add detector registry
-   Add proper Feedback table
-   Move uploads to MinIO
-   Add authentication
-   Add model version tracking
-   Add metrics dashboard

------------------------------------------------------------------------

# 🏁 Running the System

docker compose up -d --build

Web UI: http://localhost:3000

API Docs: http://localhost:8000/docs

------------------------------------------------------------------------

# 👨‍🔬 Author

Designed as a modular infrastructure ML experimentation platform.
