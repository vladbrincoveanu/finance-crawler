"""add company chapter retrieval schema

Revision ID: 20260816_0002
Revises: 20260816_0001
Create Date: 2026-08-17 00:02:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260816_0002"
down_revision: Union[str, None] = "20260816_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "company_chapters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("curated_company_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["curated_company_id"], ["curated_companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("curated_company_id", name="uq_company_chapters_company"),
    )
    op.create_table(
        "evidence_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("chapter_id", sa.String(length=36), nullable=False),
        sa.Column("section_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("security_id", sa.String(length=36), nullable=True),
        sa.Column("investor_id", sa.String(length=36), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("source_snapshot_ids", sa.JSON(), nullable=False),
        sa.Column("citation_urls", sa.JSON(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["company_chapters.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["curated_companies.id"]),
        sa.ForeignKeyConstraint(["security_id"], ["curated_securities.id"]),
        sa.ForeignKeyConstraint(["investor_id"], ["curated_investors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "retrieval_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("candidate_chunk_ids", sa.JSON(), nullable=False),
        sa.Column("rank_signals", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "retrieval_feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("retrieval_run_id", sa.String(length=36), nullable=False),
        sa.Column("usefulness_label", sa.String(length=32), nullable=True),
        sa.Column("citation_correctness_label", sa.String(length=32), nullable=True),
        sa.Column("retrieved_citation_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["retrieval_run_id"], ["retrieval_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("retrieval_feedback")
    op.drop_table("retrieval_runs")
    op.drop_table("evidence_chunks")
    op.drop_table("company_chapters")
