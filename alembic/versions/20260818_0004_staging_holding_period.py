"""store the source holding period on staging rows

Revision ID: 20260818_0004
Revises: 20260818_0003
Create Date: 2026-08-18 13:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260818_0004"
down_revision: Union[str, None] = "20260818_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("staging_holding_snapshots")}
    if "period" in columns:
        return

    with op.batch_alter_table("staging_holding_snapshots") as batch_op:
        batch_op.add_column(sa.Column("period", sa.Date(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE staging_holding_snapshots AS staging
            SET period = source.period
            FROM source_holding_snapshots AS source
            WHERE staging.source_snapshot_id = source.id
            """
        )
    )

    with op.batch_alter_table("staging_holding_snapshots") as batch_op:
        batch_op.alter_column(
            "period",
            existing_type=sa.Date(),
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("staging_holding_snapshots")}
    if "period" in columns:
        with op.batch_alter_table("staging_holding_snapshots") as batch_op:
            batch_op.drop_column("period")
