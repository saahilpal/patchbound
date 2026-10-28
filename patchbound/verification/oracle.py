"""Pinned test oracle: restores test files and configs to base commit hash."""

import subprocess
from pathlib import Path

from patchbound.core.policy import PolicyEngine, PolicyViolation


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

    def __init__(self, workspace_path: Path, policy_engine: PolicyEngine | None = None):
        self.workspace_path = workspace_path.resolve()
        self.policy_engine = policy_engine or PolicyEngine()

    def restore_test_files_and_configs(self) -> None:
        """Restore all test directories and configuration files to HEAD."""
        try:
            # 1. Restore standard test directories
            subprocess.run(
                ["git", "checkout", "HEAD", "--", "tests/", "test/"],
                cwd=self.workspace_path,
                capture_output=True,
                check=False,
            )

            # 2. Check for any other modified files that match protected policy patterns
            diff_proc = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=False,
            )
            for line in diff_proc.stdout.splitlines():
                f = line.strip()
                if not f:
                    continue
                should_restore = False
                try:
                    self.policy_engine.check_file_path(f)
                except PolicyViolation:
                    should_restore = True

                if (
                    should_restore
                    or f in self.PROTECTED_CONFIG_PATTERNS
                    or Path(f).name in self.PROTECTED_CONFIG_PATTERNS
                ):
                    subprocess.run(
                        ["git", "checkout", "HEAD", "--", f],
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
            try:
                self.policy_engine.check_file_path(f)
            except PolicyViolation:
                raise PolicyViolation(
                    f"Oracle tampering detected! Test or protected file was modified by patch: {f}"
                ) from None
            if (
                f in self.PROTECTED_CONFIG_PATTERNS
                or Path(f).name in self.PROTECTED_CONFIG_PATTERNS
            ):
                raise PolicyViolation(
                    f"Oracle tampering detected! Protected config file was modified by patch: {f}"
                )
