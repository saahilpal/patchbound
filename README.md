# PatchProof v1.1

> **Deterministic Trust Boundary & Bounded AI Repair Engine**  
> *Autonomous software diagnosis and verification for mission-critical codebases.*

---

## What is PatchProof?

PatchProof is an automated software repair engine designed around a **thick deterministic trust boundary** and **three narrow LLM roles**.

Unlike complex multi-agent frameworks that chain 7+ conversational LLMs together (dropping context, accumulating hallucinations, and inflating token cost), PatchProof inverts the paradigm:
1. **Deterministic Spine:** Cloning, environment sandboxing, log parsing, test verification, anchored diff patching, policy enforcement, and audit journaling are executed by deterministic code.
2. **Three Narrow LLM Roles:**
   - **Investigator (Single Agent Loop):** Read-only investigation and causal experiments with strict step and token budgets.
   - **Fixer (Single Structured Call):** Emits a causal repair plan and exact anchored edits `(file, old_text, new_text)`.
   - **Adversarial Reviewer (Blind Call):** Validates the patch independently without seeing the fixer's explanation, flags anti-cheat violations, and generates probe tests.
3. **Reproduce-First & Pinned Oracle:** The system reproduces failures before attempting repair and verifies candidate patches against pinned, hash-restored test suites and configs.
4. **Verifiable Assurance (Levels V1 to V3):** Replaces ambiguous boolean claims with formal verification levels:
   - **V1:** Failing tests (F2P) pass.
   - **V2:** V1 achieved + impacted passing tests (P2P) pass.
   - **V3:** V2 achieved + full CI command passes.

---

## Documentation Index

Comprehensive technical specifications and implementation guides are available in [`docs/`](file:///Users/nitrousoxide/Code/patchproof/docs/):

- 📋 [**Product Requirements Document (PRD)**](file:///Users/nitrousoxide/Code/patchproof/docs/PRD.md): Product vision, user personas, functional/non-functional requirements, and safety KPIs.
- 🏛️ [**Architecture Specification**](file:///Users/nitrousoxide/Code/patchproof/docs/ARCHITECTURE.md): The 9-stage execution graph, deterministic spine, and 3 narrow LLM roles.
- 🗺️ [**Engineering Roadmap & Build Order**](file:///Users/nitrousoxide/Code/patchproof/docs/ROADMAP.md): Phased build plan, M1-M4 milestones, falsifiable hypotheses, and explicit deferrals.
- 🛡️ [**System Design & Trust Boundary**](file:///Users/nitrousoxide/Code/patchproof/docs/SYSTEM_DESIGN_AND_TRUST_BOUNDARY.md): Disposable local clones, host invariants, two-phase sandboxing, and unified policy (`policy.yaml`).
- 🔬 [**Verification Engine & Claim Ledger**](file:///Users/nitrousoxide/Code/patchproof/docs/VERIFICATION_AND_CLAIM_LEDGER.md): F2P/P2P test isolation, oracle pinning, verification levels V1-V3, interventional experiments, and cryptographic claim ledger.
- 🔄 [**LangGraph State Machine**](file:///Users/nitrousoxide/Code/patchproof/docs/LANGGRAPH_STATE_MACHINE.md): State schema, CAS store, human approval interrupt semantics, status taxonomy, and audit journal.
- 📊 [**Evaluation Harness**](file:///Users/nitrousoxide/Code/patchproof/docs/EVALUATION_HARNESS.md): Benchmark methodology, false-verified rate ($FVR$), and synthetic/mined test suites.
- 🔌 [**API, Contracts & Data Interfaces**](file:///Users/nitrousoxide/Code/patchproof/docs/API_AND_INTERFACES.md): Pydantic schemas, runner adapter interfaces, and context provider contracts.

---

## Directory Structure

```
patchproof/
├── docs/                               # Senior AI Engineering Documentation Suite
│   ├── PRD.md                          # Product requirements, personas, FRs/NFRs & success metrics
│   ├── ARCHITECTURE.md                 # 9-stage graph, deterministic spine & 3 LLM roles
│   ├── ROADMAP.md                      # Phased build order, milestones & falsifiable evaluation
│   ├── SYSTEM_DESIGN_AND_TRUST_BOUNDARY.md # Sandboxing, git invariants & policy file
│   ├── VERIFICATION_AND_CLAIM_LEDGER.md    # Oracles, V1-V3 levels, interventional experiments
│   ├── LANGGRAPH_STATE_MACHINE.md      # State reducers, interrupt flow & audit journal
│   ├── EVALUATION_HARNESS.md           # Benchmark protocols & False-Verified Rate
│   └── API_AND_INTERFACES.md           # Data models, contracts & schemas
├── patchproof/                         # Production Python Package
│   ├── core/                           # Deterministic spine & trust boundary
│   │   ├── clone.py                    # Disposable local clone & pre/post invariants
│   │   ├── sandbox.py                  # Two-phase sandbox (Prepare & Execute)
│   │   ├── patcher.py                  # Anchored edit engine & canonical diff
│   │   ├── digest.py                   # SHA-256 tree & patch digest generator
│   │   ├── policy.py                   # Declarative policy validator (policy.yaml)
│   │   └── anti_cheat.py               # AST & pattern-based cheat detector
│   ├── verification/                   # Deterministic test verification
│   │   ├── oracle.py                   # Pinned test suite & config restorer
│   │   ├── runner.py                   # Isolated test runner adapter
│   │   ├── levels.py                   # V1, V2, V3 verification evaluator
│   │   └── parsers/                    # Structured JUnit & JSON report parsers
│   ├── ledger/                         # Causal investigation & claim ledger
│   │   ├── claim.py                    # Typed claims (observed/derived/inferred/assumed)
│   │   ├── experiment.py               # Scratchpad interventional experiment runner
│   │   └── validator.py                # Cryptographic grounding & citation validator
│   ├── graph/                          # LangGraph 9-stage state machine
│   │   ├── state.py                    # TypedDict state, reducers & status taxonomy
│   │   ├── workflow.py                 # 9-stage StateGraph builder
│   │   └── nodes/                      # Stage 1 to Stage 9 node implementations
│   ├── llm/                            # LLM Gateway, structured calls & replay
│   │   ├── gateway.py                  # Role-tiered routing & budget enforcement
│   │   ├── schemas.py                  # Pydantic schemas for Fixer & Reviewer
│   │   ├── recorder.py                 # Replay/record mock harness for deterministic tests
│   │   └── egress.py                   # Secret scanner & prompt preview
│   ├── context/                        # Context providers
│   │   ├── base.py                     # Provider interface & contract
│   │   ├── standard.py                 # Baseline primitives (grep, AST, git log)
│   │   └── synapse.py                  # Synapse structural query adapter stub
│   ├── audit/                          # Audit journal & telemetry
│   │   ├── journal.py                  # Hash-chained append-only event journal
│   │   └── metrics.py                  # OpenTelemetry metric spans
│   └── cli/                            # Command-line interface
│       └── main.py                     # CLI entrypoint (`patchproof diagnose / repair`)
├── tests/                              # Unit, integration & regression tests
└── pyproject.toml                      # Hatchling build & dependencies configuration
```

---

## Quickstart & CLI Commands

### 1. First-Time Setup & Diagnostics
```bash
# Run guided setup (initializes .env, policy.yaml, and checks system health)
uv run patchproof setup

# Run non-destructive system diagnostics
uv run patchproof doctor
```

### 2. Autonomous GitHub Issue Resolution
```bash
# Solve an issue end-to-end: clone, reproduce, repair, verify, and open verified PR
uv run patchproof gh solve owner/repo#42

# Review an incoming PR with anti-cheat checks & pinned test oracles
uv run patchproof gh review owner/repo#105 --cmd "pytest -v"
```

### 3. Local Repository Repair & Inspection
```bash
# Run full 9-stage repair loop with auto-approval and diff export
uv run patchproof run /path/to/repo --cmd "pytest -v tests/test_target.py" --export-diff solution.diff

# Inspect codebase AST symbols via Synapse/Standard provider
uv run patchproof inspect symbols /path/to/repo add

# View cryptographic audit journal
uv run patchproof inspect journal
```

### 4. Running Verification Test Suite
```bash
# Execute full unit and integration test suite across all 48 test instances
uv run pytest
```
