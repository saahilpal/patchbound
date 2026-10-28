# Development & Contributing Guide — PatchBound v1.1.0

**Document:** Developer Setup, Testing Standards, & Contribution Workflow  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Contributing Guide](contributing.md) • [API Reference](api-reference.md) • [Root Contributing Guide](../../CONTRIBUTING.md)

---

## 1. Quickstart for Contributors

PatchBound uses [`uv`](https://github.com/astral-sh/uv) for fast, deterministic dependency management.

```bash
# 1. Clone your fork
git clone https://github.com/saahilpal/patchbound.git
cd patchbound

# 2. Sync virtual environment and development tools
uv sync --extra dev

# 3. Verify health
uv run patchbound doctor
```

---

## 2. Quality Gates & Pre-Commit Invariants

Every pull request must pass the three standard quality gates:

### Gate 1: Test Suite
```bash
uv run pytest
```
*Current baseline: 80 passed tests in ~68s. All tests must pass with zero skips or xfails.*

### Gate 2: Strict Type Checking
```bash
uv run mypy patchbound tests
```
*Configuration: `strict = true` across 96 source files. Must pass with zero errors.*

### Gate 3: Formatting & Linting
```bash
uv run ruff check .
uv run ruff format --check .
```
*Auto-fix lint issues with:* `uv run ruff check --fix .`

---

## 3. Package Build & Smoke Test

Before submitting, verify that the package builds and installs cleanly:
```bash
# Build wheel and sdist
uv build

# Verify build artifacts
ls -la dist/
```

---

## 4. Architectural Rules

1. **Deterministic Spine:** All core state transitions must be reproducible without an LLM.
2. **Oracle Pinning:** Never alter tests or mocks to make a repair succeed.
3. **No Direct Host Writes:** All exploration and patching must happen in `/tmp/patchbound-workspaces`.
4. **No Secrets in Logs:** All keys and tokens must be masked or scrubbed.
