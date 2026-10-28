# 🛡️ PatchProof v1.1

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?logo=python)](pyproject.toml)
[![Type Checking](https://img.shields.io/badge/Type%20Checking-mypy%20strict-brightgreen?logo=python)](pyproject.toml)
[![Linter](https://img.shields.io/badge/Linter-ruff-black?logo=ruff)](pyproject.toml)
[![Tests](https://img.shields.io/badge/Tests-48%20passed-success?logo=pytest)](tests/)
[![Verification](https://img.shields.io/badge/Assurance%20Levels-V1%20to%20V3%20CI--Clean-purple)](docs/VERIFICATION_AND_CLAIM_LEDGER.md)
[![Release](https://img.shields.io/badge/Release-v1.1.0-orange)](https://github.com/saahilpal/patchproof/releases/tag/v1.1.0)

**The Deterministic Trust Boundary & Bounded AI Repair Engine.**  
*Autonomous software diagnosis and verification for mission-critical codebases.*

[Features](#-core-capabilities) • [Architecture](#-first-principles-architecture) • [Comparison](#-industry-comparison) • [Quickstart](#-quickstart--cli-commands) • [Documentation](#-documentation-index)

</div>

---

## 💡 The Core Philosophy

Most autonomous coding agents fail in production because they treat the LLM as the entire system—wrapping an untrusted generative model in loose, unconstrained bash loops. This creates fatal failure modes:

1. **Hallucinated Passing Conditions:** The model claims a test passed when it didn't, or deletes failing assertions to "fix" the bug.
2. **Oracle Tampering & Test Gaming:** Models monkey-patch test suites (`unittest.mock.patch`), add `@pytest.mark.skip`, or insert `sys.exit(0)`.
3. **Context Drift & Runaway Token Spend:** Unbounded agentic loops pile up thousands of noisy tokens across 15+ conversational turns.

**PatchProof inverts the paradigm from first principles:**

> **"The intelligence is an untrusted, probabilistic leaf node. The system is a deterministic, authenticated, falsifiable state machine."**

Every proposed code change is executed in an **ephemeral hardlink clone**, verified against **pinned, hash-restored test oracles**, audited by an **AST anti-cheat scanner**, and recorded in a **cryptographic, hash-chained Claim Ledger**.

---

## ⚡ Core Capabilities

- 🔒 **Deterministic Ephemeral Sandboxing:** Every reproduction and verification attempt runs in an isolated hardlink clone (`/tmp/patchproof-workspaces`) with `core.hooksPath=/dev/null` and scrubbed environment variables (`PYTHONPATH`, `NODE_PATH`).
- 📌 **Pinned Test Oracles:** Test suites and build configs are cryptographically snapshotted. Before verification runs, oracles are restored to guarantee the patch didn't tamper with test assertions.
- 🚫 **AST Anti-Cheat & Egress Gates:** Static AST analyzers reject patches that delete assertions, inject mocks into production code, or bypass test runners. Egress gates redact secrets (AWS keys, GitHub PATs, private keys) from all outbound tokens.
- 🔬 **Epistemological Claim Ledger:** Replaces hand-wavy model rationales with typed, audited claims:
  - `OBSERVED`: Ground-truth execution facts (exit codes, JUnit signatures).
  - `DERIVED`: Deterministic AST & call graph derivations (Synapse / AST locations).
  - `INFERRED`: Causal hypotheses validated via scratchpad experiments.
  - `ASSUMED`: Unverified heuristics (explicitly flagged in audit reports).
- 🚦 **Formal Verification Levels (V1 to V3):**
  - **Level V1:** Failing tests (Fail-to-Pass / F2P) pass cleanly.
  - **Level V2:** V1 achieved + existing passing tests (Pass-to-Pass / P2P) remain green.
  - **Level V3 (CI-Clean):** V2 achieved + complete repository CI command passes with zero regressions.
- 🐙 **Autonomous GitHub Workflow:** Fetch GitHub issues, clone repos, reproduce bugs, execute 9-stage causal repair loops, and open verified Pull Requests with cryptographic provenance.

---

## 🏛️ First-Principles Architecture

PatchProof is structured as a **9-Stage Bounded StateGraph** managed via LangGraph, with strict linear invariants and conditional back-propagation loops:

```mermaid
flowchart TD
    subgraph S1["Stage 1-3: Deterministic Triage Spine"]
        N1["1. Snapshot & Reproduce<br/>(Local Ephemeral Clone)"] --> N2["2. Parse & Triage<br/>(Deterministic Signatures)"]
        N2 --> N3{"3. Repairability Gate"}
    end

    subgraph S2["Stage 4-6: Causal Repair & Verification Loop"]
        N3 -->|Reproduced| N4["4. Investigator Loop<br/>(Synapse AST + Claim Ledger)"]
        N4 --> N5["5. Fixer Node<br/>(Anchored Text Edits)"]
        N5 --> N6["6. Patch Gate & Verify<br/>(Pinned Oracle + Levels V1-V3)"]
        N6 -->|Fail & Attempts Left| N4
    end

    subgraph S3["Stage 7-9: Review, Governance & Export"]
        N6 -->|Verified V1-V3| N7["7. Blind Reviewer<br/>(Anti-Cheat + EgressGate)"]
        N7 -->|Approved| N8["8. Human Approval Gate<br/>(Cryptographic Signature)"]
        N8 --> N9["9. Export & Audit Journal<br/>(SHA-256 Hash Chain)"]
        N7 -->|Rejected & Attempts Left| N4
        N3 -->|Flaky / Unreproducible| N9
        N6 -->|Budget Exhausted| N9
    end

    classDef stage fill:#1e1e2e,stroke:#89b4fa,stroke-width:2px,color:#cdd6f4;
    classDef gate fill:#313244,stroke:#f38ba8,stroke-width:2px,color:#f38ba8;
    class N1,N2,N4,N5,N6,N7,N9 stage;
    N3,N8 class gate;
```

### The 9 Execution Stages

| Stage | Name | Character | Function |
| :---: | :--- | :---: | :--- |
| **1** | `snapshot_reproduce` | Deterministic | Creates disposable clone; executes baseline test command $N$ times to classify flaky vs reproducible bugs. |
| **2** | `parse_triage` | Deterministic | Parses structured JUnit XML / JSON traces into normalized `FailureSignature` fingerprints. |
| **3** | `repairability_gate` | Deterministic | Blocks unfixable, flaky, or environment-mismatched failures before calling LLMs. |
| **4** | `investigator` | Agentic / Causal | Queries Synapse AST graph, formulates hypotheses, executes scratch interventions, and builds `ClaimLedger`. |
| **5** | `fixer` | Structured LLM | Synthesizes minimal causal repair plan and anchored edits `(file_path, old_text, new_text)`. |
| **6** | `patch_verify` | Deterministic | Creates clean clone, applies edits, restores pinned test oracle, and asserts Level V1–V3 verification. |
| **7** | `review` | Independent Critic | Blind review of canonical diff without fixer explanation; checks anti-cheat invariants and secret egress. |
| **8** | `human_approval` | Governance | Binds patch digest, verification hash, and policy metadata into a cryptographic signature. |
| **9** | `export_report` | Deterministic | Records immutable entry in `AuditJournal` (SHA-256 chain) and exports diagnostic Markdown report. |

---

## 🥊 Industry Comparison

| Capability | **PatchProof v1.1** | Devin / OpenHands | Aider | Standard Chatbot (ChatGPT / Claude) |
| :--- | :---: | :---: | :---: | :---: |
| **Trust Boundary** | **Thick Deterministic Spine** | Loose Prompt Loop | Git Commits Only | None (Prompt only) |
| **Test Verification** | **Formal Levels (V1–V3)** | Raw Test Output | Terminal Regex | Model Self-Report |
| **Oracle Pinning** | **Cryptographic Snapshot & Restore** | ❌ No (Can edit tests) | ❌ No | ❌ No |
| **Anti-Cheat Scanner** | **AST-Level & Regex Guard** | ❌ No | ❌ No | ❌ No |
| **Secret Egress Gate** | **Pre-Flight Regex & Entropy** | ❌ No | ❌ No | ❌ No |
| **Claim Provenance** | **Audited Epistemological Ledger** | ❌ No | ❌ No | ❌ No |
| **Structural AST Index** | **Synapse SQLite AST Graph** | Basic Vector/LSP | Universal Ctags | None |
| **Audit Trail** | **SHA-256 Hash-Chained Journal** | Session Logs | Git History | Session Logs |
| **Deterministic Offline Mode**| **100% Functional without LLMs** | ❌ Requires API | ❌ Requires API | ❌ Requires API |

---

## 🚀 Quickstart & CLI Commands

### 1. Installation
Managed cleanly via `uv` (no global `pip` contamination):

```bash
# Clone the repository
git clone https://github.com/saahilpal/patchproof.git
cd patchproof

# Install all dependencies with uv
uv sync --extra dev
```

### 2. First-Time Setup & Diagnostics
```bash
# Run guided setup (provisions .env, policy.yaml, and verifies sandboxes)
uv run patchproof setup

# Run non-destructive diagnostic health check
uv run patchproof doctor
```

```
                🛡️ PatchProof System Diagnostics & Health Check                 
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Subsystem  ┃ Component              ┃ S… ┃ Details / Action                  ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Core       │ Python Version (>=     │ ✓  │ Python 3.12.13                    │
│ Runtime    │ 3.11)                  │ P… │                                   │
│ Core       │ uv Package Manager     │ ✓  │ Installed and found on PATH       │
│ Runtime    │                        │ P… │                                   │
│ Core       │ Git Version Control    │ ✓  │ Configured for user identity      │
│ Runtime    │                        │ P… │                                   │
│ Integrati… │ GitHub CLI (gh)        │ ✓  │ Authenticated via gh CLI keyring  │
│ Integrati… │ Synapse AST Graph      │ ✓  │ Synap v2.4.1                      │
│ Storage    │ Ephemeral Sandboxes    │ ✓  │ Writable: /tmp/patchproof-worksp… │
│ Security   │ Policy Governance      │ ✓  │ Found: policy.yaml                │
│ AI Gateway │ AI Model Providers     │ ✓  │ Anthropic / Gemini / OpenAI       │
└────────────┴────────────────────────┴────┴───────────────────────────────────┘
```

### 3. Autonomous GitHub Issue Resolution
Solve issues end-to-end: clone remote repository, reproduce failure, investigate root cause, synthesize anchored fix, verify against test oracle, and create a signed Pull Request on GitHub:

```bash
uv run patchproof gh solve owner/repo#42
```

Review an incoming Pull Request with anti-cheat checks & pinned test oracles:
```bash
uv run patchproof gh review owner/repo#105 --cmd "pytest -v"
```

### 4. Local Repository Repair & Inspection
```bash
# Run 9-stage loop on a local repository with diff export
uv run patchproof run /path/to/repo --cmd "pytest -v tests/test_calc.py" --export-diff fix.diff

# Inspect codebase AST symbols via Synapse/Standard provider
uv run patchproof inspect symbols /path/to/repo add

# View cryptographic audit trail
uv run patchproof inspect journal
```

### 5. Running the Test Suite
```bash
# Run full unit, integration, and loop evolution test suite (48 tests)
uv run pytest -v
```

---

## 📋 Epistemological Claim Ledger

Every diagnosis emitted by PatchProof is backed by an audited, tamper-evident Claim Ledger:

```markdown
## Epistemological Claim Ledger

| Claim ID | Category | Confidence | Statement |
| :--- | :--- | :--- | :--- |
| `CLM-OBS-0` | `OBSERVED` | high | Test 'tests/test_calculator.py::test_add' failed with AssertionError: 2 - 3 == -1 != 5. |
| `CLM-DER-0` | `DERIVED` | high | Symbol 'add' identified at calculator.py:1-2 via SynapseContextProvider. |
| `CLM-INF-1` | `INFERRED` | high | Attempt 1 Hypothesis: Root cause resolved by adjusting return operator from - to + in calculator.py. |
```

---

## 📚 Documentation Index

| Specification | Description |
| :--- | :--- |
| 📋 [**Product Requirements Document (PRD)**](docs/PRD.md) | Product vision, personas, 12 Functional & 5 Non-Functional requirements, safety metrics ($FVR < 1.0\%$). |
| 🏛️ [**Architecture Specification**](docs/ARCHITECTURE.md) | The 9-stage execution graph, deterministic spine, and 3 narrow LLM roles. |
| 🗺️ [**Engineering Roadmap**](docs/ROADMAP.md) | Phased build plan, M1–M4 milestones, falsifiable hypotheses, and explicit deferrals. |
| 🛡️ [**System Design & Trust Boundary**](docs/SYSTEM_DESIGN_AND_TRUST_BOUNDARY.md) | Disposable clones, host invariants, two-phase sandboxing, and declarative policy (`policy.yaml`). |
| 🔬 [**Verification & Claim Ledger**](docs/VERIFICATION_AND_CLAIM_LEDGER.md) | Oracles, V1–V3 assurance levels, interventional experiments, and cryptographic grounding. |
| 🔄 [**LangGraph State Machine**](docs/LANGGRAPH_STATE_MACHINE.md) | State schema, reducers, human approval interrupt semantics, and hash-chained audit journal. |
| 📊 [**Evaluation Harness**](docs/EVALUATION_HARNESS.md) | Benchmark methodology, False-Verified Rate ($FVR$), and synthetic mutation injector. |
| 🔌 [**API & Interface Contracts**](docs/API_AND_INTERFACES.md) | Pydantic models, runner adapter interfaces, and context provider contracts. |

---

## 📜 License

Licensed under the [Apache License, Version 2.0](LICENSE).  
Copyright (c) 2026 PatchProof Core Team & Contributors.
