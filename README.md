# PatchBound

[![PyPI](https://img.shields.io/pypi/v/patchbound.svg?logo=pypi&logoColor=white)](https://pypi.org/project/patchbound/)
[![Release](https://img.shields.io/badge/Release-v1.1.0-blue)](https://github.com/saahilpal/patchbound/releases/tag/v1.1.0)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?logo=python)](pyproject.toml)
[![Type Checking](https://img.shields.io/badge/Type%20Checking-mypy%20strict-brightgreen?logo=python)](pyproject.toml)
[![Linter](https://img.shields.io/badge/Linter-ruff-black?logo=ruff)](pyproject.toml)
[![Tests](https://img.shields.io/badge/Tests-80%20passed-success?logo=pytest)](tests/)

**A deterministic trust boundary and bounded AI repair engine for automated patch verification.**

PatchBound diagnoses software test failures, synthesizes minimal anchored code edits, and verifies candidate patches in ephemeral sandboxes against pinned test oracles and regression suites before any changes can touch your host repository.

---

## 1. Project Status & Honest Limitations

- **Current Version:** `v1.1.0` (Active development / beta).
- **Test Baseline:** 80 passing automated tests covering core sandboxing, AST anti-cheat analysis, LangGraph workflow transitions, and adversarial security vectors.
- **Static Quality:** 100% compliant under `mypy --strict` (0 errors across 96 source files) and `ruff`.
- **Benchmark Scope:** Evaluated on an initial 5-fixture reproducible benchmark suite (100% repair accuracy on target defects, 0% regressions, 0% false diagnoses). This is an early, focused benchmark suite—not evidence of universal repair capability across arbitrary codebases.
- **Provider Status:** Local deterministic spine, AST navigation, and offline heuristics are fully verified. Live cloud LLM synthesis requires user-provisioned API keys and is marked as unverified until configured in your environment.

---

## 2. The Problem: Why Generative Agents Cheat & Fail

Most autonomous coding agents wrap a Large Language Model inside an unconstrained terminal loop. When deployed against real codebases, this architecture exhibits severe failure modes:

1. **Oracle Tampering & Test Gaming:** Models frequently "fix" bugs by modifying test assertions, commenting out expectations, injecting `@pytest.mark.skip`, or inserting `sys.exit(0)` to force exit code 0.
2. **Silent Regressions:** A patch that fixes one failing test often silently breaks five previously passing tests if the agent only runs the target failure.
3. **Arbitrary File Overwrites:** Without rigorous path containment, models producing relative or symlinked diffs can write outside the workspace.
4. **Vector RAG Drift:** Standard vector embeddings search by keyword similarity, failing on polymorphic dispatch, inheritance trees, and caller-callee reverse dependencies.
5. **Context Pileup & Token Waste:** Unbounded conversational loops accumulate thousands of noisy tokens across 20+ turns without converging.

**PatchBound inverts the paradigm:**

> **The LLM is an untrusted, probabilistic leaf node. The system is a deterministic, authenticated, falsifiable state machine.**

---

## 3. How It Works

PatchBound isolates every candidate repair inside an out-of-tree Git scratch clone (`/tmp/patchbound-workspaces`). Edits are verified against physical test oracles restored from the base commit, audited by an AST anti-cheat scanner, and subjected to human approval before touching host files.

### 3.1 System Component Topology

```mermaid
flowchart TD
    subgraph ControlPlane ["Control Plane & CLI"]
        CLI["patchbound repair / gh solve"]
        VAL["Input Validation & Policy Engine"]
        CLI --> VAL
    end

    subgraph StateMachine ["Deterministic LangGraph Orchestration"]
        direction TB
        VAL --> S1["1. snapshot_reproduce<br/>(Ephemeral Sandbox A)"]
        S1 --> S2["2. parse_triage<br/>(Failure Normalization)"]
        S2 --> S3{"3. repairability_gate<br/>(Reproducible?)"}
        
        S3 -- "No (Flaky/Clean)" --> OUT_NOT_REP["NOT_REPRODUCIBLE<br/>(0 tokens spent)"]
        S3 -- "Yes (Fails)" --> S4["4. investigator<br/>(Context Assembly)"]
        
        S4 --> S5["5. fixer<br/>(Anchored Edit in Sandbox B)"]
        S5 --> S6["6. patch_verify<br/>(Pinned Oracle & V1-V3)"]
        
        S6 --> S7{"Verification Level?"}
        S7 -- "V0_FAILED / Regression<br/>(attempt < max)" --> S4
        S7 -- "Budget Exhausted" --> S9["9. export_report<br/>(BUDGET_EXHAUSTED)"]
        S7 -- "V1+ Verified" --> S8["7. review<br/>(Adversarial Invariant Check)"]
        
        S8 --> S8B{"8. human_approval<br/>(Operator Approved?)"}
        S8B -- "Approved" --> S9_OK["9. export_report<br/>(VERIFIED_EXPORTED)"]
        S8B -- "Rejected" --> S9_NO["9. export_report<br/>(REJECTED_BY_USER)"]
    end

    subgraph ContextSubsystem ["Context Retrieval Subsystem"]
        S4 -.-> CTX_SELECT{"Context Provider Selection<br/>(--context auto|synapse|standard)"}
        CTX_SELECT --> STD_CTX["Standard Context<br/>(Git diff, modified files, grep)"]
        CTX_SELECT --> SYN_CTX["Synapse AST Engine (Optional)<br/>(SQLite call graph, bidirectional edges)"]
    end

    subgraph HostBoundary ["Host Protection & Governance"]
        S9_OK --> DIFF_EXPORT["Export Verified .diff Patch"]
        S9_OK --> JOURNAL["Append to SHA-256 Claim Journal"]
        S9_OK --> APPLY_GATE{"--apply Passed<br/>AND Human Approved?"}
        APPLY_GATE -- "Yes" --> HOST_APPLY["git apply -p0 to Host Repository"]
        APPLY_GATE -- "No" --> HOST_SAFE["Host Unmodified (Safe)"]
    end

    classDef cli fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef spine fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef context fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef gate fill:#fff3e0,stroke:#f57c00,stroke-width:2px;

    class CLI,VAL cli;
    class S1,S2,S3,S4,S5,S6,S7,S8,S8B,S9,S9_OK,S9_NO,OUT_NOT_REP spine;
    class CTX_SELECT,STD_CTX,SYN_CTX context;
    class DIFF_EXPORT,JOURNAL,APPLY_GATE,HOST_APPLY,HOST_SAFE gate;
```

### 3.2 State Machine Workflow & Routing

```mermaid
stateDiagram-v2
    [*] --> SnapshotReproduce: CLI invokes repair

    SnapshotReproduce --> ParseTriage: Raw execution trace captured
    ParseTriage --> RepairabilityGate: Parse exit code & stack trace

    state RepairabilityGate {
        [*] --> CheckFailures
        CheckFailures --> Reproducible: Failures >= 1
        CheckFailures --> NonReproducible: Failures == 0
    }

    NonReproducible --> ExportReport: Outcome = NOT_REPRODUCIBLE (Abort)
    Reproducible --> Investigator: Confirmed failing baseline

    Investigator --> Fixer: Gather symbols & AST context
    Fixer --> PatchVerify: Apply anchored edit to Sandbox B

    state PatchVerify {
        [*] --> RestoreTestOracle
        RestoreTestOracle --> ScanAntiCheat
        ScanAntiCheat --> RunTargetTests
        RunTargetTests --> RunRegressionSuite
    }

    PatchVerify --> Review: VerificationLevel >= V1_F2P
    PatchVerify --> Investigator: V0_FAILED or Regression (attempt < max_attempts)
    PatchVerify --> ExportReport: Budget exhausted (max_attempts reached)

    Review --> HumanApproval: Review passed
    Review --> Investigator: Anomaly detected (attempt < max_attempts)

    HumanApproval --> ExportReport: Record approval decision
    ExportReport --> [*]: Terminate & export patch
```

---

## 4. Real Example: Causal Repair Lifecycle

```
[Target Codebase] ──> (1. Ephemeral Sandbox Clone)
                            │
                            ▼
                      (2. Baseline Reproduction Gate) ──[Pass? Exit early: NOT_REPRODUCIBLE]
                            │
                            ▼
                      (3. Context Assembly & AST Graph)
                            │  ├── Caller-Callee Edge Resolution
                            │  └── Impacted Test Suite Backtracking
                            ▼
                      (4. Causal Repair Synthesis)
                            │  └── Minimal Anchored Edits: (file, old_text, new_text)
                            ▼
                      (5. Differential Verification Gate)
                            │  ├── Sandbox B (Patched Clone)
                            │  ├── Pinned Oracle Restoration (`git checkout -- tests/`)
                            │  ├── AST Anti-Cheat Assertions (`@pytest.mark.skip` rejected)
                            │  └── Secret Egress Filtering (Redacts keys & tokens)
                            ▼
                      (6. Human Approval Boundary)
                            │  └── Explicit operator signoff required for host modification
                            ▼
                      (7. Patch Export / Host Application)
                            └── Canonical .diff exported; applied via `git apply -p0` if approved
```

---

## 5. Installation & Minimal Quickstart

### Prerequisites
- Python 3.11 or 3.12
- Git 2.30+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`

### Installation

PatchBound is published on PyPI at [pypi.org/project/patchbound](https://pypi.org/project/patchbound/):

```bash
# Using uv (recommended)
uv tool install patchbound

# Or using standard pip
pip install patchbound

# Verify installation
patchbound doctor
```

### 5-Minute Quickstart

Create a disposable repository with a bug:
```bash
mkdir -p /tmp/demo/tests && cd /tmp/demo
git init -b main && git config user.name "Demo" && git config user.email "demo@local"

# 1. Create buggy file
cat <<'EOF' > calc.py
def add(a, b):
    return a - b  # Bug: subtraction instead of addition
EOF

# 2. Create test
cat <<'EOF' > tests/test_calc.py
from calc import add
def test_add():
    assert add(10, 5) == 15
EOF

git add . && git commit -m "initial commit"
```

Run PatchBound repair in dry-run mode:
```bash
patchbound repair /tmp/demo --cmd "pytest -v tests/test_calc.py" --export-diff fix.diff
```

To apply the patch to your host repository once verified:
```bash
patchbound repair /tmp/demo --cmd "pytest -v tests/test_calc.py" --apply
```

---

## 6. Realistic CLI Session Output

```
$ patchbound repair /tmp/demo --cmd "pytest -v tests/test_calc.py" --export-diff fix.diff

╭──────────────────────────────────────────────────────────────────────╮
│  PatchBound v1.1  · Deterministic Trust Boundary & Bounded AI Repair │
╰──────────────────────────────────────────────────────────────────────╯
Target Repository: /tmp/demo
Reproduction Command: pytest -v tests/test_calc.py

                   Verification Summary                   
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                    ┃ Value                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Outcome Level             │   VERIFICATION LEVEL: V3   │
│ F2P Tests Flipped         │ 1 passed / 1 total         │
│ P2P Regressions           │ 0 (Clean)                  │
│ Tests Skipped Delta       │ 0                          │
│ Flake-Checked             │ ✓ Yes                      │
│ Oracle Integrity (Pinned) │ ✓ Verified                 │
│ Policy Clean              │ ✓ Yes                      │
│ Patch Digest              │ `80d5e597ca309091...`      │
└───────────────────────────┴────────────────────────────┘
╭──────────────────────────── Canonical Patch Diff ────────────────────────────╮
│   1 diff --git calc.py calc.py                                               │
│   2 index 5c81c35..0a419b7 100644                                            │
│   3 --- calc.py                                                              │
│   4 +++ calc.py                                                              │
│   5 @@ -1,2 +1,2 @@                                                          │
│   6  def add(a, b):                                                          │
│   7 -    return a - b  # Bug: subtraction instead of addition                │
│   8 +    return a + b  # Bug: subtraction instead of addition                │
│   9                                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯

Pipeline Terminated. Final Outcome: verified_exported
Verified Patch Digest: `80d5e597ca309091ac239d7f5d427362500e9fbcca049c583955141970875c18`
Approval Signature: `6f680ad34414507ab35896d80ce6a2f781df6ef5c1d67de437a495a142c413f0`
Patch Exported To: `fix.diff`
```

---

## 7. Safety Model & Invariants

PatchBound enforces multi-layered defensive controls:

1. **Out-of-Tree Scratch Isolation:** Explorations run in `/tmp/patchbound-workspaces`. Git hooks are suppressed (`core.hooksPath=/dev/null`) and runtime injection variables are scrubbed.
2. **Path Traversal & Symlink Rejection:** Candidate edits are restricted using `is_relative_to(workspace_path)`. Absolute paths and edits targeting symbolic links are rejected with a `PatchApplicationError`.
3. **Physical Oracle Pinning:** Tests are checked out fresh from the base commit prior to verification (`git checkout -- tests/`).
4. **AST Anti-Cheat Gate:** Rejects edits injecting `@pytest.mark.skip`, `@unittest.skip`, or modifying assertion logic.
5. **Multi-Tier Assurance Levels:**
   - **Level V1 (Fail-to-Pass):** Target test deterministically flips from FAIL to PASS.
   - **Level V2 (Pass-to-Pass):** Level V1 satisfied AND zero regressions across baseline passing tests.
   - **Level V3 (CI-Clean):** Full repository test suite passes cleanly with zero regressions.
6. **Mandatory Human Approval:** Patch application to the host repository (`--apply`) strictly requires `human_approved` status. Unapproved patches are blocked.
7. **Secret Egress Filtering:** Pre-flight regex filtering scrubs Anthropic, OpenAI, Gemini, DeepSeek, and GitHub API keys from outgoing prompts and logs.

---

## 8. Standard Context vs. Synapse Structural AST

PatchBound supports flexible code intelligence modes:

| Capability | Standard Context Provider | Synapse Structural AST Provider |
| :--- | :--- | :--- |
| **Dependencies** | None (Built-in Git & Python `ast`) | [Synapse (`synap-git`)](https://github.com/saahilpal/synapse) |
| **Storage Backend** | In-memory filesystem scan | Local SQLite (`.synap/synap.db`) |
| **Symbol Resolution** | Regex / AST file walk | Sub-millisecond indexed AST queries |
| **Call-Graph Traversal** | Heuristic grep across files | Bidirectional static call graph edges |
| **Impacted Test Calculation** | Directory matching | Transitive reverse dependency closure |

### Context Flags:
```bash
# Auto mode (default): Uses Synapse if indexed; falls back to standard
patchbound repair /path/to/project --context auto

# Explicit Synapse: Fails fast with clear setup guide if unindexed
patchbound repair /path/to/project --context synapse

# Standard mode: Forces built-in provider
patchbound repair /path/to/project --context standard
```

---

## 9. Architecture & Design Trade-Offs

Key architectural decisions and their trade-offs:

1. **Ephemeral Clones vs. In-Place Editing:** Clones consume temporary disk space in `/tmp/`, but completely eliminate host repository corruption or partial-edit contamination.
2. **Anchored Replacement Edits vs. Full-File Rewrites:** Anchored hunks require exact character matching, but eliminate hallucinations and massive diff merge conflicts.
3. **Deterministic Spine vs. Autonomous Agent Loops:** Restricting the LLM to a bounded node prevents runaway conversational loops and bounds cost.
4. **Fail-Closed on Clean Baselines:** Aborting immediately when a test doesn't reproduce prevents spending tokens hallucinating fixes for non-issues.

*For an exhaustive breakdown across all 12 system dimensions, see the [Architectural Trade-Offs Specification](docs/architecture/tradeoffs.md).*

---

## 10. Testing & Benchmark Methodology

PatchBound is validated through empirical testing:
- **80 Automated Tests:** Across unit, integration, adversarial security, and benchmark suites.
- **5-Fixture Empirical Benchmark:** Evaluates arithmetic bug repair, regression adversary trapping, unrepairable assertions, clean baseline short-circuiting, and multi-attempt feedback loops.
- **Held-Out Test Invariant:** Repairs are validated against held-out tests (`tests/test_held_out.py`) that were never exposed to the agent during investigation.

Run the full suite:
```bash
uv run pytest
```

Run the benchmark harness:
```bash
uv run pytest tests/integration/test_repair_benchmark.py -v
```

---

## 11. Configuration & Supported Providers

Configure cloud model providers using the zero-trust credential store (`0600` permissions at `~/.config/patchbound/credentials.json`):

```bash
# Interactive guided login
patchbound auth login

# Set individual provider key
patchbound auth set-key anthropic
patchbound auth set-key gemini
patchbound auth set-key openai
patchbound auth set-key deepseek

# Check active status
patchbound auth status
```

---

## 12. Known Limitations & Unsupported Scenarios

1. **Non-Deterministic / Heuristic Test Suites:** If a test passes or fails probabilistically due to network calls or sleep statements, PatchBound will classify it as `NOT_REPRODUCIBLE`.
2. **Binary / Non-Text Files:** Anchored edits support UTF-8 text files only. Binary assets and compiled blobs cannot be repaired.
3. **Multi-Repo Dependencies:** PatchBound currently assumes the defect and test suite reside in a single Git repository.
4. **Live Provider Execution:** Requires user-supplied API credentials. Without credentials, PatchBound runs its deterministic spine and offline heuristics.

---

## 13. Documentation Index

Comprehensive documentation is organized in [`docs/`](docs/README.md):

- 🏛️ [**Architecture Overview**](docs/architecture/overview.md)
- 🔄 [**LangGraph State Machine**](docs/architecture/orchestration.md)
- 🔌 [**Context Providers & Synapse**](docs/architecture/context-providers.md)
- 🔬 [**Verification Design & Claim Ledger**](docs/architecture/verification.md)
- ⚖️ [**Architectural Trade-Offs**](docs/architecture/tradeoffs.md)
- 🛡️ [**Trust Boundaries & Sandboxing**](docs/security/trust-boundaries.md)
- 🚨 [**Threat Model & Vulnerability Defenses**](docs/security/threat-model.md)
- 📦 [**Installation Guide**](docs/guides/installation.md)
- 🚀 [**Quickstart Tutorial**](docs/guides/quickstart.md)
- ⚙️ [**Configuration & Credentials**](docs/guides/configuration.md)
- ⚡ [**Synapse Integration Guide**](docs/guides/synapse.md)
- 🤝 [**Contributing Guide**](docs/development/contributing.md)
- 📋 [**API Reference**](docs/development/api-reference.md)
- 📊 [**Benchmark Methodology & Results**](docs/benchmarks/methodology-and-results.md)
- 🛡️ [**Phase 3 Adversarial Security Audit**](docs/audits/security-adversarial-report.md)
- 📈 [**Phase 3 Repair Benchmark Audit**](docs/audits/repair-benchmark-report.md)
- 🚦 [**Phase 3 Blockers & Release Decision**](docs/audits/phase3-blockers.md)

---

## 14. Contributing & Community

Contributions are welcome! Please review:
- [CONTRIBUTING.md](CONTRIBUTING.md) for local environment setup and quality gates.
- [SECURITY.md](SECURITY.md) for responsible disclosure.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community guidelines.

---

## 15. License

Licensed under the [Apache License, Version 2.0](LICENSE).  
Copyright (c) 2026 Sahil Pal & PatchBound Contributors.
