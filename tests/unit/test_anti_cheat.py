"""Unit tests for anti-cheat verification."""

import pytest
from patchproof.core.anti_cheat import AntiCheatChecker
from patchproof.core.policy import PolicyViolation


def test_anti_cheat_detects_assert_deletion():
    diff_with_deleted_assert = """
--- a/src/logic.py
+++ b/src/logic.py
@@ -10,3 +10,2 @@
-assert result == 42
 return result
"""
    with pytest.raises(PolicyViolation, match="deletion of assertion"):
        AntiCheatChecker.check_assert_removal(diff_with_deleted_assert)


def test_anti_cheat_python_ast():
    old_code = "def check(x):\n    assert x > 0\n    return x\n"
    new_code = "def check(x):\n    return x\n"

    with pytest.raises(PolicyViolation, match="stripped 1 assert statement"):
        AntiCheatChecker.check_python_ast_invariants(old_code, new_code)
