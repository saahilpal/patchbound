# Context Providers & Code Intelligence — PatchBound v1.1.0

**Document:** Context Provider Interface & Synapse Integration  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Architecture Overview](overview.md) • [State Machine](orchestration.md) • [Context Providers](context-providers.md) • [Verification Design](verification.md) • [Trade-Offs](tradeoffs.md)

---

## 1. The Context Retrieval Problem in Automated Repair

Traditional AI coding agents use vector embeddings (e.g. OpenAI ada-002, Chroma, Pinecone) to retrieve code context for a failing test. In real-world software engineering, vector similarity exhibits severe failure modes:
1. **Dynamic Dispatch & Interface Blindness:** Keyword search matches words, but cannot resolve which concrete class implements an abstract method.
2. **Reverse Call-Graph Blindness:** Vector search cannot find caller-callee chains (e.g. "which functions call `calculate_tax`?").
3. **Prompt Stuffing & Context Drift:** Vector retrievers return 10–20 superficially similar files, inflating prompt size and diluting model focus.

PatchBound resolves this by abstracting code intelligence behind a typed interface: **`ContextProvider`**.

---

## 2. The `ContextProvider` Protocol

All context providers implement the standard interface defined in [`patchbound/context/base.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/context/base.py):

```python
class ContextProvider(ABC):
    @abstractmethod
    def get_symbol_context(self, repo_path: Path, symbol_name: str) -> list[SymbolContext]:
        """Retrieve AST coordinates, docstrings, and signatures for a symbol."""
        pass

    @abstractmethod
    def get_caller_callee_graph(self, repo_path: Path, symbol_name: str) -> CallGraphResult:
        """Resolve incoming callers and outgoing callees for a symbol."""
        pass

    @abstractmethod
    def get_impacted_tests(self, repo_path: Path, modified_files: list[str]) -> list[str]:
        """Compute the minimal test closure exercising modified code."""
        pass
```

---

## 3. Supported Context Providers

### 3.1 Standard Context Provider (`StandardContextProvider`)
- **Backend:** Native Git commands, filesystem walk, Python `ast` parsing, and ripgrep/grep search.
- **Availability:** 100% universal across all environments. Requires zero external tooling or databases.
- **Symbol Resolution:** Parses files with Python's built-in `ast` module to locate function and class definitions.
- **Call-Graph Approximation:** Performs regex-based caller/callee search across files in the repository.

### 3.2 Synapse AST Structural Provider (`SynapseContextProvider`)
- **Backend:** [Synapse](https://github.com/saahilpal/synapse) (`synap-git`) via local SQLite database (`.synap/synap.db`) or FastMCP stdio interface.
- **Availability:** Activated when `synap` is installed and the repository has been indexed (`patchbound synapse index .`).
- **Capabilities:**
  - **Sub-millisecond Symbol Lookups:** Exact line ranges, signatures, and docstrings indexed directly in SQLite.
  - **Bidirectional Call Graph:** True static call-graph edges mapping callers and callees.
  - **Git-Aware Context:** Synthesizes unstaged working-tree changes and staged index changes into retrieved context.

---

## 4. Selection Modes & Failure Guarantees

PatchBound provides explicit command-line flags to control context selection:

```bash
# Default: Try Synapse; cleanly fall back to standard if unindexed or missing
patchbound repair /path/to/project --context auto

# Explicit Synapse: Require Synapse; fails fast with actionable error if missing
patchbound repair /path/to/project --context synapse

# Standard Mode: Force built-in standard context provider
patchbound repair /path/to/project --context standard
```

### Deterministic Failure Invariants:
1. When `--context auto` is set:
   - If Synapse is installed and `.synap/synap.db` exists, PatchBound uses `SynapseContextProvider`.
   - If Synapse is missing or unindexed, PatchBound logs an informational message and seamlessly falls back to `StandardContextProvider`.
2. When `--context synapse` is set:
   - If Synapse is missing or unindexed, PatchBound **fails closed immediately** with a descriptive diagnostic message instructing the user how to install and index the repository:
     ```
     Error: Synapse context mode was explicitly requested, but Synapse is unavailable or unindexed.
     Run 'patchbound synapse install' and 'patchbound synapse index <repo>' to resolve.
     ```
