"""Abstract base interface and models for structured test output parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from patchproof.core.models import FailureSignature


@dataclass
class ParsedReport:
    """Summary of structured test suite execution."""

    total_executed: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    passed_test_ids: list[str] = field(default_factory=list)
    failed_signatures: list[FailureSignature] = field(default_factory=list)


class TestReportParser(ABC):
    """Abstract parser for test framework outputs (JUnit XML or JSON)."""

    @abstractmethod
    def parse(self, stdout: str, stderr: str, report_xml_or_json: str | None = None) -> ParsedReport:
        """Parse raw output or report artifact into a structured ParsedReport."""
        ...
