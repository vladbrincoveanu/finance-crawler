from ValueInvestorsClub.ValueInvestorsClub.holding_items import HoldingItem
from ValueInvestorsClub.ValueInvestorsClub.items import ValueinvestorsclubItem
from ValueInvestorsClub.ValueInvestorsClub.vault_pipeline import VaultProjectionPipeline


def _idea_item():
    item = ValueinvestorsclubItem()
    item["ticker"] = "AAPL"
    item["companyName"] = "Apple Inc."
    item["date_iso"] = "2019-04-12"
    item["username"] = "someuser"
    item["idea_id"] = "1234567"
    item["link"] = "https://valueinvestorsclub.com/idea/APPLE/1234567"
    item["description"] = "Thesis."
    item["catalysts"] = ""
    item["comments"] = []
    item["isShort"] = False
    item["isContestWinner"] = False
    return item


def test_writes_note_to_expected_path(tmp_path):
    pipeline = VaultProjectionPipeline(vault_root=tmp_path)
    pipeline.process_item(_idea_item())
    note = tmp_path / "vic" / "AAPL" / "2019-04-12__someuser__1234567.md"
    assert note.exists()
    assert "# Apple Inc. ([[AAPL]])" in note.read_text()


def test_returns_the_item_unchanged(tmp_path):
    pipeline = VaultProjectionPipeline(vault_root=tmp_path)
    item = _idea_item()
    assert pipeline.process_item(item) is item


def test_ignores_holding_items(tmp_path):
    pipeline = VaultProjectionPipeline(vault_root=tmp_path)
    holding = HoldingItem()
    assert pipeline.process_item(holding) is holding
    assert list(tmp_path.rglob("*.md")) == []


def test_rewrite_preserves_hand_written_tail(tmp_path):
    pipeline = VaultProjectionPipeline(vault_root=tmp_path)
    pipeline.process_item(_idea_item())
    note = tmp_path / "vic" / "AAPL" / "2019-04-12__someuser__1234567.md"
    note.write_text(note.read_text() + "\n## My notes\n\nI bought this.\n")
    pipeline.process_item(_idea_item())
    assert "I bought this." in note.read_text()


def test_render_failure_does_not_break_the_crawl(tmp_path, monkeypatch):
    import ValueInvestorsClub.ValueInvestorsClub.vault_pipeline as mod

    def boom(_item):
        raise ValueError("render exploded")

    monkeypatch.setattr(mod.vic_note, "render", boom)
    pipeline = VaultProjectionPipeline(vault_root=tmp_path)
    item = _idea_item()
    assert pipeline.process_item(item) is item


def test_unwritable_vault_does_not_break_the_crawl(tmp_path):
    blocker = tmp_path / "blocked"
    blocker.write_text("i am a file, not a directory")
    pipeline = VaultProjectionPipeline(vault_root=blocker)
    item = _idea_item()
    assert pipeline.process_item(item) is item
