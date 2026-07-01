from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RunDefaultRequest(BaseModel):
    case_id: UUID


class RunComparisonRequest(BaseModel):
    case_id: UUID
    model_version_ids: list[UUID] | None = None


class InferenceRunResponse(BaseModel):
    id: UUID
    model_version_id: UUID
    model_name: str
    architecture: str
    conf_threshold: float
    min_slice_run: int
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InferenceBatchResponse(BaseModel):
    id: UUID
    case_id: UUID
    batch_type: str
    status: str
    created_at: datetime
    runs: list[InferenceRunResponse]

    model_config = {"from_attributes": True}
