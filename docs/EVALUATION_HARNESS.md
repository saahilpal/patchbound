# PatchProof v1.1 Evaluation Harness & Benchmark Suite

> **Document:** Evaluation Methodology, Statistical Protocol & Benchmarks  
> **Status:** Active Standard

---

## 1. Evaluation Methodology

PatchProof tests every architectural claim against empirical benchmarks. We reject vanity metrics like "raw fix rate without verification" and focus on **safety**, **calibration**, and **cost-efficiency**.

### Core Falsifiable Hypotheses

| Hypothesis | Test Formulation | Validation Metric | Target |
| :--- | :--- | :--- | :--- |
| **H1: Single-Agent Spine Superiority** | A deterministic spine with a single agent loop (Investigator) outperforms a 7-agent pipeline in cost and latency while matching or exceeding resolution rate. | Cost per fix ($), Wall-clock latency (s), Resolved rate (%). | $\ge 40\%$ cost reduction, $\ge 50\%$ latency reduction at parity accuracy. |
| **H2: Causal Experiments Inhibit Regressions** | Patches supported by interventional experiments produce fewer regressions (P2P breaks) than patches derived purely from ungrounded prompt explanations. | Regression rate on Pass-to-Pass (P2P) suite. | $\ge 30\%$ reduction in P2P regressions. |
| **H3: Zero False-Verified Rate** | The Pinned Oracle and Level V1-V3 evaluator eliminate false-positive "fixes" that pass by modifying tests or gaming exit codes. | False-Verified Rate ($FVR$) on held-out test suite. | $\mathbf{FVR < 1.0\%}$ (ideally $0\%$). |
| **H4: Synapse Graph Context Advantage** | Synapse structural code graph provider improves first-pass repair rate over standard grep/AST primitives on multi-file dependencies. | First-pass V2 verification rate on multi-file bug fixtures. | Statistically significant gain ($p < 0.05$) in multi-file bug resolution. |

---

## 2. Benchmark Datasets & Fixture Mix

To combat LLM training-data contamination (where models memorize solutions to known GitHub issues), PatchProof employs a balanced, multi-tier benchmark suite:

```
+-------------------------------------------------------------------------+
| BENCHMARK SUITE COMPOSITION                                              |
|                                                                         |
| 1. Synthetic Private Injections (40%):                                  |
|    - Mutations and fault injections in proprietary/private repositories |
|    - Zero risk of LLM pretraining contamination                         |
|    - Real-world dependency graphs & private test suites                 |
|                                                                         |
| 2. GitBug-Actions & BugSwarm (35%):                                     |
|    - Mined real-world CI failure commits with reproducible F2P/P2P tests|
|    - Diverse ecosystem: Python (pytest) and TypeScript (jest/vitest)    |
|                                                                         |
| 3. SWE-bench Lite Curated Subset (25%):                                 |
|    - Established industry baseline for comparison against Agentless,    |
|      SWE-agent, and Devin architectures.                                |
+-------------------------------------------------------------------------+
```

---

## 3. Statistical Protocol & Experimental Controls

1. **Paired Arm Testing:** When comparing configurations (e.g., `Standard Context` vs `Synapse Context`, or `Prompted Repair` vs `Interventional Repair`), each fixture is evaluated across both arms on the exact same commit and environment seed.
2. **Triplicate Runs:** Every test case is executed at least $N = 3$ times per arm to account for LLM stochasticity and test flakiness.
3. **Reported Intervals:** All metrics are reported with $95\%$ bootstrap confidence intervals.
4. **Held-Out Test Oracles:** The evaluation harness maintains a secret, held-out test suite $T_{\text{held}}$ for each fixture. The candidate patch must pass $T_{\text{held}}$ without ever having had access to its code or error messages during the investigation or repair stages.
