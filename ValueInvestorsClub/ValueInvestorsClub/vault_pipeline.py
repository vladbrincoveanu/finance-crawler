"""Project accepted VIC ideas into the shared Markdown vault.

The pipeline is best-effort by design: a vault write must never fail a crawl
or block ingestion. Every projection exception is logged and the item is
returned unchanged.
"""

from __future__ import annotations

import contextlib
import fcntl
import logging
import os
import stat
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

try:
    from ValueInvestorsClub import vic_note
    from ValueInvestorsClub.items import ValueinvestorsclubItem
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub import vic_note
    from ValueInvestorsClub.ValueInvestorsClub.items import ValueinvestorsclubItem


_logger = logging.getLogger(__name__)
_LOCK_NAME = ".vic-vault.lock"
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW


class VaultProjectionPipeline:
    def __init__(self, vault_root: str | os.PathLike[str] | None = None) -> None:
        root = vault_root if vault_root is not None else os.getenv("VAULT_NOTES_DIR", "")
        self.vault_root = Path(root).expanduser() if root else None
        self.enabled = self.vault_root is not None
        if not self.enabled:
            _logger.warning("VAULT_NOTES_DIR unset; vault projection disabled.")

    def process_item(self, item: Any, spider: Any = None) -> Any:
        if not self.enabled:
            return item
        if not isinstance(item, ValueinvestorsclubItem):
            return item
        try:
            rendered = vic_note.render(item)
            if rendered is None:
                return item
            rel_path, document = rendered
            self._write(rel_path, document)
        except Exception:
            _logger.exception("Vault projection failed for %s", item.get("idea_id"))
        return item

    def _write(self, rel_path: str, document: str) -> None:
        parts = Path(rel_path).parts
        if not parts or Path(rel_path).is_absolute() or any(part in {"", ".", ".."} for part in parts):
            raise ValueError(f"invalid vault-relative path: {rel_path!r}")

        self.vault_root.mkdir(parents=True, exist_ok=True)
        root_fd = os.open(self.vault_root, _DIRECTORY_FLAGS)
        try:
            with _file_lock(root_fd):
                parent_fd = _open_directory_path(root_fd, parts[:-1])
                try:
                    _atomic_update(parent_fd, parts[-1], document)
                finally:
                    os.close(parent_fd)
        finally:
            os.close(root_fd)


@contextlib.contextmanager
def _file_lock(root_fd: int) -> Iterator[None]:
    try:
        lock_stat = os.stat(_LOCK_NAME, dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISREG(lock_stat.st_mode):
            raise ValueError("vault lock is not a regular file")
        lock_fd = os.open(_LOCK_NAME, os.O_RDWR | os.O_NOFOLLOW, dir_fd=root_fd)
    except FileNotFoundError:
        lock_fd = os.open(
            _LOCK_NAME,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=root_fd,
        )
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _open_directory_path(root_fd: int, parts: tuple[str, ...]) -> int:
    current_fd = os.dup(root_fd)
    try:
        for part in parts:
            try:
                os.mkdir(part, mode=0o755, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _read_regular_file(parent_fd: int, name: str) -> tuple[str | None, os.stat_result | None]:
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None, None
    if not stat.S_ISREG(entry.st_mode) or not entry.st_mode & 0o222:
        return None, entry

    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            return None, entry
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            fd = -1
            return handle.read(), entry
    finally:
        if fd != -1:
            os.close(fd)


def _target_is_unchanged_and_writable(
    parent_fd: int,
    name: str,
    original: os.stat_result | None,
) -> bool:
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return original is None
    if original is None:
        return False
    return (
        stat.S_ISREG(current.st_mode)
        and current.st_ino == original.st_ino
        and current.st_dev == original.st_dev
        and bool(current.st_mode & 0o222)
    )


def _atomic_update(parent_fd: int, name: str, document: str) -> None:
    existing, original = _read_regular_file(parent_fd, name)
    if original is not None and existing is None:
        return
    merged = vic_note.merge(existing, document)
    if merged == existing:
        return

    temp_name = f".{name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    temp_fd = -1
    try:
        temp_fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            stat.S_IMODE(original.st_mode) if original is not None else 0o644,
            dir_fd=parent_fd,
        )
        if original is not None:
            os.fchmod(temp_fd, stat.S_IMODE(original.st_mode))
        with os.fdopen(temp_fd, "w", encoding="utf-8") as handle:
            temp_fd = -1
            handle.write(merged)
            handle.flush()
            os.fsync(handle.fileno())

        if not _target_is_unchanged_and_writable(parent_fd, name, original):
            return
        os.replace(temp_name, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        with contextlib.suppress(OSError):
            os.fsync(parent_fd)
    finally:
        if temp_fd != -1:
            os.close(temp_fd)
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name, dir_fd=parent_fd)
