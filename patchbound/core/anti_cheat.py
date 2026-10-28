"""Static anti-cheat checks to prevent superficial or gaming fixes."""

import ast
import re

from patchbound.core.policy import PolicyViolation


class AntiCheatChecker:
    """Verifies that patches do not strip assertions or bypass checks."""

    @staticmethod
    def check_assert_removal(canonical_diff: str) -> None:
        """Ensure no assertions were deleted without equivalent replacement."""
        deleted_lines = [
            line[1:].strip()
            for line in canonical_diff.splitlines()
            if line.startswith("-") and not line.startswith("---")
        ]

        for line in deleted_lines:
            # Check for Python assert
            if re.match(r"^assert\b", line):
                raise PolicyViolation(
                    f"Anti-cheat violation: deletion of assertion '{line}' is forbidden."
                )
            # Check for JS/TS expect/assert
            if re.search(r"\b(expect\(|assert\.)", line):
                raise PolicyViolation(
                    f"Anti-cheat violation: deletion of test assertion '{line}' is forbidden."
                )

    @staticmethod
    def check_python_ast_invariants(old_code: str, new_code: str) -> None:
        """Check AST differences to ensure no assert statements were stripped."""
        try:
            old_tree = ast.parse(old_code)
            new_tree = ast.parse(new_code)
        except SyntaxError:
            # If code is not valid Python (e.g. JS/TS), skip Python AST check
            return

        old_asserts = sum(1 for node in ast.walk(old_tree) if isinstance(node, ast.Assert))
        new_asserts = sum(1 for node in ast.walk(new_tree) if isinstance(node, ast.Assert))

        if new_asserts < old_asserts:
            raise PolicyViolation(
                f"Anti-cheat violation: code stripped {old_asserts - new_asserts} assert statement(s)."
            )

    @staticmethod
    def check_banned_constructs(canonical_diff: str) -> None:
        """Ensure no test bypass decorators or mocking cheats are added."""
        added_lines = [
            line[1:].strip()
            for line in canonical_diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        for line in added_lines:
            if re.search(r"\b(mock\.patch|unittest\.mock|pytest\.skip|pytest\.xfail)\b", line):
                raise PolicyViolation(
                    f"Anti-cheat violation: prohibited test bypass or mock added: '{line}'"
                )
            if re.search(r"\bsys\.exit\(0\)", line):
                raise PolicyViolation(
                    f"Anti-cheat violation: prohibited exit(0) bypass detected: '{line}'"
                )
