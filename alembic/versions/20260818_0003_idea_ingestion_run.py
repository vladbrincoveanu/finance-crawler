"""link ideas to their ingestion run

Revision ID: 20260818_0003
Revises: 20260816_0002
Create Date: 2026-08-18 09:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260818_0003"
down_revision: Union[str, None] = "20260816_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ideas") as batch_op:
        batch_op.add_column(
            sa.Column("ingestion_run_id", sa.String(length=36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_ideas_ingestion_run_id",
            "ingestion_runs",
            ["ingestion_run_id"],
            ["id"],
        )
    op.create_index("ix_ideas_ingestion_run_id", "ideas", ["ingestion_run_id"])


def downgrade() -> None:
    op.drop_index("ix_ideas_ingestion_run_id", table_name="ideas")
    with op.batch_alter_table("ideas") as batch_op:
        batch_op.drop_constraint("fk_ideas_ingestion_run_id", type_="foreignkey")
        batch_op.drop_column("ingestion_run_id")
