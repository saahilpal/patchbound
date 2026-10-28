# 🛡️ PatchProof v1.1

<div align="center">

```
 ____       _       _     ____                 __ 
|  _ \ __ _| |_ ___| |__ |  _ \ _ __ ___   ___  / _|
| |_) / _` | __/ __| '_ \| |_) | '__/ _ \ / _ \| |_ 
|  __/ (_| | || (__| | | |  __/| | | (_) | (_) |  _|
|_|   \__,_|\__\___|_| |_|_|   |_|  \___/ \___/|_|  
```

[![PyPI](https://img.shields.io/pypi/v/patchproof.svg?logo=pypi&logoColor=white)](https://pypi.org/project/patchproof/)
[![Release](https://img.shields.io/badge/Release-v1.1.0-orange?logo=github)](https://github.com/saahilpal/patchproof/releases/tag/v1.1.0)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?logo=python)](pyproject.toml)
[![Type Checking](https://img.shields.io/badge/Type%20Checking-mypy%20strict-brightgreen?logo=python)](pyproject.toml)
[![Linter](https://img.shields.io/badge/Linter-ruff-black?logo=ruff)](pyproject.toml)
[![Tests](https://img.shields.io/badge/Tests-65%20passed-success?logo=pytest)](tests/)
[![Powered By Synapse](https://img.shields.io/badge/AST%20Engine-Synapse%20v2.4-blueviolet)](https://github.com/saahilpal/synapse)
[![Verification](https://img.shields.io/badge/Assurance%20Levels-V1%20to%20V3%20CI--Clean-purple)](docs/VERIFICATION_AND_CLAIM_LEDGER.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](.github/CONTRIBUTING.md)
[![Discussions](https://img.shields.io/badge/Discussions-Join-teal?logo=github)](https://github.com/saahilpal/patchproof/discussions)

**The Deterministic Trust Boundary & Bounded AI Repair Engine.**  
*Autonomous software diagnosis, AST call graph navigation, and cryptographic verification for mission-critical codebases.*

[Philosophy](#-the-core-philosophy) • [Under the Hood](#-under-the-hood-the-7-step-causal-repair-lifecycle) • [Supercharged by Synapse](#-supercharged-by-synapse-by-saahilpal) • [Competitor Analysis](#-competitive-landscape--first-principles-differentiation) • [Quickstart & CLI](#-quickstart--cli-reference) • [Secure Auth](#-secure-credential-management-0600-invariants) • [Docs](#-documentation-index) • [Community](#-community--contributing)

</div>

---

## 💡 The Core Philosophy

Most autonomous coding agents fail in production because they treat the Large Language Model as the entire system—wrapping an untrusted generative model in loose, unconstrained bash loops. This creates four fatal failure modes:

1. **Hallucinated Passing Conditions:** The model claims a test passed when it didn't, or deletes failing assertions to "fix" the bug.
2. **Oracle Tampering & Test Gaming:** Models monkey-patch test suites (`unittest.mock.patch`), add `@pytest.mark.skip`, or insert `sys.exit(0)` to fake green builds.
3. **Naive Vector RAG Drift:** Standard vector embeddings search by keyword similarity, failing completely on dynamic dispatch, inheritance hierarchies, and caller-callee reverse dependencies.
4. **Context Drift & Runaway Token Spend:** Unbounded agentic loops pile up thousands of noisy tokens across 15–30 conversational turns without convergence.

**PatchProof inverts the paradigm from first principles:**

> **"The intelligence is an untrusted, probabilistic leaf node. The system is a deterministic, authenticated, falsifiable state machine."**

Every proposed code change is executed in an **ephemeral hardlink sandbox clone**, navigated via a **SQLite AST structural graph** (powered by Synapse), verified against **pinned, hash-restored test oracles**, audited by an **AST anti-cheat scanner**, and recorded in a **cryptographic, SHA-256 hash-chained Claim Ledger**.

---

## 🔬 Under the Hood: The 7-Step Causal Repair Lifecycle

When you run `patchproof repair` or `patchproof gh solve`, PatchProof executes a deterministic, bounded pipeline where every state transition is falsifiable and audited:

```
[Target Codebase] ──> (1. Ephemeral Sandbox Clone)
                            │
                            ▼
                      (2. Reproduction Gate) ──[Fail? Reject early: zero token waste]
                            │
                            ▼
                      (3. Synapse AST Graph Traversal)
                            │  ├── Caller-Callee Edge Resolution
                            │  └── Impacted Test Suite Backtracking
                            ▼
                      (4. Epistemological Claim Ledger)
                            │  ├── OBSERVED: Exit codes, JUnit traces
                            │  └── DERIVED: AST symbol coordinates
                            ▼
                      (5. Anchored Patch Synthesis)
                            │  └── Exact (file, old_text, new_text) pairs
                            ▼
                      (6. Differential Verification Gate)
                            │  ├── Sandbox B (Patched Clone)
                            │  ├── Pinned Oracle Restoration (`git checkout -- tests/`)
                            │  ├── AST Anti-Cheat Assertions (`@pytest.mark.skip` rejected)
                            │  └── Secret Egress Filtering (Redacts keys & tokens)
                            ▼
                      (7. Cryptographic Journaling & Signed PR)
                            └── SHA-256 Hash Chain + Ed25519 Approval Signature
```

### Detailed Mechanics

1. **Ephemeral Sandboxing (`Copy-on-Write / Hardlinks`):**
   PatchProof creates disposable, isolated workspace clones in `/tmp/patchproof-workspaces` using Git hardlinks. The host repository is never touched directly during diagnosis or exploration. All git hooks are disabled (`core.hooksPath=/dev/null`) and runtime variables are scrubbed (`PYTHONPATH`, `NODE_PATH`).
2. **Deterministic Baseline Reproduction:**
   Before a single LLM token is spent, the test command is executed in the clean baseline sandbox. If the bug does not fail deterministically, PatchProof terminates immediately with an unreproducible classification—saving 100% of LLM costs.
3. **AST Call Graph Traversal (Synapse Integration):**
   Instead of naive vector similarity, PatchProof queries a local SQLite AST call graph (`.synap/synap.db`). It identifies the exact caller-callee chains, class hierarchies, and executes reverse dependency analysis to discover every test that exercises the modified code.
4. **Epistemological Claim Ledger:**
   The agent cannot make ungrounded assertions. Every fact is typed into an audited ledger:
   - `OBSERVED`: Ground-truth execution facts (exit code = 1, `AssertionError: expected 5 got 0`).
   - `DERIVED`: Deterministic AST derivations (symbol `calculate_tax` at `tax.py:45`).
   - `INFERRED`: Hypotheses verified via isolated scratchpad interventions.
   - `ASSUMED`: Unverified heuristics (flagged in audit warnings).
5. **Minimal Anchored Patch Generation:**
   Instead of generating full files (which introduces hallucinations and merge conflicts), PatchProof synthesizes strict anchored replacement blocks: `(file_path, old_text, new_text)`.
6. **Pinned Test Oracle & Anti-Cheat Gate:**
   PatchProof applies the patch to a fresh clone (`Sandbox B`) and immediately runs:
   ```bash
   git checkout -- tests/ **/test_*.py conftest.py
   ```
   This guarantees that an AI cannot "fix" a bug by modifying the test assertions. Furthermore, an AST visitor inspects all modified files to reject any commit containing skip annotations (`@pytest.mark.skip`, `@unittest.skip`, `@ts-ignore`), removed assertion statements, or injected mocks.
7. **Multi-Tier Assurance (Levels V1 to V3):**
   - **Level V1 (Fail-to-Pass):** The failing test case flips deterministically to `PASS`.
   - **Level V2 (Pass-to-Pass):** All previously passing tests in the impacted suite remain `PASS`.
   - **Level V3 (CI-Clean):** The complete repository CI test suite passes with zero regressions.

---

## ⚡ Supercharged by Synapse (by @saahilpal)

PatchProof natively integrates with **[Synapse](https://github.com/saahilpal/synapse)** (`synap-git`), an open-source, deterministic Git-aware structural retrieval engine created by [@saahilpal](https://github.com/saahilpal).

### Why Traditional RAG Fails for Autonomous Coding

Standard coding agents rely on vector databases (OpenAI embeddings, Chroma, Pinecone). In practice, vector search fails on codebases:
- **No Edge Awareness:** Vector search matches keyword similarity, but cannot traverse caller-to-callee call graphs.
- **Dynamic Dispatch Blindness:** Vector search cannot resolve interface implementations or polymorphic method calls.
- **Massive Token Waste:** Agents dump 20+ irrelevantly "similar" code chunks into the prompt context, blowing through rate limits.

### How Synapse Transforms PatchProof

Synapse parses the target codebase's Abstract Syntax Tree (AST) into a lightning-fast local SQLite database (`.synap/synap.db`):
- **Deterministic Symbol Resolution:** Sub-millisecond lookup of functions, methods, classes, and types.
- **Bidirectional Call Graphs:** Maps who calls a function, and all functions called by it.
- **Impacted Test Prediction:** Computes the exact transitive reverse dependency closure of any modified file to run the minimal set of impacted tests.

### Connecting & Managing Synapse via CLI

PatchProof provides dedicated CLI commands to manage Synapse out-of-the-box:

```bash
# 1. Install Synapse via the PatchProof CLI
patchproof synapse install

# Or install directly with pip / uv
pip install synap-git
uv tool install synap-git

# 2. Initialize and index your repository
cd /path/to/your/project
patchproof synapse index .

# 3. Inspect index health, indexed symbols, and call graph edges
patchproof synapse status .
```

Output:
```
                   ⚡ Synapse Structural Intelligence Status                   
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property                   ┃ Status / Value                                 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Synapse CLI (`synap`)      │ Installed (/Users/.../.local/bin/synap)         │
│ Database Index (`.synap`)  │ Found (.synap/synap.db)                        │
│ Indexed Files              │ 218                                            │
│ Indexed Symbols (AST)      │ 667                                            │
│ Call Graph Edges           │ 639                                            │
└────────────────────────────┴────────────────────────────────────────────────┘
```

You can also run structural queries directly:
```bash
patchproof synapse search "def calculate_tax"
```

---

## 🥊 Competitive Landscape & First-Principles Differentiation

| Feature / Invariant | **PatchProof v1.1** | Devin (Cognition AI) | OpenHands (OpenDevin) | SWE-agent (Princeton) | Aider (Paul Gauthier) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Architecture** | **Thick Deterministic Spine** | Proprietary Agent Loop | General ReAct Loop | ACI Shell Loop | Interactive Git Pair |
| **Context Retrieval** | **Synapse SQLite AST Graph** | Cloud Vector / LSP | Vector Embeddings | File Grep & Ctags | Universal Ctags / Grep |
| **Test Oracle Pinning** | **Cryptographic Snapshot & Restore** | ❌ No (Can edit tests) | ❌ No | ❌ No | ❌ No (User verifies) |
| **Anti-Cheat AST Gate** | **AST & Regex Inspection** | ❌ None | ❌ None | ❌ None | ❌ None |
| **Sandboxing Model** | **Ephemeral Hardlink Sandbox** | Cloud VM (Remote) | Docker Container | Docker Container | Local Host Git Tree |
| **Verification Assurance** | **Formal Levels V1–V3** | Unstructured Logs | Terminal Exit Code | Terminal Exit Code | User Acceptance |
| **Audit Provenance** | **SHA-256 Claim Ledger** | Proprietary Session | Session JSON | Trajectory JSONL | Git History |
| **Secret Egress Filtering** | **Pre-Flight Redaction Engine** | ❌ No | ❌ No | ❌ No | ❌ No |
| **Deterministic Mode** | **100% Offline (No LLM Required)** | ❌ Cloud SaaS Only | ❌ Requires LLM | ❌ Requires LLM | ❌ Requires LLM |
| **Open Source License** | **Apache 2.0 (100% Free)** | ❌ Closed Source | MIT | MIT | Apache 2.0 |

---

## 🔑 Secure Credential Management (0600 Invariants)

PatchProof handles your AI provider credentials and GitHub tokens with banking-grade security.

### Strict Filesystem Invariants

- **Storage Location:** `~/.config/patchproof/credentials.json`
- **Directory Mode:** `0700` (`rwx------`, owner-only read/write/execute)
- **File Mode:** `0600` (`rw-------`, owner-only read/write)
- **Zero Console Echo:** Interactive inputs use `click.prompt(hide_input=True)`.
- **Zero Log Leakage:** CLI outputs and diagnostic tables mask keys (e.g. `sk-ant-...4a9e`).
- **Precedence Hierarchy:** `PATCHPROOF_<PROVIDER>_KEY` > `<PROVIDER>_KEY` > `credentials.json`.

### Authentication Commands

```bash
# Guided interactive login (prompts for keys with masked input)
patchproof auth login

# Configure a specific provider
patchproof auth set-key anthropic
patchproof auth set-key gemini
patchproof auth set-key openai
patchproof auth set-key deepseek
patchproof auth set-key github

# Check credential status and active sources
patchproof auth status

# Safely delete credentials
patchproof auth logout anthropic
patchproof auth logout all
```

Status Display:
```
                🔑 PatchProof Authentication & Credential Store                 
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Provider   ┃ Env Variable       ┃   Status   ┃ Source         ┃ Masked Key    ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Anthropic  │ ANTHROPIC_API_KEY  │ Configured │ credentials.json│ sk-ant-...4a9e│
│ Gemini     │ GEMINI_API_KEY     │ Configured │ credentials.json│ AIzaSy...9b12 │
│ Openai     │ OPENAI_API_KEY     │ Configured │ credentials.json│ sk-proj...7f88│
│ Deepseek   │ DEEPSEEK_API_KEY   │  Not Set   │ missing        │ Not set       │
│ Github     │ GITHUB_TOKEN       │ Configured │ environment    │ ghp_...d81a   │
└────────────┴────────────────────┴────────────┴────────────────┴───────────────┘
```

---

## 🚀 Quickstart & CLI Reference

### 1. Installation

Install directly from PyPI:
```bash
pip install patchproof
```

Or using `uv`:
```bash
uv tool install patchproof
```

Or from source:
```bash
git clone https://github.com/saahilpal/patchproof.git
cd patchproof
uv sync --extra dev
```

### 2. Guided Setup & Health Checks

```bash
# Bootstrap policy.yaml, workspace sandboxes, and .env template
patchproof setup

# Run comprehensive system diagnostics
patchproof doctor
```

### 3. Autonomous GitHub Issue Solver

Resolve GitHub issues end-to-end: fetch issue, reproduce failure, investigate AST call graph, synthesize verified repair, assert Level V1–V3 verification, and create a cryptographically signed Pull Request:

```bash
# Authenticate GitHub CLI or set GITHUB_TOKEN
gh auth login

# Run issue solver
patchproof gh solve owner/repo#42
```

### 4. Review & Verify Incoming Pull Requests

Audit incoming Pull Requests with anti-cheat AST analysis and pinned test oracles:
```bash
patchproof gh review owner/repo#105 --cmd "pytest -v"
```

### 5. Local Repository Repair

Run the 9-stage loop on a local repository, export the verified patch diff, and optionally apply it to the host workspace:
```bash
# Verify and export patch diff
patchproof repair /path/to/project --cmd "pytest -v tests/test_core.py" --export-diff fix.diff

# Automatically apply the patch to the host repository once Level V1–V3 verification passes
patchproof repair /path/to/project --cmd "pytest -v tests/test_core.py" --apply
```

### 6. Diagnose Mode (Zero-Token Triage)

Reproduce and triage failures without applying code changes:
```bash
patchproof diagnose /path/to/project --cmd "pytest -v tests/test_core.py"
```

### 7. Evaluation & Synthetic Mutation Suite

Benchmark repair reliability and calculate Wilson score statistical confidence:
```bash
# Run SWE-bench or custom benchmark arm
patchproof eval benchmark --dataset swe_bench_lite.jsonl --arm patchproof_v1.1

# Inject a synthetic, validated mutation to test agent detection
patchproof eval inject /path/to/project --target src/calculator.py --cmd "pytest -v"
```

---

## 📋 Epistemological Claim Ledger Example

Every repair emits a tamper-evident audit ledger embedded in the final Pull Request:

```markdown
## Epistemological Claim Ledger

| Claim ID | Category | Confidence | Statement |
| :--- | :--- | :--- | :--- |
| `CLM-OBS-0` | `OBSERVED` | 1.00 | Test 'tests/test_calculator.py::test_add' failed with AssertionError: 2 - 3 == -1 != 5. |
| `CLM-DER-0` | `DERIVED` | 1.00 | Symbol 'add' identified at src/calculator.py:1-4 via SynapseContextProvider. |
| `CLM-INF-1` | `INFERRED` | 0.95 | Hypothesis 1: Operator mutated from '+' to '-'. Restoring '+' resolves failure. |
| `CLM-OBS-1` | `OBSERVED` | 1.00 | Verification Level V3 achieved: Fail-to-Pass (1/1), Pass-to-Pass (48/48). |
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
| ⚖️ [**Architectural Trade-Offs**](docs/TRADEOFFS.md) | In-depth trade-off analysis, first-principles rationale, and decision matrix across all 12 system dimensions. |

---

## 🤝 Ecosystem & Connected Projects

- **[Synapse (`synap-git`)](https://github.com/saahilpal/synapse):** Deterministic Git-aware structural AST retrieval engine created by [@saahilpal](https://github.com/saahilpal). Provides PatchProof with sub-millisecond symbol resolution, bidirectional caller-callee graphs, and impacted test set computation.

---

## 👥 Community & Contributing

We welcome contributions from researchers, software engineers, and AI safety practitioners!

- 📖 **Contributor Guide:** Check out [CONTRIBUTING.md](.github/CONTRIBUTING.md) for local environment setup, testing commands, and git conventions.
- 💬 **Discussions:** Join our [GitHub Discussions](https://github.com/saahilpal/patchproof/discussions) to ask questions or share ideas.
- 🛡️ **Security Invariants:** Please review our [Security Policy](.github/SECURITY.md) before reporting vulnerabilities.
- 🤝 **Code of Conduct:** We adhere to the [Contributor Covenant v2.1](.github/CODE_OF_CONDUCT.md).
- ❓ **Support:** Need assistance? See [SUPPORT.md](.github/SUPPORT.md).

---

## 📑 Academic Citation

If you use PatchProof or its epistemological verification engine in your academic research, benchmarking studies, or publications, please cite:

```bibtex
@software{pal2026patchproof,
  author = {Pal, Sahil and Contributors},
  title = {PatchProof: Deterministic Trust Boundary & Bounded AI Repair Engine},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/saahilpal/patchproof}}
}
```

---

## ⭐ Star History

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=saahilpal/patchproof&type=Date)](https://star-history.com/#saahilpal/patchproof&Date)

</div>

---

## 📜 License

Licensed under the [Apache License, Version 2.0](LICENSE).  
Copyright (c) 2026 Sahil Pal & PatchProof Contributors.
