from fastapi import FastAPI

app = FastAPI(title="Asset Identification API")

@app.get("/")
def read_root():
    return {"message": "Asset Identification API is running 🚀"}
