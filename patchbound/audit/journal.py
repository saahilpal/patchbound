"""Hash-chained, append-only cryptographic audit journal."""

import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from patchbound.core.digest import compute_sha256


class JournalEntry(BaseModel):
    timestamp: float
    event_type: str
    payload: dict[str, Any]
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

    def record_event(self, event_type: str, payload: dict[str, Any]) -> JournalEntry:
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

    def verify_integrity(self) -> tuple[bool, str | None]:
        """Validate the cryptographic SHA-256 hash chain from genesis to tail.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self.journal_path.exists():
            return True, None

        lines = self.journal_path.read_text(encoding="utf-8").splitlines()
        expected_prev_hash = "0" * 64

        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                timestamp = record["timestamp"]
                event_type = record["event_type"]
                payload = record["payload"]
                prev_hash = record["prev_hash"]
                entry_hash = record["entry_hash"]

                if prev_hash != expected_prev_hash:
                    return (
                        False,
                        f"Chain break at record #{idx}: expected prev_hash '{expected_prev_hash[:16]}...', found '{prev_hash[:16]}...'",
                    )

                payload_str = json.dumps(payload, sort_keys=True)
                recomputed_hash = compute_sha256(
                    f"{timestamp}:{event_type}:{payload_str}:{prev_hash}"
                )
                if entry_hash != recomputed_hash:
                    return (
                        False,
                        f"Hash tampering detected at record #{idx}: expected '{recomputed_hash[:16]}...', found '{entry_hash[:16]}...'",
                    )

                expected_prev_hash = entry_hash
            except Exception as e:
                return False, f"Malformed journal record at #{idx}: {e}"

        return True, None
