"""Hash-chained, append-only cryptographic audit journal."""

import json
import time
from pathlib import Path
from pydantic import BaseModel
from patchproof.core.digest import compute_sha256


class JournalEntry(BaseModel):
    timestamp: float
    event_type: str
    payload: dict
    prev_hash: str
    entry_hash: str


class AuditJournal:
    """Manages an immutable, hash-chained journal for auditability and compliance."""

    def __init__(self, journal_path: Path):
        self.journal_path = journal_path
        self.last_hash = "0" * 64
        self._init_chain()

    def _init_chain(self) -> None:
        if self.journal_path.exists():
            lines = self.journal_path.read_text(encoding="utf-8").splitlines()
            if lines:
                last_record = json.loads(lines[-1])
                self.last_hash = last_record["entry_hash"]

    def record_event(self, event_type: str, payload: dict) -> JournalEntry:
        """Append an event to the hash chain."""
        now = time.time()
        payload_str = json.dumps(payload, sort_keys=True)
        raw = f"{now}:{event_type}:{payload_str}:{self.last_hash}"
        entry_hash = compute_sha256(raw)

        entry = JournalEntry(
            timestamp=now,
            event_type=event_type,
            payload=payload,
            prev_hash=self.last_hash,
            entry_hash=entry_hash,
        )

        self.last_hash = entry_hash
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

        return entry
