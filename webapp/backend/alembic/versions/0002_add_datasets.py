"""add datasets table and cases.dataset_id FK

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("source", sa.String(50), nullable=False, server_default="webapp"),
        sa.Column("notes", sa.Text),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.add_column(
        "cases",
        sa.Column("dataset_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cases_dataset_id",
        "cases", "datasets",
        ["dataset_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_cases_dataset_id", "cases", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_cases_dataset_id", table_name="cases")
    op.drop_constraint("fk_cases_dataset_id", "cases", type_="foreignkey")
    op.drop_column("cases", "dataset_id")
    op.drop_table("datasets")
