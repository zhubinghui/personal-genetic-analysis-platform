import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID = Field(validation_alias="id")
    status: str
    stage: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class DunedinPaceDimensions(BaseModel):
    cardiovascular: dict[str, float | None]
    metabolic: dict[str, float | None]
    renal: dict[str, float | None]
    hepatic: dict[str, float | None]
    pulmonary: dict[str, float | None]
    immune: dict[str, float | None]
    periodontal: dict[str, float | None]
    cognitive: dict[str, float | None]
    physical: dict[str, float | None]


class AnalysisResultOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    sample_id: uuid.UUID

    # QC
    qc_passed: bool | None
    n_probes_before: int | None
    n_probes_after: int | None
    detection_p_failed_fraction: float | None

    # 时钟评分
    chronological_age: int | None
    horvath_age: float | None
    grimage_age: float | None
    phenoage_age: float | None
    dunedinpace: float | None
    biological_age_acceleration: float | None

    # DunedinPACE 19 维度
    dunedinpace_dimensions: dict | None

    computed_at: datetime

    model_config = {"from_attributes": True}
