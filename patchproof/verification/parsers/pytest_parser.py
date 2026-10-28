"""Deterministic test report parser for pytest (JUnit XML and stdout fallback)."""

import re
import xml.etree.ElementTree as ET

from patchproof.core.digest import compute_sha256
from patchproof.core.models import FailureSignature, StackFrame
from patchproof.verification.parsers.base import ParsedReport, TestReportParser


class PytestParser(TestReportParser):
    """Parses pytest test execution outputs."""

    def parse(self, stdout: str, stderr: str, report_xml_or_json: str | None = None) -> ParsedReport:
        if report_xml_or_json:
            try:
                return self._parse_junit_xml(report_xml_or_json)
            except ET.ParseError:
                pass

        return self._parse_stdout(stdout)

    def _parse_junit_xml(self, xml_content: str) -> ParsedReport:
        root = ET.fromstring(xml_content)
        report = ParsedReport()

        for testcase in root.iter("testcase"):
            classname = testcase.attrib.get("classname", "")
            name = testcase.attrib.get("name", "")
            test_id = f"{classname}::{name}"
            report.total_executed += 1

            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")

            if skipped is not None:
                report.total_skipped += 1
            elif failure is not None or error is not None:
                node = failure if failure is not None else error
                assert node is not None
                error_type = node.attrib.get("type", "AssertionError")
                message = node.attrib.get("message", "")
                text = node.text or ""

                report.total_failed += 1
                sig = self._create_signature(test_id, error_type, message, text)
                report.failed_signatures.append(sig)
            else:
                report.total_passed += 1
                report.passed_test_ids.append(test_id)

        return report

    def _parse_stdout(self, stdout: str) -> ParsedReport:
        report = ParsedReport()
        pass_ids: list[str] = []
        fail_ids: list[str] = []

        # 1. Match pytest verbose style:
        # tests/test_foo.py::test_bar PASSED
        # PASSED tests/test_foo.py::test_bar
        for m in re.finditer(r"(?:PASSED\s+([^\s]+::[^\s]+)|([^\s]+::[^\s]+)\s+PASSED)", stdout):
            test_id = m.group(1) or m.group(2)
            if test_id:
                pass_ids.append(test_id)

        # 2. Match pytest fail style:
        # tests/test_foo.py::test_bar FAILED
        # FAILED tests/test_foo.py::test_bar
        for m in re.finditer(r"(?:FAILED\s+([^\s]+::[^\s]+)|([^\s]+::[^\s]+)\s+FAILED)", stdout):
            test_id = m.group(1) or m.group(2)
            if test_id:
                fail_ids.append(test_id)

        # 3. Match generic PASS / FAIL lines (e.g. runner scripts or jest stdout)
        if not pass_ids and not fail_ids:
            for m in re.finditer(r"^PASS\s+([^\s:]+)", stdout, re.MULTILINE):
                pass_ids.append(m.group(1))
            for m in re.finditer(r"^FAIL\s+([^\s:]+)", stdout, re.MULTILINE):
                fail_ids.append(m.group(1))

        # 4. Fallback for non-verbose summary format (e.g., "1 passed in 0.05s")
        if not pass_ids and not fail_ids:
            summary_pass = re.search(r"(\d+)\s+passed", stdout)
            summary_fail = re.search(r"(\d+)\s+failed", stdout)
            if summary_pass:
                report.total_passed = int(summary_pass.group(1))
            if summary_fail:
                report.total_failed = int(summary_fail.group(1))
                sig = self._create_signature("test_suite", "TestFailure", "Failed during test run", stdout)
                report.failed_signatures.append(sig)

        report.passed_test_ids = sorted(set(pass_ids))
        if pass_ids:
            report.total_passed = len(report.passed_test_ids)

        for test_id in sorted(set(fail_ids)):
            report.total_failed += 1
            sig = self._create_signature(test_id, "TestFailure", "Failed during test run", stdout)
            report.failed_signatures.append(sig)

        report.total_executed = report.total_passed + report.total_failed
        return report

    def _create_signature(self, test_id: str, error_type: str, message: str, full_trace: str) -> FailureSignature:
        norm_message = re.sub(r"0x[0-9a-fA-F]+", "0x...", message).strip()
        top_frame = None

        # Extract top stack frame if available (File "...", line X, in Y)
        frames = re.findall(r'File "([^"]+)", line (\d+), in (\w+)', full_trace)
        if frames:
            last_file, last_line, last_fn = frames[-1]
            top_frame = StackFrame(
                file_path=last_file,
                line_number=int(last_line),
                function_name=last_fn,
            )

        sig_id = compute_sha256(f"{test_id}:{error_type}:{norm_message}")
        return FailureSignature(
            signature_id=sig_id,
            test_id=test_id,
            error_type=error_type,
            normalized_message=norm_message,
            top_frame=top_frame,
        )
