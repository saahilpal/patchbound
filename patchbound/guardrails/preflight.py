"""Pre-flight guardrails ensuring environment and repository safety prior to execution."""

import shutil
import subprocess
from pathlib import Path

from patchbound.guardrails.base import GuardrailCheckResult, GuardrailSeverity, GuardrailViolation


class PreflightGuardrails:
    """Validates repository and environment prerequisites before starting a pipeline run."""

    @staticmethod
    def check_is_git_repository(repo_path: Path) -> GuardrailCheckResult:
        """Verify target path is a valid git repository."""
        is_git = (repo_path / ".git").is_dir() or (repo_path / ".git").is_file()
        if not is_git:
            try:
                subprocess.check_call(
                    ["git", "rev-parse", "--is-inside-work-tree"],
                    cwd=repo_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                is_git = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                is_git = False

        if not is_git:
            return GuardrailCheckResult(
                guardrail_id="PRE-01-GIT-REPO",
                name="Git Repository Validation",
                passed=False,
                severity=GuardrailSeverity.HARD_GATE,
                message=f"Target path '{repo_path}' is not a valid git repository.",
            )

        return GuardrailCheckResult(
            guardrail_id="PRE-01-GIT-REPO",
            name="Git Repository Validation",
            passed=True,
            severity=GuardrailSeverity.HARD_GATE,
            message="Valid git repository detected.",
        )

    @staticmethod
    def check_disk_space(target_dir: Path, min_mb: int = 500) -> GuardrailCheckResult:
        """Ensure sufficient disk space exists in scratch directory."""
        target_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(target_dir)
        free_mb = usage.free // (1024 * 1024)

        passed = free_mb >= min_mb
        return GuardrailCheckResult(
            guardrail_id="PRE-02-DISK-SPACE",
            name="Disk Space Allocation",
            passed=passed,
            severity=GuardrailSeverity.HARD_GATE,
            message=f"Available disk space: {free_mb} MB (minimum required: {min_mb} MB).",
            details={"free_mb": free_mb, "required_mb": min_mb},
        )

    @staticmethod
    def check_git_executable() -> GuardrailCheckResult:
        """Verify git executable is present on host system."""
        git_path = shutil.which("git")
        if not git_path:
            return GuardrailCheckResult(
                guardrail_id="PRE-03-TOOL-GIT",
                name="Git Toolchain Check",
                passed=False,
                severity=GuardrailSeverity.HARD_GATE,
                message="git executable not found in PATH.",
            )
        return GuardrailCheckResult(
            guardrail_id="PRE-03-TOOL-GIT",
            name="Git Toolchain Check",
            passed=True,
            severity=GuardrailSeverity.HARD_GATE,
            message=f"git executable found at {git_path}.",
        )

    @classmethod
    def run_all(cls, repo_path: Path, scratch_dir: Path) -> list[GuardrailCheckResult]:
        """Run all preflight guardrails and raise GuardrailViolation on hard failures."""
        results = [
            cls.check_is_git_repository(repo_path),
            cls.check_disk_space(scratch_dir),
            cls.check_git_executable(),
        ]
        for r in results:
            if not r.passed and r.severity == GuardrailSeverity.HARD_GATE:
                raise GuardrailViolation(r.guardrail_id, r.message, r.severity)
        return results
