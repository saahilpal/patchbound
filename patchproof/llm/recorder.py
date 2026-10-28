"""Golden file recording and playback harness for deterministic LLM testing."""

import json
from pathlib import Path
from patchproof.core.digest import compute_sha256


class LLMRecorder:
    """Enables record and playback mode for offline deterministic graph execution."""

    def __init__(self, fixture_dir: Path, mode: str = "playback"):
        self.fixture_dir = fixture_dir
        self.mode = mode  # "playback", "record", or "live"
        self.records: dict[str, str] = {}
        self._load_records()

    def _load_records(self) -> None:
        record_file = self.fixture_dir / "llm_recordings.json"
        if record_file.exists():
            self.records = json.loads(record_file.read_text(encoding="utf-8"))

    def _save_records(self) -> None:
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        record_file = self.fixture_dir / "llm_recordings.json"
        record_file.write_text(json.dumps(self.records, indent=2), encoding="utf-8")

    def query(self, prompt: str, model: str) -> str:
        key = compute_sha256(f"{model}:{prompt}")

        if self.mode == "playback":
            if key in self.records:
                return self.records[key]
            raise KeyError(f"No playback recording found for prompt hash: {key}")

        if self.mode == "record":
            # In recording mode, call actual provider and store
            response = f"[RECORDED RESPONSE FOR {model}]"
            self.records[key] = response
            self._save_records()
            return response

        # Live mode
        return "[LIVE RESPONSE]"
