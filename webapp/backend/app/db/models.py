"""SQLAlchemy modelleri — plan Bölüm 2 (Veritabanı şeması) ile birebir uyumlu.

Enum benzeri alanlar bilerek native Postgres ENUM yerine `String` + `CheckConstraint`
olarak modellenmiştir: yeni bir değer eklemek (örn. yeni bir model mimarisi) sadece
CHECK constraint'i güncellemeyi gerektirir, Alembic'te ALTER TYPE manevrası gerekmez.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin','doctor')", name="ck_users_role"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = _uuid_pk()
    # Bölüm 3 (KVKK): gerçek hasta kimliği hiçbir zaman bu tabloda tutulmaz.
    pseudonym: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="webapp")
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded','validating','ready','failed')", name="ck_cases_status"
        ),
        CheckConstraint(
            "review_status IN ('unreviewed','in_review','reviewed','approved_for_training','excluded')",
            name="ck_cases_review_status",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    case_label: Mapped[str | None] = mapped_column(String(255))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    n_slices: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    deidentified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_report: Mapped[dict | None] = mapped_column(JSONB)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unreviewed")
    created_at: Mapped[datetime] = _created_at()

    slices: Mapped[list["CaseSlice"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseSlice(Base):
    __tablename__ = "case_slices"
    __table_args__ = (UniqueConstraint("case_id", "image_id", name="uq_case_slices_case_image"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True
    )
    image_id: Mapped[int] = mapped_column(Integer, nullable=False)
    z_index: Mapped[int] = mapped_column(Integer, nullable=False)
    dicom_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    # Lazy PNG cache (plan Bölüm 1): yükleme anında çoğu dilim için NULL kalır.
    png_storage_key: Mapped[str | None] = mapped_column(String(512))

    case: Mapped[Case] = relationship(back_populates="slices")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        CheckConstraint(
            "architecture IN ('yolo_det','yolo_seg','rfdetr','dfine','nnunet','mednext',"
            "'organ_bag_transformer','cls_timm')",
            name="ck_model_versions_architecture",
        ),
        CheckConstraint("run_mode IN ('default','comparison')", name="ck_model_versions_run_mode"),
        CheckConstraint(
            "status IN ('inactive','active','archived')", name="ck_model_versions_status"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    architecture: Mapped[str] = mapped_column(String(40), nullable=False)
    run_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="comparison")
    weights_storage_key: Mapped[str | None] = mapped_column(String(512))
    base_weights: Mapped[str | None] = mapped_column(String(255))
    train_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_jobs.id")
    )
    dataset_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_snapshots.id")
    )
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    fold: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="inactive")
    created_at: Mapped[datetime] = _created_at()

    outputs: Mapped[list["ModelOutput"]] = relationship(
        back_populates="model_version", cascade="all, delete-orphan"
    )


class ModelOutput(Base):
    """Bir model_version'ın ürettiği her çıktı türü için bir satır (plan Bölüm 2/4)."""

    __tablename__ = "model_outputs"
    __table_args__ = (
        CheckConstraint(
            "output_type IN ('bbox','mask','classification')", name="ck_model_outputs_type"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False, index=True
    )
    output_type: Mapped[str] = mapped_column(String(20), nullable=False)
    class_set: Mapped[dict | None] = mapped_column(JSONB)
    postprocess_config: Mapped[dict | None] = mapped_column(JSONB)

    model_version: Mapped[ModelVersion] = relationship(back_populates="outputs")


class DatasetSnapshot(Base):
    __tablename__ = "dataset_snapshots"
    __table_args__ = (
        CheckConstraint(
            "source IN ('webapp','bilgi_xlsx','mixed')", name="ck_dataset_snapshots_source"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    snapshot_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    manifest_storage_key: Mapped[str | None] = mapped_column(String(512))
    split_dir_storage_key: Mapped[str | None] = mapped_column(String(512))
    included_cases_count: Mapped[int | None] = mapped_column(Integer)
    included_annotations_count: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="webapp")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()


class AnnotationGroup(Base):
    """3D, vaka-seviyesi mantıksal bulgu — birden fazla ardışık dilimi bağlar (plan Bölüm 2)."""

    __tablename__ = "annotation_groups"
    __table_args__ = (
        CheckConstraint("class_type IN ('lesion','organ')", name="ck_annotation_groups_class_type"),
        CheckConstraint(
            "geometry_type IN ('bbox','polygon','mask')", name="ck_annotation_groups_geometry_type"
        ),
        CheckConstraint(
            "source IN ('prediction','manual','corrected')", name="ck_annotation_groups_source"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True
    )
    class_type: Mapped[str] = mapped_column(String(10), nullable=False)
    class_id: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry_type: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    model_output_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_outputs.id")
    )
    z_start: Mapped[int] = mapped_column(Integer, nullable=False)
    z_end: Mapped[int] = mapped_column(Integer, nullable=False)
    n_slices: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = _created_at()


class Annotation(Base):
    """2D, dilim-seviyesi geometri (plan Bölüm 2)."""

    __tablename__ = "annotations"
    __table_args__ = (
        CheckConstraint(
            "geometry_type IN ('bbox','polygon','mask')", name="ck_annotations_geometry_type"
        ),
        CheckConstraint(
            "source IN ('prediction','manual','corrected')", name="ck_annotations_source"
        ),
        CheckConstraint(
            "status IN ('active','deleted','superseded')", name="ck_annotations_status"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True
    )
    image_id: Mapped[int] = mapped_column(Integer, nullable=False)
    class_type: Mapped[str] = mapped_column(String(10), nullable=False, default="lesion")
    class_id: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry_type: Mapped[str] = mapped_column(String(10), nullable=False)
    geometry: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    derived_from_annotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotations.id")
    )
    model_output_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_outputs.id")
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotation_groups.id")
    )
    included_in_training_pool: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ClassificationPrediction(Base):
    __tablename__ = "classification_predictions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True
    )
    image_id: Mapped[int | None] = mapped_column(Integer)  # NULL => case-seviyesi tahmin
    model_output_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_outputs.id"), nullable=False
    )
    class_id: Mapped[int] = mapped_column(Integer, nullable=False)
    probability: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class AnnotationAuditLog(Base):
    __tablename__ = "annotation_audit_log"
    __table_args__ = (
        CheckConstraint(
            "action IN ('create','edit','delete','class_change','accept_prediction')",
            name="ck_annotation_audit_log_action",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    annotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("annotations.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    before_geometry: Mapped[dict | None] = mapped_column(JSONB)
    after_geometry: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _created_at()


class DataAccessLog(Base):
    """KVKK denetimi (plan Bölüm 3)."""

    __tablename__ = "data_access_log"
    __table_args__ = (
        CheckConstraint("action IN ('view','download','export')", name="ck_data_access_log_action"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"))
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id")
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class TrainingJob(Base):
    __tablename__ = "training_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('train_det','train_seg','train_coco_model','evaluate')",
            name="ck_training_jobs_job_type",
        ),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','cancelled')",
            name="ck_training_jobs_status",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    architecture: Mapped[str] = mapped_column(String(40), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    dataset_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_snapshots.id"), nullable=False
    )
    fold: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    queue_job_id: Mapped[str | None] = mapped_column(String(64))
    log_storage_key: Mapped[str | None] = mapped_column(String(512))
    result_model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id")
    )
    triggered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # Uzun süren işler için kontrol/izleme alanları (plan geri bildirimi, madde 3)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    progress_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    current_epoch: Mapped[int | None] = mapped_column(Integer)
    best_metric: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _created_at()


class InferenceBatch(Base):
    __tablename__ = "inference_batches"
    __table_args__ = (
        CheckConstraint(
            "batch_type IN ('default','comparison')", name="ck_inference_batches_batch_type"
        ),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','partial')",
            name="ck_inference_batches_status",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True
    )
    batch_type: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    created_at: Mapped[datetime] = _created_at()

    runs: Mapped[list["InferenceRun"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class InferenceRun(Base):
    __tablename__ = "inference_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed')", name="ck_inference_runs_status"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inference_batches.id"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False
    )
    conf_threshold: Mapped[float] = mapped_column(Numeric(4, 3), default=0.2, nullable=False)
    min_slice_run: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    queue_job_id: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()

    batch: Mapped[InferenceBatch] = relationship(back_populates="runs")
    model_version: Mapped["ModelVersion"] = relationship()

    @property
    def model_name(self) -> str:
        return self.model_version.name

    @property
    def architecture(self) -> str:
        return self.model_version.architecture
