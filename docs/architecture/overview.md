# Architecture Overview — PatchBound v1.1.0

**Document:** Architecture Overview & System Topology  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Architecture Index](overview.md) • [State Machine](orchestration.md) • [Context Providers](context-providers.md) • [Verification Design](verification.md) • [Trade-Offs](tradeoffs.md)

---

## 1. High-Level System Architecture

PatchBound is architected around a foundational design rule:

> **"The LLM is an untrusted, probabilistic leaf node. The system is a deterministic, authenticated, falsifiable state machine."**

Every state transition, test reproduction, code mutation, and verification assertion is orchestrated through a deterministic spine built on LangGraph. The host repository is insulated from modification until candidate edits are verified in throwaway clones and approved by a human.

### System Component Topology

```mermaid
flowchart TD
    subgraph CLI ["CLI & Control Plane"]
        CLI_CMD["CLI Command<br/>(patchbound repair / gh solve)"]
        INPUT_VAL["Input & Path Validation<br/>(policy.yaml, bounds check)"]
        CLI_CMD --> INPUT_VAL
    end

    subgraph StateMachine ["LangGraph Orchestration Spine"]
        direction TB
        INPUT_VAL --> S1["1. snapshot_reproduce<br/>(Ephemeral Sandbox A)"]
        S1 --> S2["2. parse_triage<br/>(JUnit / Pytest parser)"]
        S2 --> S3{"3. repairability_gate<br/>(Reproducible?)"}
        
        S3 -- "No (Flaky/Clean)" --> OUT_NOT_REP["Outcome: NOT_REPRODUCIBLE<br/>(0 tokens spent)"]
        S3 -- "Yes (Fails)" --> S4["4. investigator<br/>(AST & Context Assembly)"]
        
        S4 --> S5["5. fixer<br/>(Anchored Edit Synthesis in Sandbox B)"]
        S5 --> S6["6. patch_verify<br/>(Pinned Oracle, Anti-Cheat, V1-V3)"]
        
        S6 --> S7{"Verification Level?"}
        S7 -- "V0_FAILED / Regression<br/>(attempt < max)" --> S4
        S7 -- "Budget Exhausted" --> S9["9. export_report<br/>(Outcome: BUDGET_EXHAUSTED)"]
        S7 -- "V1+ Verified" --> S8["7. review<br/>(Adversarial Invariant Check)"]
        
        S8 --> S8B{"8. human_approval<br/>(Approved?)"}
        S8B -- "Yes" --> S9_OK["9. export_report<br/>(Outcome: VERIFIED_EXPORTED)"]
        S8B -- "No" --> S9_NO["9. export_report<br/>(Outcome: REJECTED_BY_USER)"]
    end

    subgraph ContextSubsystem ["Context Providers"]
        S4 -.-> CTX_SELECT{"Context Provider Selection<br/>(--context auto|synapse|standard)"}
        CTX_SELECT --> STD_CTX["Standard Context<br/>(Git diff, modified files, grep)"]
        CTX_SELECT --> SYN_CTX["Synapse AST Engine (Optional)<br/>(SQLite call graph, bidirectional edges)"]
    end

    subgraph OutputGate ["Output & Governance Boundary"]
        S9_OK --> DIFF_OUT["Export Verified .diff Patch"]
        S9_OK --> JOURNAL["Append to SHA-256 Claim Journal"]
        S9_OK --> APPLY_GATE{"--apply Flag Passed<br/>AND Human Approved?"}
        APPLY_GATE -- "Yes" --> HOST_APPLY["git apply -p0 to Host Repository"]
        APPLY_GATE -- "No" --> HOST_SAFE["Host Unmodified (Safe)"]
    end

    classDef cli fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef spine fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef context fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef gate fill:#fff3e0,stroke:#f57c00,stroke-width:2px;

    class CLI_CMD,INPUT_VAL cli;
    class S1,S2,S3,S4,S5,S6,S7,S8,S8B,S9,S9_OK,S9_NO,OUT_NOT_REP spine;
    class CTX_SELECT,STD_CTX,SYN_CTX context;
    class DIFF_OUT,JOURNAL,APPLY_GATE,HOST_APPLY,HOST_SAFE gate;
```

---

## 2. Core Architectural Pillars

### 2.1 The Thick Deterministic Spine
All critical path decisions—workspace sandboxing, test reproduction, regression checking, oracle pinning, and policy compliance—are executed by deterministic Python modules. The probabilistic AI model (invoked only in Stage 5 for repair synthesis or Stage 7 for secondary review) has no direct access to filesystem operations, terminal execution, or network egress outside controlled sandboxes.

### 2.2 Pinned Test Oracles & Anti-Cheat Invariants
AI agents frequently cheat by modifying test assertions to fake a passing build. PatchBound enforces two non-bypassable constraints:
1. **Physical Restoration:** Before running post-patch verification in Sandbox B, the test files are restored from the initial Git commit:
   ```bash
   git checkout -- tests/ **/test_*.py conftest.py
   ```
2. **AST Anti-Cheat Analysis:** Modified files are inspected using Python's Abstract Syntax Tree parser. Commits introducing `@pytest.mark.skip`, `@unittest.skip`, `@ts-ignore`, removed assertion statements, or injected mocks are rejected with a policy violation.

### 2.3 Ephemeral Hardlink Sandbox Isolation
Explorations and candidate patches are isolated in `/tmp/patchbound-workspaces/<investigation_id>/attempt-<n>` using Git hardlinks (`git clone --local --no-checkout` or hardlink file trees). This provides:
- **Instantaneous cloning:** Sub-100ms clone creation regardless of repository size.
- **Host repository immutability:** The target repository remains completely untouched during investigation and iterative repair attempts.
- **Hook suppression:** All Git hooks are neutralized (`core.hooksPath=/dev/null`) to prevent arbitrary script execution.

### 2.4 Epistemological Claim Ledger
Every assertion made during an investigation is recorded in an append-only, SHA-256 hash-chained claim ledger. Statements are formally partitioned into four epistemological tiers:
- `OBSERVED`: Empirical facts verified by execution (e.g. exit code 1, exact JUnit trace).
- `DERIVED`: Deterministic static deductions (e.g. symbol `calculate_tax` defined at `tax.py:45`).
- `INFERRED`: Hypotheses verified via targeted experiments.
- `ASSUMED`: Unverified working heuristics.
