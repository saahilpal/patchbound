"""Synapse structural code graph provider adapter stub."""

from pathlib import Path
from patchproof.context.base import ContextProvider, SymbolLocation
from patchproof.context.standard import StandardContextProvider


class SynapseContextProvider(ContextProvider):
    """Adapter for Synapse structural graph intelligence, layered over standard primitives."""

    def __init__(self, workspace_path: Path, standard_provider: StandardContextProvider | None = None):
        self.workspace_path = workspace_path.resolve()
        self.standard = standard_provider or StandardContextProvider(workspace_path)

    def read_file(self, rel_path: str, start_line: int | None = None, end_line: int | None = None) -> str:
        return self.standard.read_file(rel_path, start_line, end_line)

    def grep_search(self, pattern: str, path_prefix: str | None = None) -> list[tuple[str, int, str]]:
        return self.standard.grep_search(pattern, path_prefix)

    def find_symbol_definitions(self, symbol_name: str) -> list[SymbolLocation]:
        # Synapse structural query replaces naive regex grep
        return self.standard.find_symbol_definitions(symbol_name)

    def get_impacted_tests(self, modified_files: list[str]) -> list[str]:
        # Synapse queries reverse dependency graph directly
        return self.standard.get_impacted_tests(modified_files)
