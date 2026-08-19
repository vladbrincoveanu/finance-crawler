from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_idea_ingestion_run_migration_adds_nullable_indexed_foreign_key(
    tmp_path, monkeypatch
):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = Config(
        str(Path(__file__).resolve().parents[2] / "alembic.ini")
    )
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    ideas_columns = {
        column["name"]: column for column in inspect(engine).get_columns("ideas")
    }
    staging_columns = {
        column["name"]: column
        for column in inspect(engine).get_columns("staging_holding_snapshots")
    }
    assert staging_columns["period"]["nullable"] is False
    assert ideas_columns["ingestion_run_id"]["nullable"] is True
    assert any(
        foreign_key["referred_table"] == "ingestion_runs"
        and foreign_key["constrained_columns"] == ["ingestion_run_id"]
        for foreign_key in inspect(engine).get_foreign_keys("ideas")
    )
    assert any(
        index["name"] == "ix_ideas_ingestion_run_id"
        and index["column_names"] == ["ingestion_run_id"]
        for index in inspect(engine).get_indexes("ideas")
    )
