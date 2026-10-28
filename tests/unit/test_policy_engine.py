"""Unit tests for the declarative policy engine."""

import pytest
from patchproof.core.policy import PolicyEngine, PolicyViolation


def test_protected_path_rejection():
    engine = PolicyEngine()
    with pytest.raises(PolicyViolation, match="Modification of protected path is prohibited"):
        engine.check_file_path("tests/test_something.py")

    with pytest.raises(PolicyViolation, match="Modification of protected path is prohibited"):
        engine.check_file_path("conftest.py")

    # Regular source path should pass
    engine.check_file_path("src/core/parser.py")


def test_forbidden_pattern_detection():
    engine = PolicyEngine()
    diff_with_skip = """
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,4 @@
+@pytest.mark.skip(reason="cheating")
 def test_cheat():
     pass
"""
    with pytest.raises(PolicyViolation, match="pytest_skip"):
        engine.check_diff(diff_with_skip, ["foo.py"])


def test_clean_diff_passes():
    engine = PolicyEngine()
    clean_diff = """
--- a/src/math.py
+++ b/src/math.py
@@ -1,3 +1,3 @@
 def add(a, b):
-    return a - b
+    return a + b
"""
    engine.check_diff(clean_diff, ["src/math.py"])
