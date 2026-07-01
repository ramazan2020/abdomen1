from __future__ import annotations

from pydantic import BaseModel


class CreateSnapshotRequest(BaseModel):
    snapshot_name: str
    description: str | None = None
    notes: str | None = None
    dataset_id: str | None = None


class SnapshotDto(BaseModel):
    id: str
    snapshot_name: str
    description: str | None
    notes: str | None
    included_cases_count: int | None
    included_annotations_count: int | None
    source: str
    manifest_storage_key: str | None
    created_at: str

    model_config = {"from_attributes": True}


class LaunchJobRequest(BaseModel):
    snapshot_id: str
    architecture: str
    params: dict = {}


class TrainingJobDto(BaseModel):
    id: str
    job_type: str
    architecture: str
    params: dict
    dataset_snapshot_id: str
    status: str
    progress_percent: float | None
    current_epoch: int | None
    best_metric: dict | None
    error_message: str | None
    cancel_requested: bool
    log_storage_key: str | None
    queue_job_id: str | None
    started_at: str | None
    finished_at: str | None
    heartbeat_at: str | None
    result_model_version_id: str | None
    created_at: str

    model_config = {"from_attributes": True}
