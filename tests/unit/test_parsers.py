"""Unit tests for test report parsers (pytest and Jest/Vitest)."""

from patchproof.verification.parsers.jest_parser import JestVitestParser
from patchproof.verification.parsers.pytest_parser import PytestParser


def test_jest_parser_from_stdout_json() -> None:
    """Verify that JestVitestParser can parse JSON emitted directly in stdout."""
    stdout_with_json = """
yarn run v1.22.19
$ jest --json
{
  "numTotalTests": 2,
  "numPassedTests": 1,
  "numFailedTests": 1,
  "testResults": [
    {
      "name": "/app/src/__tests__/auth.test.ts",
      "assertionResults": [
        {
          "title": "should hash password",
          "status": "passed"
        },
        {
          "title": "should reject invalid token",
          "status": "failed",
          "failureMessages": ["Error: Token expired at verifyToken (/app/src/auth.ts:42:15)"]
        }
      ]
    }
  ]
}
Done in 1.42s.
"""
    parser = JestVitestParser()
    report = parser.parse(stdout=stdout_with_json, stderr="", report_xml_or_json=None)

    assert report.total_executed == 2
    assert report.total_passed == 1
    assert report.total_failed == 1
    assert len(report.failed_signatures) == 1
    assert "should reject invalid token" in report.failed_signatures[0].test_id
    assert "Token expired" in report.failed_signatures[0].normalized_message


def test_pytest_parser_refines_error_and_message_from_stdout() -> None:
    """Verify PytestParser extracts real error type, message, and top frame from traceback."""
    stdout = """
============================= test session starts ==============================
rootdir: /app
collected 2 items

tests/test_calculator.py::test_add PASSED                               [ 50%]
tests/test_calculator.py::test_subtract FAILED                          [100%]

=================================== FAILURES ===================================
________________________________ test_subtract _________________________________

    def test_subtract():
>       assert subtract(5, 2) == 3
E       AssertionError: assert -1 == 3
E        +  where -1 = subtract(5, 2)

tests/test_calculator.py:12: AssertionError
=========================== short test summary info ============================
FAILED tests/test_calculator.py::test_subtract - AssertionError: assert -1 == 3
========================= 1 failed, 1 passed in 0.05s ==========================
"""
    parser = PytestParser()
    report = parser.parse(stdout=stdout, stderr="", report_xml_or_json=None)

    assert report.total_executed == 2
    assert report.total_passed == 1
    assert report.total_failed == 1
    assert len(report.failed_signatures) == 1

    sig = report.failed_signatures[0]
    assert sig.test_id == "tests/test_calculator.py::test_subtract"
    assert sig.error_type == "AssertionError"
    assert "assert -1 == 3" in sig.normalized_message
    assert sig.top_frame is not None
    assert sig.top_frame.file_path == "tests/test_calculator.py"
    assert sig.top_frame.line_number == 12
