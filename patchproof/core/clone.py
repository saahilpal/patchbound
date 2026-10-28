"""Disposable repository cloning and host integrity invariant enforcement."""

import shutil
import subprocess
from pathlib import Path

from patchproof.core.digest import compute_sha256


class HostIntegrityViolation(Exception):
    """Raised when host repository state changes during PatchProof execution."""
    pass


class CloneManager:
    """Manages disposable clones with strict host invariant guarantees."""

    def __init__(self, host_repo_path: Path, scratch_base_dir: Path):
        self.host_repo_path = host_repo_path.resolve()
        self.scratch_base_dir = scratch_base_dir.resolve()
        self.pre_run_host_state: str | None = None

    def capture_host_state(self) -> str:
        """Capture cryptographic fingerprint of host repository state.

        Fingerprint covers HEAD commit, branch references, working tree index,
        and git status output.
        """
        try:
            head_rev = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=self.host_repo_path,
                text=True,
            ).strip()

            refs = subprocess.check_output(
                ["git", "show-ref"],
                cwd=self.host_repo_path,
                text=True,
            )

            status = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=self.host_repo_path,
                text=True,
            )

            payload = f"{head_rev}\n{refs}\n{status}"
            return compute_sha256(payload)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to inspect host git repository: {e}") from e

    def record_pre_state(self) -> None:
        """Record the host state prior to starting the run."""
        self.pre_run_host_state = self.capture_host_state()

    def verify_host_invariants(self) -> None:
        """Assert that host repository state is completely identical to pre-run state."""
        if not self.pre_run_host_state:
            raise RuntimeError("Pre-run host state was never captured.")

        current_state = self.capture_host_state()
        if current_state != self.pre_run_host_state:
            raise HostIntegrityViolation(
                f"Host repository changed during run! Pre: {self.pre_run_host_state}, Post: {current_state}"
            )

    def create_disposable_clone(self, investigation_id: str, attempt: int) -> Path:
        """Create an isolated, disposable clone with git hooks strictly disabled."""
        target_dir = self.scratch_base_dir / investigation_id / f"attempt-{attempt}"
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        # Clone using local hardlinks to save space, but disable hooks entirely
        cmd = [
            "git",
            "clone",
            "--local",
            "-c",
            "core.hooksPath=/dev/null",
            str(self.host_repo_path),
            str(target_dir),
        ]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return target_dir

    def cleanup_attempt(self, investigation_id: str, attempt: int) -> None:
        """Remove an attempt's scratch clone workspace."""
        target_dir = self.scratch_base_dir / investigation_id / f"attempt-{attempt}"
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
