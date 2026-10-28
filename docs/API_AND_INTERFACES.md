# PatchProof v1.1 API, Contracts & Data Interfaces

> **Document:** Core Data Models, Contracts and Interfaces  
> **Status:** Active Standard

---

## 1. Core Data Models (`patchproof.core.models`)

### 1.1 Failure Signature
```python
from pydantic import BaseModel, Field

class StackFrame(BaseModel):
    file_path: str
    line_number: int
    function_name: str
    code_context: str | None = None

class FailureSignature(BaseModel):
    signature_id: str = Field(description="SHA-256 fingerprint of failure")
    test_id: str = Field(description="Fully-qualified test identifier")
    error_type: str = Field(description="Exception or failure type name")
    normalized_message: str = Field(description="Normalized failure message with ephemeral tokens stripped")
    top_frame: StackFrame | None = None
    raw_output_cas_ref: str = Field(description="CAS reference to full test log")
```

### 1.2 Anchored Edit
```python
class AnchoredEdit(BaseModel):
    file_path: str = Field(description="Repository-relative target file path")
    old_text: str = Field(description="Exact snippet to find and replace. Must match uniquely.")
    new_text: str = Field(description="Replacement text snippet")
    rationale: str | None = Field(default=None, description="Explanation of this specific edit")

class FixerOutput(BaseModel):
    repair_plan: str = Field(description="High-level causal repair strategy and expected outcome")
    target_tests: list[str] = Field(description="List of test IDs expected to be flipped or guarded")
    edits: list[AnchoredEdit] = Field(description="Ordered sequence of anchored edits")
```

### 1.3 Verification Record
```python
from enum import Enum

class VerificationLevel(str, Enum):
    V0_FAILED = "V0"    # F2P tests still failing
    V1_TARGET = "V1"    # F2P tests flipped to PASS
    V2_IMPACT = "V2"    # V1 + directly impacted tests pass
    V3_CI_CLEAN = "V3"  # Full CI suite passes cleanly

class VerificationFlags(BaseModel):
    flake_checked: bool = False
    pinned_tests: bool = False
    policy_clean: bool = False

class VerificationRecord(BaseModel):
    attempt: int
    level: VerificationLevel
    flags: VerificationFlags
    f2p_executed: list[str]
    f2p_passed: list[str]
    f2p_failed: list[str]
    p2p_regressed: list[str]
    total_executed: int
    total_skipped: int
    patch_digest: str
    verification_hash: str
```

---

## 2. Provider Contracts

### 2.1 Context Provider Interface (`patchproof.context.base`)
```python
from abc import ABC, abstractmethod

class SymbolLocation(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    symbol_name: str
    kind: str  # class, function, method, variable

class ContextProvider(ABC):
    @abstractmethod
    def read_file(self, rel_path: str, start_line: int | None = None, end_line: int | None = None) -> str:
        """Read file contents safely from isolated workspace."""
        ...

    @abstractmethod
    def grep_search(self, pattern: str, path_prefix: str | None = None) -> list[tuple[str, int, str]]:
        """Perform exact or regex search across codebase."""
        ...

    @abstractmethod
    def find_symbol_definitions(self, symbol_name: str) -> list[SymbolLocation]:
        """Locate definitions of classes, functions, or variables."""
        ...

    @abstractmethod
    def find_references(self, symbol_name: str) -> list[SymbolLocation]:
        """Locate usages/references of symbol across codebase."""
        ...

    @abstractmethod
    def get_impacted_tests(self, modified_files: list[str]) -> list[str]:
        """Query reverse dependency graph to identify tests impacted by changes."""
        ...
```

### 2.2 Test Runner Adapter Contract (`patchproof.verification.runner`)
```python
class TestRunResult(BaseModel):
    exit_code: int
    duration_seconds: float
    report_xml_or_json: str | None
    raw_stdout: str
    raw_stderr: str

class TestRunnerAdapter(ABC):
    @abstractmethod
    def get_reproduce_command(self, test_id: str | None = None) -> list[str]:
        """Produce typed command array to execute reproduction."""
        ...

    @abstractmethod
    def parse_report(self, raw_output: str, report_content: str | None) -> list[FailureSignature]:
        """Parse test failure signatures from structured test reports."""
        ...
```
