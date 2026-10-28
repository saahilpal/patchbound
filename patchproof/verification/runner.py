"""Test runner coordinator executing tests inside sandboxes and parsing structured outputs."""

from pathlib import Path

from patchproof.core.sandbox import LocalTrustedSandbox, SandboxRunner
from patchproof.verification.parsers.base import ParsedReport, TestReportParser
from patchproof.verification.parsers.pytest_parser import PytestParser


class VerificationRunner:
    """Coordinates sandboxed test execution and report parsing."""

    def __init__(self, sandbox: SandboxRunner | None = None, parser: TestReportParser | None = None):
        self.sandbox = sandbox or LocalTrustedSandbox()
        self.parser = parser or PytestParser()

    def run_tests(
        self,
        workspace_path: Path,
        command: list[str],
        timeout_seconds: int = 120,
    ) -> ParsedReport:
        """Execute test command inside sandbox and return parsed structured report."""
        exec_res = self.sandbox.execute(
            workspace_path=workspace_path,
            command=command,
            timeout_seconds=timeout_seconds,
        )

        return self.parser.parse(
            stdout=exec_res.stdout,
            stderr=exec_res.stderr,
        )
