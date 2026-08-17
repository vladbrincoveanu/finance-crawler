from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


EXPECTED_TABLES = {
    "companies",
    "ideas",
    "descriptions",
    "catalyst",
    "performance",
    "investors",
    "holdings",
    "comments",
    "photos",
    "users",
    "ingestion_runs",
    "source_documents",
    "source_fetches",
    "source_investors",
    "source_portfolio_managers",
    "source_securities",
    "source_holding_snapshots",
    "staging_holding_snapshots",
    "quarantine_records",
    "curated_investors",
    "portfolio_managers",
    "curated_investor_managers",
    "curated_companies",
    "curated_securities",
    "investor_aliases",
    "security_aliases",
    "identity_candidates",
    "identity_decisions",
    "curated_holding_snapshots",
    "curated_holding_events",
    "company_chapters",
    "evidence_chunks",
    "retrieval_runs",
    "retrieval_feedback",
}


def _alembic_config(database_url: str) -> Config:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_initial_migration_creates_legacy_and_identity_tables_then_downgrades(
    tmp_path, monkeypatch
):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
