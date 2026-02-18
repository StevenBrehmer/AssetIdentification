from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

class PhotoOut(BaseModel):
    id: int
    filename: str
    content_type: str
    stored_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class StepOut(BaseModel):
    id: int
    name: str
    status: str
    details: Dict[str, Any]
    updated_at: datetime

class RunOut(BaseModel):
    id: int
    photo_id: int
    status: str
    created_at: datetime
    steps: List[StepOut]
