# PatchBound v1.1.0 — Manual Test Results & Live Execution Audit

> **Document:** Phase 2 Manual & Live Integration Test Execution Logs  
> **Environment:** macOS 15+ (Darwin aarch64), Python 3.12.13 (CPython), Git 2.39+, Synapse v2.4.1  
> **Date:** October 28, 2026  

---

## 1. Environment & Setup Health Checks

### Test 1.1: System Doctor Diagnostics
- **Command:** `uv run patchbound doctor`
- **Exit Code:** `0`
- **Output:**
  ```text
  ╭──────────────────────────────────────────────────────────────────────╮
  │  PatchBound v1.1  · Deterministic Trust Boundary & Bounded AI Repair │
  ╰──────────────────────────────────────────────────────────────────────╯
  Diagnosing System Environment & Integrations...

                  🩺 PatchBound System Diagnostics & Health Check                 
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ Diagnostic Check           ┃ Status ┃ Details                               ┃
  ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
  │ Python Environment         │  PASS  │ Python 3.12.13                        │
  │ Git Version                │  PASS  │ git version 2.39.5 (Apple Git-154)    │
  │ Synapse AST Engine         │  PASS  │ Installed                             │
  │ Test Framework (Pytest)    │  PASS  │ pytest 9.2.0                          │
  │ Security Policy Config     │  PASS  │ policy.yaml found                     │
  │ Ephemeral Workspace Base   │  PASS  │ /tmp/patchbound-workspaces exists     │
  │ Credential Store (0600)    │  PASS  │ ~/.config/patchbound/credentials.json │
  │ Anthropic API Key          │  WARN  │ Not configured                        │
  │ Gemini API Key             │  WARN  │ Not configured                        │
  │ OpenAI API Key             │  WARN  │ Not configured                        │
  │ DeepSeek API Key           │  WARN  │ Not configured                        │
  │ GitHub API Token           │  WARN  │ Not configured                        │
  └────────────────────────────┴────────┴───────────────────────────────────────┘
  ```
- **Result:** **PASS**. All core primitives and local invariants pass. Missing remote API keys cleanly reported as non-fatal warnings.

---

### Test 1.2: Authentication & Credential Store Inspection
- **Command:** `uv run patchbound auth status`
- **Exit Code:** `0`
- **Output:**
  ```text
                  🔑 PatchBound Authentication & Credential Store                 
  ┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
  ┃ Provider   ┃ Env Variable       ┃  Status   ┃ Source         ┃ Masked Key    ┃
  ┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
  │ Anthropic  │ ANTHROPIC_API_KEY  │  Not Set  │ missing        │ Not set       │
  │ Gemini     │ GEMINI_API_KEY     │  Not Set  │ missing        │ Not set       │
  │ Openai     │ OPENAI_API_KEY     │  Not Set  │ missing        │ Not set       │
  │ Deepseek   │ DEEPSEEK_API_KEY   │  Not Set  │ missing        │ Not set       │
  │ Github     │ GITHUB_TOKEN       │  Not Set  │ missing        │ Not set       │
  └────────────┴────────────────────┴───────────┴────────────────┴───────────────┘
  Credentials file: /Users/nitrousoxide/.config/patchbound/credentials.json (mode 0600)
  ```
- **Result:** **PASS**. Confirmed permissions invariant `0600` and masked output formatting.

---

## 2. Live Synapse Structural AST & FastMCP Integration

### Test 2.1: Live Synapse CLI Inspection
- **Command:** `synap status`
- **Exit Code:** `0`
- **Output:**
  ```text
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            Synap Runtime Status          
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Daemon:            Stopped          
  Repository:        patchbound       
  Branch:            main             
  Indexed:           119              
  Symbols:           326              
  Approved Lessons:  0                
  LLM Provider:      Ollama           
  Model:             qwen2.5-coder:14b
  CPU:               0%               
  RAM:               0.0 MB           
  ```
- **Result:** **PASS**. Real installed `synap` CLI inspected local repository context.

---

### Test 2.2: Live FastMCP Stdio Verification
- **Command:** `synap mcp verify`
- **Exit Code:** `0`
- **Output:**
  ```text
  Synap MCP Verification

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Building Structural Index: main
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Parsing codebase... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01

  ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ Stage              ┃ Status ┃ Latency (ms) ┃ Details                         ┃
  ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
  │ get_status         │ PASS   │ 8.8          │ keys: ['repository_path',       │
  │ verify_system      │ PASS   │ 10.8         │ keys: ['database_integrity',    │
  │ search             │ PASS   │ 23.4         │ keys: ['result', 'context',     │
  │ create_checkpoint  │ PASS   │ 8.3          │ keys: ['status',                │
  │ restore_checkpoint │ PASS   │ 7.3          │ keys: ['checkpoint_id', ...     │
  └────────────────────┴────────┴──────────────┴─────────────────────────────────┘

  ✓ MCP Protocol Verified. All contracts passed.
  ```
- **Result:** **PASS**. FastMCP stdio server verified protocol compliance and low latency (<25ms).

---

### Test 2.3: PatchBound Synapse Integration Status
- **Command:** `uv run patchbound synapse status`
- **Exit Code:** `0`
- **Output:**
  ```text
                     ⚡ Synapse Structural Intelligence Status                   
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ Property                   ┃ Status / Value                                 ┃
  ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
  │ Synapse CLI (`synap`)      │ Installed                                      │
  │                            │ (/Users/nitrousoxide/.local/bin/synap)         │
  │ Database Index             │ Found                                          │
  │ (`.synap/synap.db`)        │ (/Users/nitrousoxide/Code/patchbound/.synap/s… │
  │ Indexed Files              │ 119                                            │
  │ Indexed Symbols (AST)      │ 326                                            │
  │ Call Graph Edges           │ 552                                            │
  └────────────────────────────┴────────────────────────────────────────────────┘
  ```
- **Result:** **PASS**. Synapse index correctly queried via SQLite connection.

---

### Test 2.4: Real AST Symbol Definition Lookup
- **Command:** `uv run patchbound inspect symbols . PinnedOracle`
- **Exit Code:** `0`
- **Output:**
  ```text
  Using provider: SynapseContextProvider
  Found: `PinnedOracle` (class_definition) in patchbound/verification/oracle.py:9-86
  ```
- **Result:** **PASS**. Synapse accurately located `PinnedOracle` definition coordinates.

---

## 3. End-to-End Real Repair Scenarios in Disposable Repositories

### Test 3.1: Scenario 1 & 8 — End-to-End Deterministic Fix & Verified `--apply`
- **Repository Setup:** Disposable git repo in `/tmp/pytest-.../scenario_1_repo` with `calculator.py` (`return a - b`) and failing test `assert add(2, 3) == 5`.
- **Pre-Test Execution:** `pytest -v tests/test_calculator.py` -> **FAILED** (exit code 1).
- **Execution Command:**
  ```bash
  patchbound repair /tmp/.../scenario_1_repo --cmd "pytest -v tests/test_calculator.py" --apply
  ```
- **Exit Code:** `0`
- **Observed Log Snippet:**
  ```text
  [PASS] Level V3_CI_CLEAN achieved
  Applying verified patch to host repository: /tmp/.../scenario_1_repo...
  ✓ Verified patch successfully applied to host repository!
  ```
- **Post-Test Verification:**
  - `git diff` on host repo shows: `- return a - b`, `+ return a + b`.
  - `pytest -v tests/test_calculator.py` executed on host repo -> **PASSED** (exit code 0).
- **Result:** **PASS**. Target bug repaired, verified, and safely applied to host repo.

---

### Test 3.2: Scenario 3 — Zero-Token Early Exit on Non-Reproducible Failure
- **Repository Setup:** Disposable git repo with clean passing test `assert 1 + 1 == 2`.
- **Execution:** `snapshot_reproduce_node` ran test 3 times; all 3 runs passed (0 failures).
- **Observed State:**
  - `reproduce_classification = "not_reproducible"`
  - `status = ProcessStatus.TERMINATED`
  - `outcome = OutcomeResult.NOT_REPRODUCIBLE`
  - Zero tokens spent; `canonical_diff` was never generated.
- **Result:** **PASS**. Deterministic reproduction gate prevented wasteful token burn.

---

### Test 3.3: Scenario 4 — Rejection of Patch Causing Pass-to-Pass (P2P) Regression
- **Repository Setup:** Disposable git repo with two passing tests (`calc(5) == 5`, `calc(8) == 8`) and one failing target test (`calc(10) == 10`).
- **Proposed Patch:** Replaced function with `return 10`, which fixes the target test but breaks the two passing tests.
- **Verification Execution:**
  - `VerificationEvaluator.evaluate` detected 2 regressed tests in `p2p_regressed`.
  - Scored `level = VerificationLevel.V0_FAILED`.
  - Emitted `failure_delta.delta_type = "REGRESSION"`.
  - Host repository remained 100% untouched.
- **Result:** **PASS**. Regressive patch rejected deterministically.

---

### Test 3.4: Scenario 5 — Test Oracle Tampering Rejection
- **Repository Setup:** Disposable git repo where patch attempted to add `@pytest.mark.skip` to `tests/test_calc.py`.
- **Verification Execution:**
  - `PinnedOracle.verify_no_test_diffs()` detected test modification.
  - Automatically ran `git checkout -- tests/` and raised `PolicyViolation`.
  - Recorded `failure_delta.delta_type = "POLICY_OR_APPLICATION_ERROR"`.
- **Result:** **PASS**. Oracle tampering thwarted; test suite restored to baseline hash.

---

### Test 3.5: Scenario 6 — Ambiguous / Non-Existent Anchor Rejection
- **Repository Setup:** Disposable git repo where patch provided an `old_text` snippet that does not exist in target file.
- **Verification Execution:**
  - `Patcher.apply_edits` raised `PatchApplicationError("Anchor not found in service.py...")`.
  - Caught cleanly in `patch_verify_node`, incremented attempt, and returned guidance.
  - Host repository remained untouched.
- **Result:** **PASS**. Clean error propagation and failure delta recovery.

---

## 4. Test Suite Execution & Strict Analysis

### Test 4.1: Complete Pytest Suite
- **Command:** `uv run pytest -v`
- **Exit Code:** `0`
- **Output:**
  ```text
  ============================= 73 passed in 36.41s ==============================
  ```
- **Result:** **PASS**. All 73 tests green across unit and integration suites.

---

### Test 4.2: Strict Static Type Checking (Mypy)
- **Command:** `uv run mypy patchbound tests`
- **Exit Code:** `0`
- **Output:**
  ```text
  Success: no issues found in 94 source files
  ```
- **Result:** **PASS**. 100% strict type safety across all 94 files.

---

### Test 4.3: Ruff Linting & Formatting
- **Command:** `uv run ruff check .`
- **Exit Code:** `0`
- **Output:**
  ```text
  All checks passed!
  ```
- **Result:** **PASS**. 100% compliant with PEP 8 and modern Python conventions.

---

### Test 4.4: Wheel & Source Packaging Build
- **Command:** `uv build`
- **Exit Code:** `0`
- **Output:**
  ```text
  Successfully built dist/patchbound-1.1.0.tar.gz
  Successfully built dist/patchbound-1.1.0-py3-none-any.whl
  ```
- **Result:** **PASS**. Distribution packages successfully compiled and ready for deployment.

