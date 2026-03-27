import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SampleUploadResponse(BaseModel):
    sample_id: uuid.UUID
    job_id: uuid.UUID
    array_type: str
    status: str
    message: str


class SampleOut(BaseModel):
    id: uuid.UUID
    array_type: str
    upload_status: str
    chronological_age: int | None
    uploaded_at: datetime
    deleted_at: datetime | None
    latest_job_id: uuid.UUID | None = None
    latest_job_status: str | None = None

    model_config = {"from_attributes": True}
