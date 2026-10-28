# PatchBound v1.1.0 — Defect Backlog & Remediation Ledger

> **Document:** Phase 2 Defect Backlog, Prioritization, and Remediation Record  
> **Status:** All High-Priority Defects Resolved & Verified  

---

## 1. Prioritization Methodology

Defects are prioritized according to:
$$\text{Priority Score} = \text{Severity} \times \text{Likelihood} \times \text{Scope of Impact}$$

- **P0 (Critical):** Data loss, corruption, security bypass, or total command failure on primary execution paths.
- **P1 (Major):** Broken core functionality, missing contract fulfillment, or unhandled exceptions under documented modes.
- **P2 (Minor):** Non-blocking performance bottleneck, cosmetic inconsistency, or missing optional convenience feature.
- **P3 (Trivial):** Code hygiene, documentation typo, or minor refactoring.

---

## 2. Confirmed Defects & Remediation Record

---

### Defect PP-DEF-01: `git apply` Exit Code 128 on `--apply`
- **Severity:** **P0 (Critical)**
- **Component:** [`patchbound/cli/main.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/cli/main.py#L393)
- **Problem Statement:** When `patchbound repair --apply` attempted to apply a verified patch to the host repository, `subprocess.run(["git", "apply", "-"], ...)` crashed with exit code 128:
  ```text
  error: git diff header lacks filename information when removing 1 leading pathname component at <stdin>:5
  ```
- **Root Cause:** [`patchbound/core/patcher.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/core/patcher.py) generates diffs with `git diff --no-prefix -U3` (producing `--- file.py` instead of `--- a/file.py`). Standard `git apply` defaults to `-p1`, which strips the first pathname component and failed because no component existed.
- **Remediation:** Updated `patchbound/cli/main.py` to dynamically detect patch format and pass `-p0` when diff headers lack `a/` prefixes:
  ```python
  apply_cmd = (
      ["git", "apply", "-p0", "-"]
      if "\n--- a/" not in diff and not diff.startswith("--- a/")
      else ["git", "apply", "-"]
  )
  ```
- **Regression Test:** `test_scenario_1_deterministic_fix_and_cli_apply` in [`tests/integration/test_e2e_scenarios.py`](file:///Users/nitrousoxide/Code/patchbound/tests/integration/test_e2e_scenarios.py).
- **Status:** **VERIFIED & RESOLVED**. Real host repository tests pass with returncode 0.

---

### Defect PP-DEF-02: Absence of Explicit Context Provider Mode Selection (`auto`, `synapse`, `standard`)
- **Severity:** **P1 (Major)**
- **Component:** [`patchbound/config.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/config.py), [`patchbound/graph/nodes/investigator.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/graph/nodes/investigator.py), [`patchbound/cli/main.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/cli/main.py)
- **Problem Statement:** The documentation and roadmap specified support for `auto`, `synapse`, and `standard` context modes, and specified that explicit `synapse` mode must fail if the repository is not indexed by Synapse. However, `_get_context_provider` had no mode argument, did not check settings, and silently fell back to standard mode without error reporting.
- **Root Cause:** Missing configuration field and CLI argument wiring for context selection.
- **Remediation:**
  1. Added `context_mode: str = Field(default="auto")` to `Settings`.
  2. Added `context_mode: str | None` to `PatchBoundState`.
  3. Added `--context-mode` choice option to CLI commands `diagnose`, `repair`, and `run`.
  4. Updated `_get_context_provider(repo_path, mode)` to raise a descriptive `RuntimeError` when explicit `synapse` mode is requested on an unindexed repository.
- **Regression Test:** `test_context_modes_auto_standard_and_explicit_synapse` in [`tests/integration/test_e2e_scenarios.py`](file:///Users/nitrousoxide/Code/patchbound/tests/integration/test_e2e_scenarios.py).
- **Status:** **VERIFIED & RESOLVED**.

---

### Defect PP-DEF-03: Missing Code Context in Investigator Payload and Offline Attempt 0 Heuristics
- **Severity:** **P1 (Major)**
- **Component:** [`patchbound/graph/nodes/investigator.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/graph/nodes/investigator.py), [`patchbound/graph/nodes/fixer.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/graph/nodes/fixer.py)
- **Problem Statement:** `investigator_node` located symbol definition coordinates (`file_path`, `line_start`, `line_end`) but never returned the actual source lines (`code_context`) in state. When `fixer_node` synthesized LLM prompts, it lacked the source lines, forcing the LLM to guess `old_text`. Furthermore, when running offline without API keys, Attempt 0 had no heuristic to propose an initial repair for simple deterministic bugs.
- **Root Cause:** State dictionary omitted `target_file`, `target_symbol`, and `code_context`.
- **Remediation:**
  1. In `investigator_node`, read surrounding lines using `context_provider.read_file` and return `target_file`, `target_symbol`, and `code_context` in state.
  2. In `fixer_node`, embed `code_context` in `user_prompt` for LLMs.
  3. Added Attempt 0 offline heuristic to detect simple arithmetic/boolean mutations in the target symbol lines when running without active API keys.
- **Regression Test:** `test_scenario_1_deterministic_fix_and_cli_apply` in [`tests/integration/test_e2e_scenarios.py`](file:///Users/nitrousoxide/Code/patchbound/tests/integration/test_e2e_scenarios.py).
- **Status:** **VERIFIED & RESOLVED**.

---

### Defect PP-DEF-04: Incomplete AI Provider Key Patterns in Egress Sanitizer
- **Severity:** **P1 (Security)**
- **Component:** [`patchbound/llm/egress.py`](file:///Users/nitrousoxide/Code/patchbound/patchbound/llm/egress.py)
- **Problem Statement:** `EgressGate.SECRET_PATTERNS` only redacted AWS keys, GitHub PATs, and generic bearer tokens. API keys for Anthropic (`sk-ant-...`), OpenAI (`sk-proj-...`, `sk-...`), Gemini (`AIzaSy...`), and DeepSeek (`sk-...`) were not covered, creating a risk of accidental key reflection in logs or prompts.
- **Root Cause:** Incomplete regex patterns in secret denylist.
- **Remediation:** Added dedicated regex patterns for Anthropic, OpenAI, Gemini, and DeepSeek credentials with exact replacement tags (`[REDACTED_ANTHROPIC_KEY]`, `[REDACTED_OPENAI_KEY]`, `[REDACTED_GEMINI_KEY]`, `[REDACTED_DEEPSEEK_KEY]`).
- **Regression Test:** `test_egress_gate_ai_provider_key_redaction` in [`tests/integration/test_e2e_scenarios.py`](file:///Users/nitrousoxide/Code/patchbound/tests/integration/test_e2e_scenarios.py).
- **Status:** **VERIFIED & RESOLVED**.

---

## 3. Residual Feature Backlog (Post-v1.1 Roadmap)

| ID | Title | Priority | Target Milestone | Description |
| :--- | :--- | :--- | :--- | :--- |
| **BACKLOG-01** | Rootless Docker Sandbox Tier | P2 | M2 | Add optional Docker/Podman container runner alongside `LocalTrustedSandbox` for untrusted public code execution. |
| **BACKLOG-02** | Interactive PR Approvals | P2 | M2 | Add CLI prompt during `patchbound gh review` to interactively merge or reject verified PRs. |
| **BACKLOG-03** | Distributed Worker Fleet | P3 | M3 | Implement Celery/Temporal adapter for orchestrating 1,000+ simultaneous repository repairs. |

