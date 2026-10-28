"""Synthetic bug injection engine for generating private, uncontaminated repair benchmarks."""

import random
from pathlib import Path

from patchproof.eval.datasets import EvalFixture
from patchproof.verification.runner import VerificationRunner


class SyntheticMutator:
    """Injects subtle programmatic faults into clean repositories to evaluate repair accuracy."""

    MUTATION_RULES = [
        ("==", "!="),
        ("!=", "=="),
        (" > ", " >= "),
        (" < ", " <= "),
        (" + ", " - "),
        (" - ", " + "),
        (" and ", " or "),
        (" or ", " and "),
    ]

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path.resolve()

    def generate_candidate_mutations(self, target_rel_path: str) -> list[tuple[str, str]]:
        """Identify potential mutation sites in a source file."""
        target_file = self.workspace_path / target_rel_path
        if not target_file.is_file():
            return []

        content = target_file.read_text(encoding="utf-8")
        candidates = []

        for old_op, new_op in self.MUTATION_RULES:
            if old_op in content:
                # Find line containing operator
                for line in content.splitlines():
                    if old_op in line and not line.strip().startswith("#"):
                        mutated_line = line.replace(old_op, new_op, 1)
                        candidates.append((line, mutated_line))

        return candidates

    def inject_validated_bug(
        self,
        fixture_id: str,
        target_rel_path: str,
        test_command: list[str],
        runner: VerificationRunner | None = None,
    ) -> EvalFixture | None:
        """Inject a mutation, verify it flips test to FAIL, and emit an EvalFixture."""
        runner = runner or VerificationRunner()
        candidates = self.generate_candidate_mutations(target_rel_path)
        if not candidates:
            return None

        target_file = self.workspace_path / target_rel_path
        original_content = target_file.read_text(encoding="utf-8")

        # Shuffle candidates to get diverse injections
        random.shuffle(candidates)

        for old_line, new_line in candidates:
            # Apply mutation
            mutated_content = original_content.replace(old_line, new_line, 1)
            target_file.write_text(mutated_content, encoding="utf-8")

            # Check if this mutation causes a test failure
            report = runner.run_tests(self.workspace_path, test_command, timeout_seconds=60)
            if report.total_failed > 0:
                # Successfully injected a reproducible bug!
                import subprocess
                base_commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.workspace_path,
                    text=True,
                ).strip()

                # Restore clean code
                target_file.write_text(original_content, encoding="utf-8")

                return EvalFixture(
                    fixture_id=fixture_id,
                    repo_url_or_path=str(self.workspace_path),
                    base_commit=base_commit,
                    reproduce_command=test_command,
                    held_out_command=test_command,
                    expected_repairable=True,
                    tags=["synthetic", "private-repo", "operator-mutation"],
                )

        # Restore file if none succeeded
        target_file.write_text(original_content, encoding="utf-8")
        return None
