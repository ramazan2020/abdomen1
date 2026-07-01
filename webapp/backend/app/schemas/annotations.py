from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AnnotationCreateRequest(BaseModel):
    image_id: int
    class_type: str = "lesion"  # "lesion" | "organ"
    class_id: int
    geometry_type: str  # "bbox" | "polygon"
    geometry: dict[str, Any]


class AnnotationUpdateRequest(BaseModel):
    class_id: int | None = None
    geometry: dict[str, Any] | None = None


class AnnotationResponse(BaseModel):
    id: UUID
    case_id: UUID
    image_id: int
    class_type: str
    class_id: int
    geometry_type: str
    geometry: dict[str, Any]
    source: str
    confidence: float | None
    status: str
    derived_from_annotation_id: UUID | None
    included_in_training_pool: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnotationTrainingPoolRequest(BaseModel):
    in_pool: bool


class AnnotationZipImportDetail(BaseModel):
    case_num: str
    prefix: str
    matched: bool | None
    case_id: str | None = None
    sent: int
    skipped: int
    note: str | None = None


class AnnotationZipImportResponse(BaseModel):
    total_sent: int
    total_skipped: int
    details: list[AnnotationZipImportDetail]
