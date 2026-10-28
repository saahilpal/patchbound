"""Context provider contracts and interface definitions."""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class SymbolLocation(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    symbol_name: str
    kind: str  # class, function, method, variable


class ContextProvider(ABC):
    """Abstract interface for context retrieval engines (Standard vs Synapse)."""

    name: str = "ContextProvider"

    @abstractmethod
    def read_file(
        self, rel_path: str, start_line: int | None = None, end_line: int | None = None
    ) -> str:
        """Safely read lines from a file in the workspace."""
        ...

    @abstractmethod
    def grep_search(
        self, pattern: str, path_prefix: str | None = None
    ) -> list[tuple[str, int, str]]:
        """Search for literal or regex matches across repository."""
        ...

    @abstractmethod
    def find_symbol_definitions(self, symbol_name: str) -> list[SymbolLocation]:
        """Find definition sites of a given symbol."""
        ...

    @abstractmethod
    def get_impacted_tests(self, modified_files: list[str]) -> list[str]:
        """Determine tests impacted by changes to modified files."""
        ...
