from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ModelOutputResponse(BaseModel):
    id: UUID
    output_type: str  # "bbox" | "mask" | "classification"
    class_set: dict[str, Any] | list[Any] | None
    postprocess_config: dict[str, Any] | None

    model_config = {"from_attributes": True}


class ModelVersionResponse(BaseModel):
    id: UUID
    name: str
    architecture: str
    run_mode: str
    base_weights: str | None
    metrics: dict[str, Any] | None
    fold: int | None
    status: str
    created_at: datetime
    outputs: list[ModelOutputResponse]

    model_config = {"from_attributes": True}


class ModelOutputCreateRequest(BaseModel):
    output_type: str
    class_set: dict[str, Any] | list[Any] | None = None
    postprocess_config: dict[str, Any] | None = None
