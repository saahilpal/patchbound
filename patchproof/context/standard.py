"""Standard context provider using deterministic primitives (grep, AST, git log)."""

import subprocess
from pathlib import Path

from patchproof.context.base import ContextProvider, SymbolLocation


class StandardContextProvider(ContextProvider):
    """Baseline context provider using standard Unix and git tools."""

    name: str = "StandardContextProvider"

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path.resolve()

    def read_file(self, rel_path: str, start_line: int | None = None, end_line: int | None = None) -> str:
        target = self.workspace_path / rel_path
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {rel_path}")

        lines = target.read_text(encoding="utf-8").splitlines()
        start = (start_line - 1) if start_line else 0
        end = end_line if end_line else len(lines)
        return "\n".join(lines[start:end])

    def grep_search(self, pattern: str, path_prefix: str | None = None) -> list[tuple[str, int, str]]:
        cmd = ["grep", "-rnE", pattern]
        if path_prefix:
            cmd.append(path_prefix)
        else:
            cmd.append(".")

        try:
            output = subprocess.check_output(cmd, cwd=self.workspace_path, text=True)
        except subprocess.CalledProcessError:
            return []

        results = []
        for line in output.splitlines():
            parts = line.split(":", 2)
            if len(parts) == 3:
                try:
                    results.append((parts[0], int(parts[1]), parts[2]))
                except ValueError:
                    continue
        return results

    def find_symbol_definitions(self, symbol_name: str) -> list[SymbolLocation]:
        # Baseline AST or regex search
        matches = self.grep_search(f"def {symbol_name}|class {symbol_name}")
        locs = []
        for file_path, line_no, content in matches:
            kind = "class" if "class" in content else "function"
            locs.append(
                SymbolLocation(
                    file_path=file_path,
                    line_start=line_no,
                    line_end=line_no,
                    symbol_name=symbol_name,
                    kind=kind,
                )
            )
        return locs

    def get_impacted_tests(self, modified_files: list[str]) -> list[str]:
        # Grep for test files that import or reference modified modules
        impacted = set()
        for f in modified_files:
            stem = Path(f).stem
            matches = self.grep_search(stem, path_prefix="tests")
            for test_file, _, _ in matches:
                impacted.add(test_file)
        return list(impacted)
