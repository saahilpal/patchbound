"""Benchmark dataset fixtures, schemas, and loaders."""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class EvalFixture(BaseModel):
    """A single evaluation benchmark fixture."""

    fixture_id: str
    repo_url_or_path: str
    base_commit: str
    reproduce_command: list[str]
    held_out_command: list[str] = Field(
        default_factory=list, description="Private test command for FVR calculation"
    )
    expected_repairable: bool = True
    ground_truth_patch: str | None = None
    tags: list[str] = Field(default_factory=list)


class DatasetLoader:
    """Loads benchmark suites from JSONL files and formats."""

    @staticmethod
    def load_jsonl(file_path: Path) -> list[EvalFixture]:
        """Load benchmark fixtures from a standard JSONL file."""
        if not file_path.exists():
            return []

        fixtures = []
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    fixtures.append(EvalFixture.model_validate(data))
        return fixtures

    @staticmethod
    def save_jsonl(file_path: Path, fixtures: list[EvalFixture]) -> None:
        """Write fixtures to a JSONL file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            for fix in fixtures:
                f.write(fix.model_dump_json() + "\n")
