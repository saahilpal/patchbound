# Contributing to PatchProof

First off, thank you for considering contributing to **PatchProof**! 🎉

PatchProof is an open-source, deterministic trust boundary and bounded AI repair engine designed for mission-critical software verification. We welcome contributions from developers, researchers, and AI safety engineers.

---

## 🧭 Code of Conduct

This project and everyone participating in it is governed by the [PatchProof Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## 🛠️ Development Setup

PatchProof uses [`uv`](https://github.com/astral-sh/uv) for fast, deterministic, reproducible dependency management and packaging.

### Prerequisites

- **Python:** 3.11 or 3.12
- **uv:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git:** Version 2.30+

### Clone & Install

```bash
# 1. Clone your fork or the repository
git clone https://github.com/saahilpal/patchproof.git
cd patchproof

# 2. Sync virtual environment and development dependencies
uv sync --extra dev

# 3. Verify setup
uv run patchproof doctor
```

---

## 🧪 Testing & Quality Invariants

PatchProof enforces strict quality and architectural invariants. Pull requests must satisfy all of the following checks before merging:

### 1. Unit & Integration Tests

```bash
uv run pytest
```
*Target: 100% passing tests with zero skips.*

### 2. Strict Type Checking (Mypy)

```bash
uv run mypy patchproof tests
```
*Target: Zero type errors across all source files under `mypy --strict`.*

### 3. Linting & Formatting (Ruff)

```bash
uv run ruff check .
uv run ruff format --check .
```
*Auto-fix lint issues with:* `uv run ruff check --fix .`

---

## 🏛️ Architectural Doctrine & Principles

When submitting code to PatchProof, please adhere to our first-principles design rules:

1. **Thick Deterministic Spine vs. Thin Probabilistic Leaf:**
   - The LLM is an untrusted leaf node.
   - All state transitions, clones, test reproductions, and anti-cheat validations must be deterministic and verifiable without an LLM.
2. **Reproduction Invariant:**
   - A bug must deterministically fail in an isolated sandbox clone before any repair action is dispatched.
3. **Pinned Test Oracles:**
   - Test suites and test configurations must never be modified by repair agents. All tests are restored via `git checkout -- tests/` before differential verification.
4. **Epistemological Claim Grounding:**
   - Every claim emitted by PatchProof must be tagged as `OBSERVED`, `DERIVED`, `INFERRED`, or `ASSUMED`.
5. **No Token Waste:**
   - Short-circuit early on unreproducible or out-of-scope failures.

---

## 🌿 Git & Commit Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new feature or capability (e.g. `feat(auth): add biometric keyring backend`)
- `fix:` A bug fix in PatchProof (e.g. `fix(sandbox): preserve file execution bits on hardlink clone`)
- `docs:` Documentation updates (e.g. `docs(readme): expand synapse integration guide`)
- `test:` Adding or refactoring tests
- `refactor:` Code restructuring without functional alterations
- `chore:` Maintenance, dependency bumps, CI updates

---

## 🚀 Submitting a Pull Request

1. **Fork the repo** and create a descriptive branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Write tests** covering your new behavior.
3. **Verify locally:**
   ```bash
   uv run ruff check .
   uv run mypy patchproof tests
   uv run pytest
   ```
4. **Push to your fork** and submit a Pull Request targeting `main`.
5. **Fill out the Pull Request Template:**
   - Reference associated issues (`Fixes #123`).
   - Confirm verification level (V1/V2/V3).
   - Confirm test suite passes.

---

## 💬 Getting Help

- Join our [GitHub Discussions](https://github.com/saahilpal/patchproof/discussions).
- Check our comprehensive documentation in the [`docs/`](../docs/) directory.
