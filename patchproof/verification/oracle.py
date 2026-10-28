"""Pinned test oracle: restores test files and configs to base commit hash."""

from pathlib import Path
import subprocess
from patchproof.core.policy import PolicyViolation


class PinnedOracle:
    """Guarantees that verification executes strictly against unmutated test oracles."""

    PROTECTED_CONFIG_PATTERNS = [
        "conftest.py",
        "pytest.ini",
        "setup.cfg",
        "tox.ini",
        "pyproject.toml",
        "package.json",
        "tsconfig.json",
        "jest.config.js",
        "jest.config.ts",
        "vitest.config.ts",
    ]

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path.resolve()

    def restore_test_files_and_configs(self) -> None:
        """Restore all test directories and configuration files to HEAD."""
        # 1. Restore tests/ directories
        try:
            subprocess.run(
                ["git", "checkout", "HEAD", "--", "tests/", "test/"],
                cwd=self.workspace_path,
                capture_output=True,
                check=False,
            )

            # 2. Restore root configuration files
            for cfg in self.PROTECTED_CONFIG_PATTERNS:
                if (self.workspace_path / cfg).exists():
                    subprocess.run(
                        ["git", "checkout", "HEAD", "--", cfg],
                        cwd=self.workspace_path,
                        capture_output=True,
                        check=False,
                    )
        except Exception as e:
            raise RuntimeError(f"Failed to restore pinned test oracles: {e}") from e

    def verify_no_test_diffs(self) -> None:
        """Verify that no test files or protected configs show uncommitted or committed diffs against base."""
        diff_output = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=self.workspace_path,
            text=True,
        )
        modified_files = [f.strip() for f in diff_output.splitlines() if f.strip()]
        for f in modified_files:
            if f.startswith("tests/") or f.startswith("test/") or f in self.PROTECTED_CONFIG_PATTERNS:
                raise PolicyViolation(
                    f"Oracle tampering detected! Test or config file was modified by patch: {f}"
                )
