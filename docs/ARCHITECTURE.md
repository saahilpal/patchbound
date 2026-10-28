# PatchProof v1.1 Technical Architecture Specification

> **Version:** 1.1.0  
> **Status:** Approved / Active Specification  
> **Date:** 28 October 2026  
> **Classification:** Core System Architecture

---

## 1. Executive Summary & Design Philosophy

PatchProof v1.0 suffered from a common multi-agent anti-pattern: **a thin deterministic wrapper around seven loosely coordinated LLM agents**. Repairing software bugs is fundamentally a sequential, context-heavy, highly constrained problem. Every LLM-to-LLM handoff drops essential context, compounds prompt token costs, inflates latency, and introduces stochastic failure modes.

**PatchProof v1.1 inverts this paradigm:**
- **Thick Deterministic Trust Boundary:** All code execution, snapshotting, log parsing, test verification, diff synthesis, policy enforcement, and audit recording are handled by deterministic, non-LLM code.
- **Three Narrow LLM Roles:** Only three specific steps employ LLMs:
  1. **Investigator** (the *only* agent loop): Runs read-only tools and scratchpad experiments to formulate causal hypotheses supported by interventional evidence.
  2. **Fixer** (single structured LLM call): Emits a causal repair plan followed by exact anchored edits.
  3. **Adversarial Reviewer** (blind evaluation call): Evaluates the patch independently without seeing the fixer's narrative, checks anti-cheat constraints, and optionally generates probe tests.
- **Deterministic Oracle & Verifiable Gates:** An LLM *never* decides whether a fix succeeded. Verification status is strictly derived from trusted sandbox execution against pinned test suites.

```mermaid
flowchart TD
    subgraph Deterministic Spine
        S1["1. Snapshot & Reproduce\n(Disposable clone, F2P/P2P sets)"] --> S2["2. Parse & Triage\n(JUnit/Log parsers; LLM fallback)"]
        S2 --> S3{"3. Repairability Gate\n(Reproduced? In-scope?)"}
        S3 -- "Flaky / Unreproducible / Unsafe" --> S9B["Diagnosis-Only Report\n(Outcome: Clean Exit)"]
        S3 -- "Reproduced & Repairable" --> S4
    end

    subgraph LLM Agent Loop (Bounded)
        S4["4. Investigator\n(Read-only tools, Scratch experiments,\nClaim Ledger, Max Budget)"]
    end

    subgraph LLM Structured Call
        S4 --> S5["5. Fixer\n(Single structured call:\nPlan -> Anchored Edits)"]
    end

    subgraph Deterministic Spine
        S5 --> S6{"6. Patch Gate & Verify\n(Apply anchored edits -> Canonical diff\nPinned oracle, Levels V1-V3)"}
        S6 -- "Failed (Attempts < 2)" --> S4
        S6 -- "Failed (Attempts >= 2)" --> S9C["Unresolved Report"]
        S6 -- "Verified (V1/V2/V3)" --> S7
    end

    subgraph Adversarial Review
        S7["7. Anti-Cheat & Review\n(Code anti-cheat -> Blind Reviewer\nOptional probe execution)"]
        S7 -- "Blocked" --> S4
        S7 -- "Approved" --> S8
    end

    subgraph Human Boundary
        S8{"8. Human Approval Gate\n(LangGraph Interrupt\nBound to Patch Digest & Policy)"}
        S8 -- "Revise / Reject" --> S9C
        S8 -- "Approved" --> S9
    end

    subgraph Deterministic Spine
        S9["9. Export & Report\n(Re-verify digest, render from\nvalidated Claim Ledger)"]
    end
```

---

## 2. Nine-Stage Pipeline Specification

Every node in the PatchProof v1.1 execution graph belongs to one of three categories:
1. **Deterministic Code**
2. **Single Structured LLM Call**
3. **Bounded Agent Loop** (strictly limited to **one** throughout the entire graph: the Investigator).

| Stage | Kind | Responsibility | Failure/Exit Route |
| :--- | :--- | :--- | :--- |
| **1. Snapshot & Reproduce** | Deterministic | Create disposable local clone at base commit (hooks disabled). Execute failing command $N$ times. Baseline baseline test runs. Extract fail-to-pass (F2P) and pass-to-pass (P2P) sets. | Failure to reproduce routes to Stage 3 as `not_reproducible` or `flaky`. |
| **2. Parse & Triage** | Deterministic + Cheap LLM Fallback | High-performance AST/regex log parsers (pytest, jest, vitest, tsc, ruff, mypy) produce normalized failure signatures `(error_type, normalized_message, top_frame)`. Cheap LLM call used strictly if format is unrecognized. | Unparseable logs flag raw text signature. |
| **3. Repairability Gate** | Deterministic Policy | Evaluates failure against repairability policy. Filters out infrastructure errors, un-reproduced runs, flaky runs, environment mismatches, or out-of-scope/forbidden repositories. | Non-repairable runs terminate immediately with a **Diagnosis-Only Report** (counted as an operational success, not a failure). |
| **4. Investigator** | LLM Agent Loop (Only Loop) | Read-only investigation: query symbols, inspect git history, bisect commits, and execute interventional experiments in scratchpad workspaces. Populates the **Claim Ledger**. Bounded by strict step, token, and time budgets. | On budget exhaustion, emits best-effort diagnosis report and exits. |
| **5. Fixer** | Single Structured LLM Call | Takes top-ranked causal hypothesis and test targets. Emits a structured repair plan (with testable predictions) followed by exact anchored edits `(file_path, old_text, new_text)`. No unified diffs. | Schema violation triggers up to 1 bounded JSON repair attempt. |
| **6. Patch Gate & Verify** | Deterministic | Applies anchored edits in code; synthesizes canonical git diff and SHA-256 patch digest. Runs pre-verification policy checks. Restores original test files/configs by hash. Executes test runner in isolated sandbox. Evaluates verification levels (V1, V2, V3). | Verification failure sends failure signature delta back to Investigator (max 2 retries). |
| **7. Review** | Deterministic Checks + Blind LLM Call | Runs static anti-cheat checks (assert deletion, test alteration, skip injection). Blind Reviewer inspects diff and problem description *without* Fixer rationales to prevent confirmation bias. Optionally submits probe test cases. | Rejection sends actionable counterexample feedback to Investigator. |
| **8. Human Approval** | Human-in-the-Loop Gate (LangGraph Interrupt) | Graph execution pauses. Human operator inspects patch diff, verification level achieved (V1-V3), anti-cheat audit, and claim ledger. Approval is cryptographically bound to `(patch_digest, verification_record_hash, policy_version)`. | Human edit or rejection triggers re-verification or exits as `verified_rejected`. |
| **9. Export & Report** | Deterministic | Validates that patch digest matches approval signature. Generates canonical git patch artifact. Renders human- and machine-readable audit report directly from validated Claim Ledger. | Invariant violation aborts export. |

---

## 3. Trust Boundary & Sandboxing Architecture

### 3.1 Repository Isolation Invariants
PatchProof never operates directly on the user's working tree or active repository:
- **Disposable Clone (Not a Worktree):** `git worktree add` writes metadata into the original `.git` directory and shares hooks, config, and object locks. PatchProof clones the repository to an isolated, disposable directory using local hardlinks (`git clone --local --no-hardlinks` or clean ephemeral checkout).
- **Hooks Disabled:** All git operations run with `--no-verify` and `core.hooksPath=/dev/null` to guarantee hostile or broken hooks cannot trigger arbitrary code execution during inspection.
- **Repository Invariant:** The host repository's `HEAD`, branch references, index, and working-tree hash must be cryptographically identical before and after any PatchProof operation.

### 3.2 Two-Phase Sandbox Model
Code execution occurs within isolated sandbox tiers (Rootless Container / gVisor / bubblewrap / firecracker, with an explicit `trusted-local` fallback tier stamped on all artifacts):

1. **Prepare Phase (Dependency & Setup):**
   - Package installation routed exclusively through an allowlisted mirror or cached wheel/npm store.
   - Install scripts disabled by default (`npm ci --ignore-scripts`, pip wheels-only `--no-build-isolation`).
   - Caching keyed strictly by lockfile SHA-256 (`package-lock.json`, `poetry.lock`, `uv.lock`, `requirements.txt`).
   - No repository secrets or production tokens mounted.
2. **Execute Phase (Test & Experiment Execution):**
   - Network interface disabled (`--net=none`).
   - Root filesystem mounted read-only (`ro`).
   - Non-root user execution with dropped capabilities (`CAP_DROP_ALL`).
   - Strict resource limits enforced: cgroup CPU quota, memory limits (default 4GB), PID limits (max 256), and hard wall-clock timeouts.

### 3.3 Anchored Edits vs Model-Authored Diffs
LLMs frequently hallucinate line numbers, mangle indentation, and fail unified diff chunk headers (`@@ -L,N +L,N @@`).
PatchProof enforces **Anchored Edits**:
```json
{
  "edits": [
    {
      "file_path": "src/patchproof/core/runner.py",
      "old_text": "def execute(cmd):\n    return subprocess.run(cmd)",
      "new_text": "def execute(cmd):\n    return subprocess.run(cmd, check=True)"
    }
  ]
}
```
The deterministic spine locates the unique `old_text` match, executes the substitution, writes the file, and runs `git diff --no-prefix` to generate the authoritative canonical patch. The patch digest is computed as:
$$\text{PatchDigest} = \text{SHA-256}(\text{BaseTreeHash} \parallel \text{CanonicalDiffBytes})$$

---

## 4. Verification Engine & Pinned Test Oracles

### 4.1 Oracle Pinning
A known failure mode in automated program repair is test modification or config tampering (e.g., adding `@pytest.mark.xfail`, `@unittest.skip`, or softening test assertions in `conftest.py`).
- Before Stage 6 executes, the verification engine **restores all test files and testing configs** to their baseline commit hashes:
  - Python: `tests/**`, `conftest.py`, `pytest.ini`, `setup.cfg`, `pyproject.toml`, `tox.ini`
  - JavaScript/TypeScript: `**/*.test.*`, `**/*.spec.*`, `jest.config.*`, `tsconfig*.json`, `package.json`
- If an anchored edit touches any protected test file without explicit permission, Stage 6 hard-fails with a `POLICY_VIOLATION_PROTECTED_TEST_MUTATION` error.

### 4.2 Verification Levels & Quality Flags
Rather than treating verification as a naive boolean, PatchProof computes a structured verification tier:

```
[V1] Failing Tests Inverted: All fail-to-pass (F2P) tests execute and pass cleanly.
[V2] Regression-Free Core: V1 achieved + all directly impacted pass-to-pass (P2P) tests pass.
[V3] Full CI Clean: V2 achieved + entire repository test suite / CI command passes in full.
```

**Orthogonal Verification Flags:**
- `flake-checked`: The patched repro command ran $N \ge 3$ consecutive times with 0 failures.
- `pinned-tests`: Cryptographically verified that no test code or test config differed from base commit.
- `policy-clean`: Passed all static anti-cheat checks (no suppressions, diff size within bounds).

---

## 5. Causal Root-Cause Analysis & The Claim Ledger

### 5.1 Interventional Causality
A plausible LLM explanation is not evidence of causality. The Investigator must support hypotheses through **interventions**:
1. Formulate testable hypothesis: *"Bug is caused by missing null check in `parse_header()`."*
2. Execute scratch experiment: Revert suspect hunk, inject probe assertion, or run minimal reproducer.
3. Observe outcome: If the intervention turns the failure into the expected behavior, hypothesis transitions from `inferred` to `supported`.

### 5.2 The Claim Ledger
Every claim in the final diagnostic report is registered in a cryptographically audited Claim Ledger:
- `observed`: Direct observation from tool execution (e.g., test output, exit code).
- `derived`: Deterministically computed from observed data (e.g., git bisect result).
- `inferred`: LLM deduction supported by interventional experiment evidence.
- `assumed`: Unsupported conjecture or heuristic (flagged prominently for human review).

A deterministic Grounding Validator verifies that all cited line numbers, file paths, and quoted snippets actually exist at the specified git tree hash.

---

## 6. LangGraph State Machine Architecture

### 6.1 State Reducer & Storage Principles
- **State holds IDs and metadata only:** Large text blobs, source files, and test output logs are stored in a local content-addressed storage (CAS) keyed by SHA-256.
- **Append-only evidence:** Evidence items are immutable and deduplicated by content hash.
- **Interrupt Idempotency:** LangGraph's `interrupt()` resumes execution from the start of the node. The Human Approval stage is isolated in a pure, side-effect-free node. All preceding side-effect operations (cloning, building, running tests) are strictly keyed by `(investigation_id, attempt_index)`.

### 6.2 Process Status vs Outcome Result
Process status describes execution state; outcome represents final business delivery:

```
Process Status:
  INITIALIZING -> REPRODUCING -> TRIAGING -> INVESTIGATING ->
  FIXING -> VERIFYING -> REVIEWING -> AWAITING_APPROVAL -> EXPORTING -> TERMINATED

Terminal Outcomes:
  - verified_exported     (V1-V3 verified, approved by human, patch emitted)
  - verified_rejected     (V1-V3 verified, human declined to approve)
  - unverified_candidate  (Fix produced, but failed V1-V3 verification)
  - diagnosis_only        (Flaky, unreproducible, out-of-scope, or budget hit; full RCA report generated)
  - not_reproducible      (Failed to reproduce on base snapshot)
  - flaky                 (Non-deterministic test behavior detected on base snapshot)
  - blocked_by_policy     (Violated security, file scope, or anti-cheat constraints)
  - budget_exhausted      (Exceeded max steps, tokens, or cost limits)
  - error                 (Fatal infrastructure failure)
```

---

## 7. Anti-Cheat & Adversarial Review

Before any patch reaches human eyes, it passes two adversarial screens:
1. **Deterministic Anti-Cheat:**
   - Detects removed `assert`, `expect`, `should` statements.
   - Detects added test skip decorators (`@pytest.mark.skip`, `test.skip`, `it.only`).
   - Detects compiler/linter suppression comments (`@ts-ignore`, `noqa`, `eslint-disable`).
   - Checks that executed test count $\ge$ baseline test count and skipped count did not increase.
2. **Blind LLM Reviewer:**
   - Evaluates the canonical diff with a fresh context window (and ideally a distinct model family).
   - Generates an independent description of the diff's functional behavior.
   - Compares its independent interpretation against the Fixer's claimed intent to identify hidden regressions or semantic drift.
   - May submit executable probe test cases directly to the sandbox to falsify the repair.
