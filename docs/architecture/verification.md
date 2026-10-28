# Verification Design & Claim Ledger — PatchBound v1.1.0

**Document:** Formal Verification Levels & Epistemological Claim Ledger  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Architecture Overview](overview.md) • [State Machine](orchestration.md) • [Context Providers](context-providers.md) • [Verification Design](verification.md) • [Trade-Offs](tradeoffs.md)

---

## 1. Multi-Tier Verification Levels (V0 to V3)

A proposed patch is never declared successful based on a single exit code. PatchBound evaluates candidate patches against a rigorous 4-tier assurance hierarchy:

| Level | Identifier | Invariants Required | Passing Criterion |
| :--- | :--- | :--- | :--- |
| **V0** | `V0_FAILED` | None | Target test fails, patch causes syntax error, or regresses existing tests. |
| **V1** | `V1_F2P` | Fail-to-Pass | The original failing test case transitions deterministically from `FAIL` to `PASS`. |
| **V2** | `V2_P2P` | Pass-to-Pass (Regression Clean) | Level V1 satisfied AND all previously passing baseline tests remain `PASS`. |
| **V3** | `V3_CI_CLEAN` | CI-Clean (Full Repository Clean) | Levels V1 & V2 satisfied AND complete repository test suite passes with zero regressions. |

---

## 2. Pinned Test Oracle & Anti-Cheat Invariants

### 2.1 Pinned Test Oracles
Autonomous agents given bash or write access frequently modify test suites to "fix" bugs (e.g. altering expected values or deleting assertions). 

PatchBound implements **physical oracle pinning**:
```bash
# Executed in Sandbox B immediately before running verification
git checkout -- tests/ **/test_*.py conftest.py
```
Any changes made by the repair agent to test files are wiped out and restored to their original commit state prior to running test execution.

### 2.2 AST Anti-Cheat Scanner
In addition to oracle pinning, `patchbound.core.anti_cheat` performs Abstract Syntax Tree analysis over all candidate edits. Commits are rejected with a `PolicyViolation` if they introduce:
- Test skip decorators (`@pytest.mark.skip`, `@pytest.mark.xfail`, `@unittest.skip`).
- Type suppression directives (`# type: ignore`, `@ts-ignore`).
- Dynamic mocking injections designed to override assertions (`unittest.mock.patch`).
- Forced process exits (`sys.exit(0)`, `os._exit(0)`).

---

## 3. Epistemological Claim Ledger

Every investigation outputs a cryptographic, append-only claim ledger detailing the factual basis of the repair.

### Statement Categories:
1. **`OBSERVED` (Confidence 1.00):** Ground-truth empirical observations verified by command execution (e.g. exit codes, JUnit error strings).
2. **`DERIVED` (Confidence 1.00):** Deterministic static derivations (e.g. AST symbol line ranges, call-graph edges).
3. **`INFERRED` (Confidence 0.70–0.95):** Inductive hypotheses verified via differential test runs in Sandbox B.
4. **`ASSUMED` (Confidence < 0.70):** Unverified working heuristics (explicitly flagged in audit reports).

### Cryptographic Hash-Chain Verification
The claim ledger entries are serialized and linked via SHA-256 hash pointers:
$$\text{entry\_hash} = H(\text{timestamp} \parallel \text{event\_type} \parallel \text{payload} \parallel \text{prev\_hash})$$

Integrity can be validated at any time using:
```bash
patchbound inspect journal --journal /path/to/journal.jsonl
```
If any record is mutated or truncated, `verify_integrity()` detects the chain break and pinpoints the exact tampered index.
