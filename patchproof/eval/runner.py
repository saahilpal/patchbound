"""Evaluation benchmark runner executing paired-arm comparisons."""

import time
from pathlib import Path
from typing import Any

from patchproof.core.models import ProcessStatus
from patchproof.eval.datasets import EvalFixture
from patchproof.eval.metrics import EvalCalculator, EvalMetricsSummary
from patchproof.graph.workflow import compile_patchproof_graph
from patchproof.verification.runner import VerificationRunner


class BenchmarkRunner:
    """Orchestrates benchmark runs across test fixtures."""

    def __init__(self, arm_name: str = "patchproof-v1.1-spine"):
        self.arm_name = arm_name
        self.app = compile_patchproof_graph()
        self.verification_runner = VerificationRunner()

    def run_fixture(self, fixture: EvalFixture) -> dict[str, Any]:
        """Execute a single fixture through the pipeline and test held-out suite."""
        start_time = time.perf_counter()

        initial_state = {
            "investigation_id": fixture.fixture_id,
            "repo_path": fixture.repo_url_or_path,
            "reproduce_cmd": fixture.reproduce_command,
            "attempt": 0,
            "max_attempts": 2,
            "status": ProcessStatus.INITIALIZING,
        }

        # Run pipeline
        result = self.app.invoke(initial_state)
        duration = time.perf_counter() - start_time

        # Check held-out oracle if verified
        record = result.get("verification_record")
        level_str = record.level.value if record else "V0"
        held_out_failed = False

        if level_str in ("V1", "V2", "V3") and fixture.held_out_command:
            # Execute held-out suite against patched workspace
            workspace = Path(result.get("patched_workspace_path") or result.get("repo_path", "."))
            held_out_report = self.verification_runner.run_tests(
                workspace, fixture.held_out_command, timeout_seconds=60
            )
            if held_out_report.total_failed > 0:
                held_out_failed = True

        return {
            "fixture_id": fixture.fixture_id,
            "outcome": result.get("outcome"),
            "verification_level": level_str,
            "held_out_failed": held_out_failed,
            "expected_unrepairable": not fixture.expected_repairable,
            "duration_seconds": duration,
            "cost_usd": 0.05,  # Estimated or tracked cost
            "tokens": 1500,
            "patch_digest": result.get("patch_digest"),
        }

    def run_suite(self, fixtures: list[EvalFixture]) -> EvalMetricsSummary:
        """Run entire collection of fixtures and compute summary metrics."""
        results = []
        for fix in fixtures:
            res = self.run_fixture(fix)
            results.append(res)
        return EvalCalculator.compute_summary(self.arm_name, results)
