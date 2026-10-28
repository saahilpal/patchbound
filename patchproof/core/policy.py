"""Declarative policy engine for security and patch governance."""

import fnmatch
import re
from pathlib import Path
from pydantic import BaseModel, Field
import yaml


class ForbiddenPattern(BaseModel):
    id: str
    regex: str
    description: str


class PolicyScope(BaseModel):
    max_diff_bytes: int = 16384
    max_files_modified: int = 5
    protected_paths: list[str] = Field(
        default_factory=lambda: [
            ".git/**",
            ".github/**",
            "ci/**",
            "**/*test*/**",
            "**/conftest.py",
            "**/pytest.ini",
            "**/package.json",
            "**/tsconfig*.json",
        ]
    )


class PolicyConfig(BaseModel):
    version: str = "1.1.0"
    policy_id: str = "default-strict-v1.1"
    scope: PolicyScope = Field(default_factory=PolicyScope)
    forbidden_patterns: list[ForbiddenPattern] = Field(
        default_factory=lambda: [
            ForbiddenPattern(
                id="pytest_skip",
                regex=r"@pytest\.mark\.(skip|xfail)",
                description="Forbidden test skip marker added",
            ),
            ForbiddenPattern(
                id="ts_ignore",
                regex=r"@ts-(ignore|expect-error|nocheck)",
                description="TypeScript compiler check suppression",
            ),
            ForbiddenPattern(
                id="python_noqa",
                regex=r"#\s*noqa",
                description="Linter suppression comment",
            ),
        ]
    )


class PolicyViolation(Exception):
    """Raised when an operation or patch violates policy."""
    pass


class PolicyEngine:
    """Enforces policy invariants on files, diffs, and runner commands."""

    def __init__(self, policy: PolicyConfig | None = None):
        self.policy = policy or PolicyConfig()

    @classmethod
    def load_from_file(cls, path: Path) -> "PolicyEngine":
        """Load policy configuration from a YAML file."""
        if not path.exists():
            return cls(PolicyConfig())
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(PolicyConfig.model_validate(data))

    def check_file_path(self, rel_path: str) -> None:
        """Verify that a target file path is not protected."""
        path_obj = Path(rel_path)
        normalized = rel_path.lstrip("./")

        for pattern in self.policy.scope.protected_paths:
            # Check direct fnmatch
            if fnmatch.fnmatch(normalized, pattern):
                raise PolicyViolation(
                    f"Modification of protected path is prohibited: {rel_path} (matched '{pattern}')"
                )
            # Check without leading **/
            stripped_pattern = pattern.removeprefix("**/")
            if fnmatch.fnmatch(normalized, stripped_pattern) or fnmatch.fnmatch(path_obj.name, stripped_pattern):
                raise PolicyViolation(
                    f"Modification of protected path is prohibited: {rel_path} (matched '{pattern}')"
                )
            # Check directory parts (e.g. tests in tests/unit/foo.py)
            if any(fnmatch.fnmatch(part, stripped_pattern.rstrip("/*")) for part in path_obj.parts):
                raise PolicyViolation(
                    f"Modification of protected path is prohibited: {rel_path} (matched '{pattern}')"
                )
            # Check purepath match
            if path_obj.match(pattern):
                raise PolicyViolation(
                    f"Modification of protected path is prohibited: {rel_path} (matched '{pattern}')"
                )

    def check_diff(self, canonical_diff: str, modified_files: list[str]) -> None:
        """Validate diff size, modified file count, and forbidden patterns."""
        diff_bytes = len(canonical_diff.encode("utf-8"))
        if diff_bytes > self.policy.scope.max_diff_bytes:
            raise PolicyViolation(
                f"Diff size ({diff_bytes} bytes) exceeds maximum allowed ({self.policy.scope.max_diff_bytes} bytes)"
            )

        if len(modified_files) > self.policy.scope.max_files_modified:
            raise PolicyViolation(
                f"Modified files count ({len(modified_files)}) exceeds maximum allowed ({self.policy.scope.max_files_modified})"
            )

        # Check modified file paths
        for f in modified_files:
            self.check_file_path(f)

        # Check for forbidden patterns in added lines
        added_lines = [
            line[1:] for line in canonical_diff.splitlines() if line.startswith("+") and not line.startswith("+++")
        ]
        added_text = "\n".join(added_lines)

        for pat in self.policy.forbidden_patterns:
            if re.search(pat.regex, added_text):
                raise PolicyViolation(f"Policy violation detected ({pat.id}): {pat.description}")
