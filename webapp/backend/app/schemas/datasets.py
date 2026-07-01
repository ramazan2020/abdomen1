from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DatasetCreateRequest(BaseModel):
    name: str
    description: str | None = None
    source: str = "webapp"
    notes: str | None = None


class DatasetAssignRequest(BaseModel):
    dataset_id: str | None  # null = atamayı kaldır


class DatasetDto(BaseModel):
    id: str
    name: str
    description: str | None
    source: str
    notes: str | None
    case_count: int
    created_at: str
