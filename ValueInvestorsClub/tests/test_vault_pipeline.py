import multiprocessing
import os
import stat
import threading
import time

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


def test_unmarked_note_is_not_replaced(tmp_path):
    note = tmp_path / "vic" / "AAPL" / "2019-04-12__someuser__1234567.md"
    note.parent.mkdir(parents=True)
    manual = "---\nstatus: manual\n---\n\n# Keep this\n"
    note.write_text(manual)

    VaultProjectionPipeline(vault_root=tmp_path).process_item(_idea_item())

    assert note.read_text() == manual


def test_items_without_identity_are_skipped(tmp_path):
    item = _idea_item()
    item["idea_id"] = ""
    item["link"] = ""

    VaultProjectionPipeline(vault_root=tmp_path).process_item(item)

    assert list(tmp_path.rglob("*.md")) == []


def test_rendered_path_cannot_escape_vault_root(tmp_path, monkeypatch):
    import ValueInvestorsClub.ValueInvestorsClub.vault_pipeline as mod

    monkeypatch.setattr(mod.vic_note, "render", lambda _item: ("../escaped.md", "owned"))

    VaultProjectionPipeline(vault_root=tmp_path).process_item(_idea_item())

    assert not (tmp_path.parent / "escaped.md").exists()


def test_symlinked_parent_cannot_escape_vault_root(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "vic").symlink_to(outside, target_is_directory=True)

    VaultProjectionPipeline(vault_root=tmp_path).process_item(_idea_item())

    assert list(outside.rglob("*.md")) == []


def test_symlink_target_is_not_replaced(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    note = tmp_path / "vic" / "AAPL" / "2019-04-12__someuser__1234567.md"
    note.parent.mkdir(parents=True)
    note.symlink_to(outside)

    VaultProjectionPipeline(vault_root=tmp_path).process_item(_idea_item())

    assert note.is_symlink()
    assert outside.read_text() == "outside"


def test_fifo_target_is_rejected_without_blocking(tmp_path):
    note = tmp_path / "vic" / "AAPL" / "2019-04-12__someuser__1234567.md"
    note.parent.mkdir(parents=True)
    os.mkfifo(note)

    context = multiprocessing.get_context("fork")
    process = context.Process(
        target=_project_once,
        args=(str(tmp_path),),
    )
    process.start()
    process.join(timeout=2)
    if process.is_alive():
        process.terminate()
        process.join()
        raise AssertionError("projection blocked while inspecting a FIFO")

    assert stat.S_ISFIFO(note.stat(follow_symlinks=False).st_mode)


def test_existing_file_mode_is_preserved_on_atomic_rewrite(tmp_path):
    pipeline = VaultProjectionPipeline(vault_root=tmp_path)
    pipeline.process_item(_idea_item())
    note = tmp_path / "vic" / "AAPL" / "2019-04-12__someuser__1234567.md"
    os.chmod(note, 0o640)

    updated = _idea_item()
    updated["description"] = "Updated thesis."
    pipeline.process_item(updated)

    assert stat.S_IMODE(note.stat().st_mode) == 0o640
    assert "Updated thesis." in note.read_text()


def test_read_only_file_is_not_replaced(tmp_path):
    pipeline = VaultProjectionPipeline(vault_root=tmp_path)
    pipeline.process_item(_idea_item())
    note = tmp_path / "vic" / "AAPL" / "2019-04-12__someuser__1234567.md"
    original = note.read_text()
    original_inode = note.stat().st_ino
    os.chmod(note, 0o444)

    updated = _idea_item()
    updated["description"] = "Must not land."
    pipeline.process_item(updated)

    assert note.read_text() == original
    assert note.stat().st_ino == original_inode


def test_cooperating_writers_hold_one_projection_lock(tmp_path, monkeypatch):
    import ValueInvestorsClub.ValueInvestorsClub.vault_pipeline as mod

    active = 0
    maximum = 0
    state_lock = threading.Lock()

    def observe_merge(existing, document):
        nonlocal active, maximum
        with state_lock:
            active += 1
            maximum = max(maximum, active)
        time.sleep(0.1)
        with state_lock:
            active -= 1
        return document

    monkeypatch.setattr(mod.vic_note, "merge", observe_merge)
    pipelines = [VaultProjectionPipeline(vault_root=tmp_path) for _ in range(2)]
    threads = [
        threading.Thread(target=pipeline.process_item, args=(_idea_item(),))
        for pipeline in pipelines
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert maximum == 1


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


def _project_once(root):
    VaultProjectionPipeline(vault_root=root).process_item(_idea_item())
