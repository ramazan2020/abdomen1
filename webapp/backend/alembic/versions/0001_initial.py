"""initial schema (plan Bölüm 2)

Revision ID: 0001
Revises:
Create Date: 2026-06-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin','doctor')", name="ck_users_role"),
    )

    op.create_table(
        "patients",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("pseudonym", sa.String(32), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "dataset_snapshots",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("manifest_storage_key", sa.String(512)),
        sa.Column("split_dir_storage_key", sa.String(512)),
        sa.Column("included_cases_count", sa.Integer),
        sa.Column("included_annotations_count", sa.Integer),
        sa.Column("source", sa.String(20), nullable=False, server_default="webapp"),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("source IN ('webapp','bilgi_xlsx','mixed')", name="ck_dataset_snapshots_source"),
    )

    op.create_table(
        "training_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(30), nullable=False),
        sa.Column("architecture", sa.String(40), nullable=False),
        sa.Column("params", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("dataset_snapshot_id", pg.UUID(as_uuid=True), sa.ForeignKey("dataset_snapshots.id"), nullable=False),
        sa.Column("fold", sa.Integer),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("queue_job_id", sa.String(64)),
        sa.Column("log_storage_key", sa.String(512)),
        sa.Column("result_model_version_id", pg.UUID(as_uuid=True)),
        sa.Column("triggered_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_requested", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("error_message", sa.Text),
        sa.Column("progress_percent", sa.Numeric(5, 2)),
        sa.Column("current_epoch", sa.Integer),
        sa.Column("best_metric", pg.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "job_type IN ('train_det','train_seg','train_coco_model','evaluate')",
            name="ck_training_jobs_job_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed','cancelled')",
            name="ck_training_jobs_status",
        ),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("architecture", sa.String(40), nullable=False),
        sa.Column("run_mode", sa.String(20), nullable=False, server_default="comparison"),
        sa.Column("weights_storage_key", sa.String(512)),
        sa.Column("base_weights", sa.String(255)),
        sa.Column("train_job_id", pg.UUID(as_uuid=True), sa.ForeignKey("training_jobs.id")),
        sa.Column("dataset_snapshot_id", pg.UUID(as_uuid=True), sa.ForeignKey("dataset_snapshots.id")),
        sa.Column("metrics", pg.JSONB),
        sa.Column("fold", sa.Integer),
        sa.Column("status", sa.String(20), nullable=False, server_default="inactive"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "architecture IN ('yolo_det','yolo_seg','rfdetr','dfine','nnunet','mednext',"
            "'organ_bag_transformer','cls_timm')",
            name="ck_model_versions_architecture",
        ),
        sa.CheckConstraint("run_mode IN ('default','comparison')", name="ck_model_versions_run_mode"),
        sa.CheckConstraint("status IN ('inactive','active','archived')", name="ck_model_versions_status"),
    )
    op.create_foreign_key(
        "fk_training_jobs_result_model_version",
        "training_jobs", "model_versions", ["result_model_version_id"], ["id"],
    )

    op.create_table(
        "model_outputs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_version_id", pg.UUID(as_uuid=True), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("output_type", sa.String(20), nullable=False),
        sa.Column("class_set", pg.JSONB),
        sa.Column("postprocess_config", pg.JSONB),
        sa.CheckConstraint("output_type IN ('bbox','mask','classification')", name="ck_model_outputs_type"),
    )
    op.create_index("ix_model_outputs_model_version_id", "model_outputs", ["model_version_id"])

    op.create_table(
        "cases",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", pg.UUID(as_uuid=True), sa.ForeignKey("patients.id")),
        sa.Column("case_label", sa.String(255)),
        sa.Column("uploaded_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("n_slices", sa.Integer),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("deidentified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("validation_report", pg.JSONB),
        sa.Column("review_status", sa.String(30), nullable=False, server_default="unreviewed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('uploaded','validating','ready','failed')", name="ck_cases_status"),
        sa.CheckConstraint(
            "review_status IN ('unreviewed','in_review','reviewed','approved_for_training','excluded')",
            name="ck_cases_review_status",
        ),
    )

    op.create_table(
        "case_slices",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", pg.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("image_id", sa.Integer, nullable=False),
        sa.Column("z_index", sa.Integer, nullable=False),
        sa.Column("dicom_storage_key", sa.String(512), nullable=False),
        sa.Column("png_storage_key", sa.String(512)),
        sa.UniqueConstraint("case_id", "image_id", name="uq_case_slices_case_image"),
    )
    op.create_index("ix_case_slices_case_id", "case_slices", ["case_id"])

    op.create_table(
        "annotation_groups",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", pg.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("class_type", sa.String(10), nullable=False),
        sa.Column("class_id", sa.Integer, nullable=False),
        sa.Column("geometry_type", sa.String(10), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("model_output_id", pg.UUID(as_uuid=True), sa.ForeignKey("model_outputs.id")),
        sa.Column("z_start", sa.Integer, nullable=False),
        sa.Column("z_end", sa.Integer, nullable=False),
        sa.Column("n_slices", sa.Integer, nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("class_type IN ('lesion','organ')", name="ck_annotation_groups_class_type"),
        sa.CheckConstraint("geometry_type IN ('bbox','polygon','mask')", name="ck_annotation_groups_geometry_type"),
        sa.CheckConstraint("source IN ('prediction','manual','corrected')", name="ck_annotation_groups_source"),
    )
    op.create_index("ix_annotation_groups_case_id", "annotation_groups", ["case_id"])

    op.create_table(
        "annotations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", pg.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("image_id", sa.Integer, nullable=False),
        sa.Column("class_type", sa.String(10), nullable=False, server_default="lesion"),
        sa.Column("class_id", sa.Integer, nullable=False),
        sa.Column("geometry_type", sa.String(10), nullable=False),
        sa.Column("geometry", pg.JSONB, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("derived_from_annotation_id", pg.UUID(as_uuid=True)),
        sa.Column("model_output_id", pg.UUID(as_uuid=True), sa.ForeignKey("model_outputs.id")),
        sa.Column("group_id", pg.UUID(as_uuid=True), sa.ForeignKey("annotation_groups.id")),
        sa.Column("included_in_training_pool", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("reviewed_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("geometry_type IN ('bbox','polygon','mask')", name="ck_annotations_geometry_type"),
        sa.CheckConstraint("source IN ('prediction','manual','corrected')", name="ck_annotations_source"),
        sa.CheckConstraint("status IN ('active','deleted','superseded')", name="ck_annotations_status"),
    )
    op.create_foreign_key(
        "fk_annotations_derived_from", "annotations", "annotations",
        ["derived_from_annotation_id"], ["id"],
    )
    op.create_index("ix_annotations_case_id", "annotations", ["case_id"])

    op.create_table(
        "classification_predictions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", pg.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("image_id", sa.Integer),
        sa.Column("model_output_id", pg.UUID(as_uuid=True), sa.ForeignKey("model_outputs.id"), nullable=False),
        sa.Column("class_id", sa.Integer, nullable=False),
        sa.Column("probability", sa.Numeric(6, 5), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_classification_predictions_case_id", "classification_predictions", ["case_id"])

    op.create_table(
        "annotation_audit_log",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("annotation_id", pg.UUID(as_uuid=True), sa.ForeignKey("annotations.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("actor_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("before_geometry", pg.JSONB),
        sa.Column("after_geometry", pg.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "action IN ('create','edit','delete','class_change','accept_prediction')",
            name="ck_annotation_audit_log_action",
        ),
    )
    op.create_index("ix_annotation_audit_log_annotation_id", "annotation_audit_log", ["annotation_id"])

    op.create_table(
        "data_access_log",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("case_id", pg.UUID(as_uuid=True), sa.ForeignKey("cases.id")),
        sa.Column("patient_id", pg.UUID(as_uuid=True), sa.ForeignKey("patients.id")),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("action IN ('view','download','export')", name="ck_data_access_log_action"),
    )
    op.create_index("ix_data_access_log_user_id", "data_access_log", ["user_id"])

    op.create_table(
        "inference_batches",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", pg.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("batch_type", sa.String(20), nullable=False),
        sa.Column("triggered_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("batch_type IN ('default','comparison')", name="ck_inference_batches_batch_type"),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed','partial')",
            name="ck_inference_batches_status",
        ),
    )
    op.create_index("ix_inference_batches_case_id", "inference_batches", ["case_id"])

    op.create_table(
        "inference_runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", pg.UUID(as_uuid=True), sa.ForeignKey("inference_batches.id"), nullable=False),
        sa.Column("case_id", pg.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("model_version_id", pg.UUID(as_uuid=True), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("conf_threshold", sa.Numeric(4, 3), nullable=False, server_default="0.2"),
        sa.Column("min_slice_run", sa.Integer, nullable=False, server_default="3"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("queue_job_id", sa.String(64)),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('queued','running','succeeded','failed')", name="ck_inference_runs_status"),
    )
    op.create_index("ix_inference_runs_batch_id", "inference_runs", ["batch_id"])


def downgrade() -> None:
    op.drop_table("inference_runs")
    op.drop_table("inference_batches")
    op.drop_table("data_access_log")
    op.drop_table("annotation_audit_log")
    op.drop_table("classification_predictions")
    op.drop_table("annotations")
    op.drop_table("annotation_groups")
    op.drop_table("case_slices")
    op.drop_table("cases")
    op.drop_table("model_outputs")
    op.drop_constraint("fk_training_jobs_result_model_version", "training_jobs", type_="foreignkey")
    op.drop_table("model_versions")
    op.drop_table("training_jobs")
    op.drop_table("dataset_snapshots")
    op.drop_table("patients")
    op.drop_table("users")
