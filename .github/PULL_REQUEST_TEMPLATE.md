## 🛡️ Pull Request Description

### Summary
<!-- Provide a concise description of the changes made and the motivation behind them. -->

### Related Issues
<!-- Link relevant issues: Fixes #123, Resolves #456 -->
Fixes #

---

### 🔬 Verification & Quality Checklist

Please confirm that your changes satisfy the following invariants:

- [ ] **Deterministic Tests:** Added or updated unit/integration tests (`uv run pytest`) — all pass cleanly.
- [ ] **Strict Typing:** `uv run mypy patchbound tests` passes with 0 errors (`mypy --strict`).
- [ ] **Linter & Formatting:** `uv run ruff check .` and `uv run ruff format --check .` pass.
- [ ] **Anti-Cheat Compliance:** No test skips (`@pytest.mark.skip`), assertion deletions, or artificial bypasses introduced.
- [ ] **No Secret Leaks:** Verified zero secrets or tokens included in test fixtures, mocks, or logs.
- [ ] **Documentation:** Updated `README.md` or `docs/` if modifying CLI commands, configuration, or architectural interfaces.

---

### 🚦 PatchBound Verification Level

If this PR fixes a code defect, what assurance level was verified?
- [ ] **Level V1 (Fail-to-Pass):** Target failing test reproduces in baseline and passes in target clone.
- [ ] **Level V2 (Pass-to-Pass):** All existing passing tests in the impacted test suite remain green.
- [ ] **Level V3 (CI-Clean):** Full repository CI test command passes with zero regressions.
- [ ] **N/A:** Documentation, infrastructure, or refactoring.
