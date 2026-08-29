import importlib

import pytest


@pytest.fixture(autouse=True)
def restore_settings():
    """Reloading settings mutates a module other tests import. Put it back."""
    yield
    import ValueInvestorsClub.ValueInvestorsClub.settings as settings

    importlib.reload(settings)


def _pipelines(mode, monkeypatch):
    monkeypatch.setenv("PIPELINE_MODE", mode)
    import ValueInvestorsClub.ValueInvestorsClub.settings as settings

    importlib.reload(settings)
    return dict(settings.ITEM_PIPELINES)


def test_vault_pipeline_registered_at_400(monkeypatch):
    pipelines = _pipelines("sql,vault", monkeypatch)
    key = "ValueInvestorsClub.vault_pipeline.VaultProjectionPipeline"
    assert pipelines[key] == 400
    assert pipelines["ValueInvestorsClub.pipelines.SqlPipeline"] == 300


def test_vault_pipeline_absent_by_default(monkeypatch):
    pipelines = _pipelines("sql", monkeypatch)
    assert not any("vault" in key for key in pipelines)
