"""Deterministic test report parser for Jest and Vitest (JSON format)."""

import json
from patchproof.core.digest import compute_sha256
from patchproof.core.models import FailureSignature
from patchproof.verification.parsers.base import ParsedReport, TestReportParser


class JestVitestParser(TestReportParser):
    """Parses Jest/Vitest JSON test execution outputs."""

    def parse(self, stdout: str, stderr: str, report_xml_or_json: str | None = None) -> ParsedReport:
        report = ParsedReport()
        if not report_xml_or_json:
            return report

        try:
            data = json.loads(report_xml_or_json)
        except json.JSONDecodeError:
            return report

        test_results = data.get("testResults", [])
        for suite in test_results:
            suite_path = suite.get("name", "")
            for assertion in suite.get("assertionResults", []):
                title = assertion.get("title", "")
                test_id = f"{suite_path}::{title}"
                status = assertion.get("status", "")
                report.total_executed += 1

                if status == "passed":
                    report.total_passed += 1
                    report.passed_test_ids.append(test_id)
                elif status in ("failed", "timedOut"):
                    report.total_failed += 1
                    messages = assertion.get("failureMessages", ["Test failure"])
                    msg = messages[0] if messages else "Failure"
                    sig_id = compute_sha256(f"{test_id}:{msg[:100]}")
                    report.failed_signatures.append(
                        FailureSignature(
                            signature_id=sig_id,
                            test_id=test_id,
                            error_type="AssertionError",
                            normalized_message=msg[:200].strip(),
                        )
                    )
                elif status in ("pending", "skipped", "todo"):
                    report.total_skipped += 1

        return report
