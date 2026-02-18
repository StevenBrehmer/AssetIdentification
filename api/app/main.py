from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image
import exifread
import os
import uuid

app = FastAPI(title="Asset Identification API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def read_root():
    return {"message": "Asset Identification API is running ??"}


@app.post("/upload")
async def upload_photo(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extract EXIF
    exif_data = {}
    try:
        with open(file_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
            for tag in tags:
                exif_data[tag] = str(tags[tag])
    except Exception as e:
        exif_data = {"error": str(e)}

    # Simple pipeline steps (placeholder)
    pipeline = [
        {"step": "ingest", "status": "complete"},
        {"step": "extract_exif", "status": "complete"},
        {"step": "utility_classifier", "status": "pending"},
        {"step": "asset_detection", "status": "pending"},
        {"step": "condition_assessment", "status": "pending"},
    ]

    return JSONResponse(
        {
            "file_id": file_id,
            "filename": file.filename,
            "exif": exif_data,
            "pipeline": pipeline,
        }
    )
