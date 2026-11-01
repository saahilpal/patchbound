# PatchBound Documentation

Welcome to the documentation for **PatchBound**. This folder contains the technical design files, user guides, and audit reports written during the project.

> [!NOTE]
> **Project Status:** PatchBound has been discontinued. Read [**POSTMORTEM.md**](../POSTMORTEM.md) for the honest story of why I stopped working on it.

---

## 🏛️ Architecture & System Design
- [**Verification Engine HLD/LLD (proposed)**](architecture/verification-engine-spec.md): Trusted supervisor, sandbox, split-job GitHub Actions model, evidence schemas, pure judge, test transplant, and property-test plan.
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

## 🔍 Independent Audits & Strategic Analysis
- [**Engineering Audit**](audits/ENGINEERING_AUDIT.md): Comprehensive source inspection, contract verification, and verified implementation gaps.
- [**Product Audit**](audits/PRODUCT_AUDIT.md): Assessment of target users, competitive workflows, differentiation, and product viability.
- [**Executive Verdict**](audits/EXECUTIVE_VERDICT.md): Executive summary and strategic recommendation on product direction.
- [**Component Disposition Inventory**](audits/KEEP_REMOVE_REWRITE.md): Component-by-component analysis classifying systems as keep, simplify, rewrite, or remove.
- [**Contingent Target Architecture**](audits/TARGET_ARCHITECTURE.md): Minimal replacement design for narrow, reliable patch-evidence workflows.
- [**Decision-Gated Roadmap**](audits/ROADMAP.md): Prioritized remediation and discovery gates (P0–P3, NEVER).

---

## 📜 Specifications & Requirements
- [**Product Requirements Document (PRD)**](PRD.md): Product vision, user personas, functional & non-functional requirements.
