# PatchBound Documentation Suite

Welcome to the technical documentation for **PatchBound v1.1.0** — the deterministic trust boundary and bounded AI repair engine for automated software verification.

---

## 🏛️ Architecture & System Design
- [**Architecture Overview**](architecture/overview.md): System topology, the 9-stage execution pipeline, and the thick deterministic spine.
- [**LangGraph State Machine**](architecture/orchestration.md): Orchestration graph, `PatchBoundState` schema, failure deltas, and state transitions.
- [**Context Providers**](architecture/context-providers.md): Standard Git context vs Synapse structural AST SQLite context, selection modes, and fallback guarantees.
- [**Verification Design & Claim Ledger**](architecture/verification.md): Verification Levels (V0–V3), pinned test oracles, anti-cheat AST analysis, and SHA-256 hash-chained claim ledger.
- [**Architectural Trade-Offs**](architecture/tradeoffs.md): In-depth trade-off analysis across all 12 core system dimensions.

---

## 🛡️ Security & Trust Boundaries
- [**Trust Boundaries & Sandboxing**](security/trust-boundaries.md): Ephemeral hardlink sandbox clones, host repository immutability, and scratch containment.
- [**Threat Model & Defenses**](security/threat-model.md): Threat vectors, path traversal rejection, symlink hijacking defenses, secret egress sanitization, and responsible disclosure.

---

## 🚀 Guides & Quickstart
- [**Installation Guide**](guides/installation.md): Prerequisites, installing via PyPI, uv, or source, and diagnostic verification via `patchbound doctor`.
- [**Quickstart Tutorial**](guides/quickstart.md): 5-minute verified tutorial demonstrating repair, verification summary, and human approval boundary.
- [**Configuration & Credentials**](guides/configuration.md): Zero-trust credential store (`0600` permissions), auth CLI commands, environment variables, and `policy.yaml`.
- [**Synapse Integration Guide**](guides/synapse.md): Setting up, indexing, and querying the Synapse structural AST engine.

---

## 🧪 Development & API Reference
- [**Contributing Guide**](development/contributing.md): Local developer setup, quality gates (`pytest`, `mypy --strict`, `ruff`), and contribution workflow.
- [**API Reference & Contracts**](development/api-reference.md): Pydantic data models, runner adapters, and context provider protocols.

---

## 📊 Benchmarks & Empirical Evaluation
- [**Benchmark Methodology & Results**](benchmarks/methodology-and-results.md): Evaluation philosophy, 5-fixture benchmark specification, empirical results ledger, and live provider status.

---

## 📋 Historical Audit Reports
- [**Phase 3 Adversarial Security Report**](audits/security-adversarial-report.md): Red-team testing covering path traversal, symlinks, unapproved patch gating, and journal tampering.
- [**Phase 3 Repair Benchmark Report**](audits/repair-benchmark-report.md): Detailed 5-fixture empirical benchmark results, runtime, cost, and provider evaluation.
- [**Phase 3 Blockers & Decision Report**](audits/phase3-blockers.md): Verification evidence, environmental blockers, and final release GO recommendation.
- [**Phase 2 E2E Validation Report**](audits/e2e-validation-report.md): Verification across all 8 real-world repair scenarios and Synapse FastMCP contracts.
- [**Phase 2 Feature Verification Matrix**](audits/feature-verification-matrix.md): Exhaustive feature-by-feature verification ledger.
- [**Phase 2 Manual Test Results**](audits/manual-test-results.md): Step-by-step raw command outputs and manual verification evidence.
- [**Defect Backlog**](audits/defect-backlog.md): Prioritized backlog of discovered and resolved items.

---

## 📜 Specifications & Strategy
- [**Product Requirements Document (PRD)**](PRD.md): Product vision, user personas, functional & non-functional requirements.
- [**Engineering Roadmap**](ROADMAP.md): Milestones M1 through M4, falsifiable hypotheses, and explicit deferrals.
