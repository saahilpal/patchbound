"""Synapse structural code graph provider adapter connecting PatchBound with Synapse."""

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from patchbound.context.base import ContextProvider, SymbolLocation
from patchbound.context.standard import StandardContextProvider


class SynapseContextProvider(ContextProvider):
    """Adapter for Synapse structural graph intelligence, layered over standard primitives."""

    name: str = "SynapseContextProvider"

    def __init__(
        self,
        workspace_path: Path,
        standard_provider: StandardContextProvider | None = None,
        db_path: Path | None = None,
    ):
        self.workspace_path = workspace_path.resolve()
        self.standard = standard_provider or StandardContextProvider(workspace_path)
        self.db_path = db_path or self._discover_synapse_db(self.workspace_path)
        self.cli_bin = shutil.which("synap")

    @staticmethod
    def _discover_synapse_db(workspace_path: Path) -> Path | None:
        """Search workspace and its parent directories for .synap/synap.db."""
        curr: Path | None = workspace_path.resolve()
        while curr and curr != curr.parent:
            candidate = curr / ".synap" / "synap.db"
            if candidate.is_file():
                return candidate
            curr = curr.parent
        return None

    def is_synapse_indexed(self) -> bool:
        """Check whether Synapse database index is present and readable."""
        return self.db_path is not None and self.db_path.is_file()

    def is_cli_available(self) -> bool:
        """Check whether the synap CLI is installed on PATH."""
        return self.cli_bin is not None

    def read_file(
        self, rel_path: str, start_line: int | None = None, end_line: int | None = None
    ) -> str:
        """Safely read lines from a file in the workspace."""
        return self.standard.read_file(rel_path, start_line, end_line)

    def grep_search(
        self, pattern: str, path_prefix: str | None = None
    ) -> list[tuple[str, int, str]]:
        """Search for literal or regex matches across repository."""
        return self.standard.grep_search(pattern, path_prefix)

    def find_symbol_definitions(self, symbol_name: str) -> list[SymbolLocation]:
        """Find definition sites of a given symbol via Synapse AST graph index."""
        if self.is_synapse_indexed() and self.db_path:
            try:
                conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
                cursor = conn.cursor()
                query = """
                    SELECT f.path, s.name, s.kind, s.start_line, s.end_line
                    FROM symbols s
                    JOIN files f ON s.file_id = f.file_id
                    WHERE s.name = ?
                """
                cursor.execute(query, (symbol_name,))
                rows = cursor.fetchall()
                conn.close()

                if rows:
                    results: list[SymbolLocation] = []
                    for row in rows:
                        results.append(
                            SymbolLocation(
                                file_path=str(row[0]),
                                symbol_name=str(row[1]),
                                kind=str(row[2]),
                                line_start=int(row[3]),
                                line_end=int(row[4]),
                            )
                        )
                    return results
            except (sqlite3.Error, OSError):
                pass

        # Fallback to standard provider
        return self.standard.find_symbol_definitions(symbol_name)

    def get_impacted_tests(self, modified_files: list[str]) -> list[str]:
        """Determine tests impacted by changes using Synapse reverse dependency call edges."""
        impacted: set[str] = set()

        if self.is_synapse_indexed() and self.db_path:
            try:
                conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
                cursor = conn.cursor()
                for mod_file in modified_files:
                    query = """
                        SELECT DISTINCT f_src.path
                        FROM symbols s_tgt
                        JOIN files f_tgt ON s_tgt.file_id = f_tgt.file_id
                        JOIN edges e ON e.target_symbol = s_tgt.symbol_id
                        JOIN symbols s_src ON e.source_symbol = s_src.symbol_id
                        JOIN files f_src ON s_src.file_id = f_src.file_id
                        WHERE f_tgt.path = ?
                          AND (f_src.path LIKE 'tests/%' OR f_src.path LIKE 'test%')
                    """
                    cursor.execute(query, (mod_file,))
                    for row in cursor.fetchall():
                        impacted.add(str(row[0]))
                conn.close()
            except (sqlite3.Error, OSError):
                pass

        # Combine with standard baseline test discovery
        standard_impacted = self.standard.get_impacted_tests(modified_files)
        impacted.update(standard_impacted)
        return sorted(impacted)

    def search_structural(self, query: str, max_tokens: int = 4000) -> str:
        """Run hybrid structural retrieval using synap CLI if available."""
        if self.is_cli_available() and self.cli_bin:
            try:
                cmd = [
                    self.cli_bin,
                    "search",
                    query,
                    "--path",
                    str(self.workspace_path),
                    "--max-tokens",
                    str(max_tokens),
                ]
                output = subprocess.check_output(cmd, text=True, timeout=30)
                return output
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass

        # Fallback to formatted grep context
        grep_results = self.grep_search(query)
        formatted_lines = [f"{fp}:{line}: {content}" for fp, line, content in grep_results[:20]]
        return "\n".join(formatted_lines)

    def get_status(self) -> dict[str, Any] | None:
        """Retrieve repository indexing status via synap status CLI."""
        if self.is_cli_available() and self.cli_bin:
            try:
                cmd = [self.cli_bin, "status", str(self.workspace_path), "--json"]
                output = subprocess.check_output(cmd, text=True, timeout=10)
                res: dict[str, Any] = json.loads(output)
                return res
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
                pass
        return None
