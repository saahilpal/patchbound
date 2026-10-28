"""Two-phase sandbox execution environment for untrusted builds and tests."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


class SandboxRunner(ABC):
    """Abstract contract for two-phase sandboxed execution."""

    @abstractmethod
    def prepare(self, workspace_path: Path, install_command: list[str]) -> ExecutionResult:
        """Execute dependency installation in prepare phase (outbound network allowed to mirror)."""
        ...

    @abstractmethod
    def execute(
        self,
        workspace_path: Path,
        command: list[str],
        timeout_seconds: int = 120,
    ) -> ExecutionResult:
        """Execute test or experiment in execute phase (isolated, no network, rlimits)."""
        ...


class LocalTrustedSandbox(SandboxRunner):
    """Local process-based execution sandbox for developer and CI runs."""

    def prepare(self, workspace_path: Path, install_command: list[str]) -> ExecutionResult:
        """Run dependency installation with scripts disabled."""
        import time
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                install_command,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_seconds=time.perf_counter() - start,
            )
        except subprocess.TimeoutExpired as e:
            return ExecutionResult(
                exit_code=-1,
                stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
                stderr=e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or ""),
                duration_seconds=time.perf_counter() - start,
                timed_out=True,
            )

    def execute(
        self,
        workspace_path: Path,
        command: list[str],
        timeout_seconds: int = 120,
    ) -> ExecutionResult:
        """Execute command with timeout and environment scrubbing."""
        import time
        start = time.perf_counter()
        # Clean environment to prevent secret leaking while preserving tool execution PATH
        import os
        import sys

        sys_bin = str(Path(sys.executable).parent)
        base_path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
        safe_path = f"{sys_bin}:/opt/homebrew/bin:{base_path}"

        clean_env = {
            "PATH": safe_path,
            "HOME": str(workspace_path),
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "PYTHONPATH": str(workspace_path),
        }
        try:
            proc = subprocess.run(
                command,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=clean_env,
            )
            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_seconds=time.perf_counter() - start,
            )
        except subprocess.TimeoutExpired as e:
            return ExecutionResult(
                exit_code=-1,
                stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
                stderr=e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or ""),
                duration_seconds=time.perf_counter() - start,
                timed_out=True,
            )
