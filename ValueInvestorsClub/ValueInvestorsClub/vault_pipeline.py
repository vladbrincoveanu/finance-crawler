"""Project accepted VIC ideas into the shared Markdown vault.

The pipeline is best-effort by design: a vault write must never fail a crawl
or block ingestion. Every projection exception is logged and the item is
returned unchanged.
"""

import logging
import os
from pathlib import Path

try:
    from ValueInvestorsClub import vic_note
    from ValueInvestorsClub.items import ValueinvestorsclubItem
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub import vic_note
    from ValueInvestorsClub.ValueInvestorsClub.items import ValueinvestorsclubItem


_logger = logging.getLogger(__name__)


class VaultProjectionPipeline:
    def __init__(self, vault_root=None):
        root = vault_root or os.getenv("VAULT_NOTES_DIR", "")
        self.vault_root = Path(root) if root else None
        self.enabled = self.vault_root is not None
        if not self.enabled:
            _logger.warning("VAULT_NOTES_DIR unset; vault projection disabled.")

    def process_item(self, item, spider=None):
        if not self.enabled:
            return item
        if not isinstance(item, ValueinvestorsclubItem):
            return item
        try:
            rel_path, document = vic_note.render(item)
            target = self.vault_root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            existing = target.read_text(encoding="utf-8") if target.exists() else None
            target.write_text(vic_note.merge(existing, document), encoding="utf-8")
        except Exception as exc:
            _logger.error("Vault projection failed for %s: %s", item.get("idea_id"), exc)
        return item
