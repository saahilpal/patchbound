# Benchmark Methodology & Empirical Results — PatchBound v1.1.0

**Document:** Evaluation Protocol & Empirical Benchmark Results  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Benchmarks Index](methodology-and-results.md) • [Phase 3 Benchmark Audit](../audits/repair-benchmark-report.md)

---

## 1. Evaluation Philosophy

PatchBound avoids vanity metrics (such as unverified fix rates or claims based on unpinned test runs). Our evaluation methodology enforces four rigorous invariants:
1. **Isolated Disposable Repositories:** Each fixture executes in a fresh, isolated Git repository in `/tmp/`.
2. **Pinned Test Oracles:** The candidate patch cannot touch test files or assertion logic.
3. **Independent Held-Out Evaluation:** A patch is only declared resolved if it passes an unexposed, held-out test suite (`tests/test_held_out.py`) and causes zero regressions on existing baseline tests (`p2p_regressed`).
4. **Honest Accounting:** We distinguish early, small-scale test suites from universal or production-grade benchmark claims.

---

## 2. The 5-Fixture Reproducible Benchmark Suite

The automated benchmark suite ([`tests/integration/test_repair_benchmark.py`](file:///Users/nitrousoxide/Code/patchbound/tests/integration/test_repair_benchmark.py)) contains 5 diverse bug scenarios:

| Fixture ID | Category | Nature of Defect | Expected Outcome | Verification Standard |
| :--- | :--- | :--- | :--- | :--- |
| **`bench_01_op_inversion`** | Arithmetic Inversion | Inverted operator (`a - b` instead of `a + b`) | Repaired on Attempt 0 | Target test PASS, Held-out test PASS |
| **`bench_02_regression_adv`** | Regression Adversary | Candidate patch fixes VIP pricing by returning 80 unconditionally, breaking regular customers | Rejected (`V0_FAILED`) | Detected `p2p_regressed` > 0 |
| **`bench_03_impossible`** | Unrepairable Spec | Impossible assertion (`assert 1 == 2`) | Budget Exhausted | Clean loop termination at `max_attempts` |
| **`bench_04_clean_baseline`** | Flaky / Non-reproducible | All tests in baseline pass cleanly | Abort (`NOT_REPRODUCIBLE`) | Immediate exit on Attempt 0 without consuming tokens |
| **`bench_05_evolution`** | Multi-Attempt Loop | Flawed edit on Attempt 0 (`*`); state machine evolves addition on Attempt 1 | Repaired on Attempt 1 | Attempt 0 rejected; Attempt 1 resolved |

---

## 3. Empirical Results Ledger

### Measured Metrics (v1.1.0 Baseline):

| Metric | Measured Value | Standard / Target |
| :--- | :--- | :--- |
| **Total Benchmark Fixtures** | 5 | 5 |
| **Repairable Fixtures** | 2 (`bench_01`, `bench_05`) | 2 |
| **Repairs Successfully Resolved** | 2 | 2 |
| **Repair Success Rate on Target Defects** | **100.0%** (2 of 2) | Parity on solvable bugs |
| **Overall Suite Resolution Rate** | **40.0%** (2 of 5) | Exact match (3 are non-repairable specifications) |
| **Undetected Regression Rate** | **0.0%** (0 of 1 leaked) | Zero regressions allowed |
| **Regression Adversary Detection** | **100.0%** (1 of 1 caught) | Flagged `p2p_regressed` |
| **Incorrect Diagnosis Rate** | **0.0%** | Zero false-positive repairs |
| **Mean Runtime per Fixture** | **3.59 seconds** | < 10.0s |
| **Median Runtime per Fixture** | **3.52 seconds** | < 10.0s |
| **Total Benchmark Execution Time** | **17.96 seconds** | Fast, reproducible local test |
| **Token Usage & API Cost (Offline Harness)** | 0 tokens / $0.00 | Deterministic offline verification |

---

## 4. Real Provider Test Status

### Status: **BLOCKED (Requires External API Key)**
In the local audit environment, no external AI API keys (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.) are configured. In this mode, PatchBound exercises its local deterministic spine and offline heuristic repair algorithms.

Live repairs using cloud LLMs (Claude 3.7 Sonnet, Gemini 1.5 Pro, GPT-4o) require provisioning a key via:
```bash
patchbound auth set-key anthropic
```
Once provisioned, PatchBound routes repair synthesis through `LLMGateway` while enforcing all pinned oracle, regression checking, and secret egress redaction invariants.

---

## 5. How to Run the Benchmark Locally

The benchmark suite is fully reproducible with a single command:
```bash
uv run pytest tests/integration/test_repair_benchmark.py -v
```
Expected output:
```
tests/integration/test_repair_benchmark.py::test_reproducible_repair_benchmark_suite PASSED [100%]
============================== 1 passed in 17.96s ==============================
```
