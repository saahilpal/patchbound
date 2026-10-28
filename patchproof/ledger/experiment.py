"""Interventional experiment runner in scratchpad workspaces."""

from enum import Enum
from pathlib import Path
from pydantic import BaseModel
from patchproof.core.models import AnchoredEdit
from patchproof.core.patcher import Patcher
from patchproof.core.sandbox import LocalTrustedSandbox, SandboxRunner


class ExperimentStatus(str, Enum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class ExperimentRecord(BaseModel):
    experiment_id: str
    hypothesis: str
    prediction: str
    status: ExperimentStatus
    details: str


class ExperimentRunner:
    """Executes interventional scratch experiments to establish causality."""

    def __init__(self, sandbox: SandboxRunner | None = None):
        self.sandbox = sandbox or LocalTrustedSandbox()

    def run_intervention(
        self,
        experiment_id: str,
        workspace_path: Path,
        hypothesis: str,
        prediction: str,
        probe_edits: list[AnchoredEdit],
        test_command: list[str],
    ) -> ExperimentRecord:
        """Apply temporary probe edits, execute test, and determine if hypothesis is supported."""
        patcher = Patcher(workspace_path)
        try:
            patcher.apply_edits(probe_edits)
            exec_res = self.sandbox.execute(workspace_path, test_command, timeout_seconds=60)

            # If the test succeeded under the intervention
            if exec_res.exit_code == 0:
                status = ExperimentStatus.SUPPORTED
                details = f"Intervention succeeded: test passed cleanly ({exec_res.duration_seconds:.2f}s)."
            else:
                status = ExperimentStatus.REFUTED
                details = f"Intervention failed to satisfy prediction: exit code {exec_res.exit_code}."
        except Exception as e:
            status = ExperimentStatus.INCONCLUSIVE
            details = f"Experiment error: {e}"

        return ExperimentRecord(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            prediction=prediction,
            status=status,
            details=details,
        )
