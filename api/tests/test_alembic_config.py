from pathlib import Path

from alembic.config import Config


def test_alembic_config_has_repo_script_location_and_default_url():
    config = Config("alembic.ini")

    assert Path(config.get_main_option("script_location")).name == "alembic"
    assert "postgresql+psycopg2" in config.get_main_option("sqlalchemy.url")
