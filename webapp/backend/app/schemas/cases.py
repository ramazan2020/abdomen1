from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CaseResponse(BaseModel):
    id: UUID
    case_label: str | None
    status: str
    review_status: str
    deidentified: bool
    n_slices: int | None
    validation_report: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseListItem(BaseModel):
    id: UUID
    case_label: str | None
    status: str
    review_status: str
    n_slices: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewStatusUpdateRequest(BaseModel):
    review_status: str  # unreviewed | in_review | reviewed | approved_for_training | excluded
