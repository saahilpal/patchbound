# PatchBound: Engineering Audit

**Audit date:** 2026-11-01  
**Method:** Source inspection, repository-wide call-site searches, local lint/type/test execution, and targeted temporary-repository reproductions. No implementation edits were made. No live model or GitHub API calls, production deployment, or malicious-code exploit tests were performed.

## 1. System as implemented

The repository is a single Python package and CLI. It is not deployed as microservices. The codebase contains a LangGraph workflow, CLI/setup and GitHub adapters, a local subprocess runner, Git clone/patch/policy utilities, test parsers/evaluation, context providers, model gateway, reporting/audit code, and a synthetic evaluation package. There are roughly 8,500 Python lines across package and tests. `patchbound/cli/main.py` is roughly 900 lines and mixes command parsing, orchestration, reporting, and GitHub side effects.

The intended flow is visible in `patchbound/graph/workflow.py` and `docs/architecture/overview.md`: snapshot/reproduce → triage → repairability gate → investigate → fix → verify → review → approval → export. The implementation uses LangGraph but does not need distributed execution or durable external state for this local, short-lived workflow. The core graph is a deterministic sequence with bounded retries; a plain Python coordinator would be easier to inspect and test.

## 2. Verified findings

### ENG-01 — Critical — Verification can issue a false “V3 / CI clean” result

**Observed:** `VerificationRunner.run_tests` passes only stdout/stderr to the parser and discards `ExecutionResult.exit_code` and `timed_out` (`patchbound/verification/runner.py:19-35`). The stdout parser can return zero executed/failed for an unrecognized command result (`patchbound/verification/parsers/pytest_parser.py:57-108`). `patch_verify_node` reruns only `reproduce_cmd`, hardcodes `impacted_test_ids=set()`, and sets flake/pinned/policy flags to true (`patchbound/graph/nodes/patch_verify.py:57-82`). `VerificationEvaluator` calls the result `V3_CI_CLEAN` when the parsed report has zero failures; it has no evidence that the command covered CI (`patchbound/verification/levels.py:48-57`).

**Reproduction:** In a disposable temporary Git repo, the configured command selected and ran a target test that passed after the candidate patch. A separate unrelated test failed. PatchBound returned `V3_CI_CLEAN`; running the full suite in the patched workspace returned exit 1 with one failure and one pass. Separately, `/usr/bin/false` yielded subprocess exit code 1 but a parsed report of zero executed and zero failed. The snapshot node then classifies three such reports as `not_reproducible` because it classifies only from parsed failure counts (`patchbound/graph/nodes/snapshot_reproduce.py:23-49`).

**Why it matters:** The central trust signal can be false while the product exports, approves, or opens a PR. This invalidates the V3 label and can hide regressions or infrastructure failures.

**Recommended action:** Preserve exit code, timeout, signal, command, and output. Treat nonzero/unparseable runs as failed or inconclusive, never clean. Record the exact test scope. Only issue a full-suite/CI result when an explicitly configured full command ran successfully. Run each baseline repetition from an identical clean state. Until corrected, disable V3 wording and prevent any side effect from relying on it.

**Expected impact:** Removes false-clean approvals and makes test evidence auditable. It will likely turn some apparent successes into “inconclusive,” which is correct but reduces success rate.

**Confidence:** High; directly reproduced.

### ENG-02 — High — The “sandbox” does not isolate repository code

**Observed:** `LocalTrustedSandbox.execute` invokes `subprocess.run` with a workspace cwd, a timeout, and a partly scrubbed environment (`patchbound/core/sandbox.py:68-115`). It retains the inherited `PATH` (`:82-91`) and imposes no OS-level filesystem boundary, network block, CPU/memory limits, process-tree supervision, or output-size limit. The abstract interface docstring promises “isolated, no network, rlimits” (`:26-34`), but the concrete implementation does not provide those properties. `sandbox_tier` is configuration metadata and does not choose an alternate runner (`patchbound/config.py:53-60`). The `prepare` docstring says scripts are disabled, but it simply invokes the supplied install command (`patchbound/core/sandbox.py:40-66`).

**Why it matters:** Repository tests and build steps execute code. A malicious or compromised test/dependency can access files available to the user, contact the network, consume host resources, or leave child processes running. Setting `HOME` to the workspace does not prevent absolute-path reads or network access.

**Recommended action:** Do not call this a security sandbox. Either restrict the product to repositories the operator explicitly trusts, or execute untrusted code in an OS-enforced boundary (for example, a disposable VM or a hardened container with no host secrets, constrained mounts/network/resources, and process cleanup). Make installation and test phases separate policies. Validate the chosen boundary on each supported OS.

**Expected impact:** Honest threat model and materially lower host exposure for untrusted repositories. This adds operational complexity; it is justified only if untrusted repo execution is a core use case.

**Verification method:** Static inspection of runner and config; no hostile payload was run. Risk severity is based on the executed command’s permissions and missing controls.

**Confidence:** High for the missing controls; high for the resulting risk, not an exploit demonstration.

**Verification:** Static inspection of `LocalTrustedSandbox`, `sandbox_tier`, and the runner interface. No hostile code was run.

### ENG-03 — High — Approval is automatic by default and has no human event

**Observed:** Repair CLI `--auto-approve` defaults to true (`patchbound/cli/main.py:420-427`) and config defaults true (`patchbound/config.py:61-63`). `human_approval_node` reads a boolean or falls back to that default and computes `SHA256("APPROVED:<patch>:<verification>:v1.1")` (`patchbound/graph/nodes/human_approval.py:17-37`). This digest is not keyed and is generated by the application; it does not establish who approved anything. `gh solve` sets `auto_approve=True` and `--auto-pr` defaults true (`patchbound/cli/main.py:580-583, 637-645`), then pushes a branch and opens a PR on a successful outcome (`:658-691`). There is no interactive pause/approval UI in this node. `--no-auto-approve` rejects instead of waiting for a human.

**Why it matters:** “Human approved” and “cryptographic approval” are false descriptions. The GitHub path can create an external side effect based on an automatically generated approval token and the faulty verifier in ENG-01.

**Recommended action:** Change approval semantics to an explicit user review of the exact final diff and evidence. Default to no side effects. Bind an approval record to patch digest, evidence digest, policy version, reviewer identity, and timestamp using an authenticated source if a signature is required. Disable auto-PR until verification is reliable.

**Expected impact:** Makes the governance boundary real and prevents surprising PR creation. Any existing automation depending on defaults will need explicit opt-in migration.

**Confidence:** High; source inspected.

**Verification:** Inspected Click/config defaults and the approval node; no interactive prompt or approval interrupt is present in that node.

### ENG-04 — High — The investigation and independent reviewer are mostly heuristics, but named as AI/causal stages

**Observed:** `investigator_node` derives candidate symbols from test IDs/failure text, reads source context, and constructs a hypothesis string; inferred claims are assigned confidence without an interventional experiment (`patchbound/graph/nodes/investigator.py`, especially hypothesis/claim construction near lines 145-215). The `ExperimentRunner` class exists but repository-wide search finds no workflow call site (`patchbound/ledger/experiment.py:27-67`). `review_node` runs deterministic policy, secret-pattern, and anti-cheat checks (`patchbound/graph/nodes/review.py:13-63`); it does not call an independent model. `LLMGateway.synthesize_review` has no pipeline caller. `parse_triage.py` contains a `pass` at the promised fallback location (`patchbound/graph/nodes/parse_triage.py:9-24`).

**Why it matters:** Users and maintainers may infer that causal experiments corroborate hypotheses or a blind reviewer independently evaluates semantic correctness. Neither is part of the connected path. Deterministic policy checks can catch specified patterns; they do not determine whether the code change is correct.

**Recommended action:** Rename and document the actual behaviors, or remove the unused experiment/reviewer abstractions. Keep deterministic checks as one gate, and do not describe them as semantic review. Add model review only if real evaluations show measurable value beyond tests and a human diff review.

**Expected impact:** Reduces conceptual surface and misleading assurance. Existing docs/API consumers relying on these labels may need a major-version correction.

**Confidence:** High for call paths; medium-high for the product impact.

**Verification:** Inspected the investigator, review, triage, and experiment modules, then searched repository call sites for experiment and reviewer gateway methods.

### ENG-05 — Medium — The claim ledger and experiment machinery do not provide the promised evidence chain

**Observed:** `ClaimItem` is a typed Pydantic model (`patchbound/ledger/claim.py:1-36`). The experiment runner is uncalled (ENG-04). The export path records one pipeline-termination event and a summary rather than an event for each claim/evidence transition (`patchbound/graph/nodes/export_report.py:49-62`). A separate audit journal hash chain can reveal accidental/after-the-fact changes to its file, but without an external key or anchor it does not authenticate the author or prevent a privileged writer from rewriting the chain.

**Why it matters:** “Cryptographic claim ledger” implies provenance and tamper resistance stronger than the current record provides. It adds data models and documentation burden without a connected evidence lifecycle.

**Recommended action:** Remove the claim-ledger branding and unused ledger abstractions. Preserve a simple JSON report with patch hash, exact commands, exit statuses, test scope, policy version, and timestamps. Add externally anchored signatures only if a buyer needs them.

**Expected impact:** Less code and clearer output. Consumers of claim-specific report fields would need a migration if this API has external users; no such usage is evidenced in this repository.

**Confidence:** High for code shape; medium for downstream compatibility because external consumers are unknown.

**Verification:** Inspected the claim model and export node, and searched for claim/experiment persistence paths. No external consumer analysis was available.

### ENG-06 — High — Default model identifiers are retired

**Observed:** Tracked defaults configure Gemini 1.5 Flash/Pro (`patchbound/config.py:32-41`); `.env.example` configures older Claude 3.7/3.5 model names. The gateway routes Anthropic defaults to `claude-3-7-sonnet-20250219` and hardcodes Gemini 1.5 Pro in the strong-model path (`patchbound/llm/gateway.py:79-88, 135-138`).

**Provider evidence:** Anthropic’s [model deprecations page](https://docs.anthropic.com/en/docs/about-claude/model-deprecations) lists Claude 3.7 Sonnet as retired on 2026-02-19. Google’s [Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog) records Gemini 1.5 Pro/Flash shutdown on 2025-09-29. Pages checked 2026-11-01.

**Why it matters:** A new installation’s configured provider path is likely to fail before producing a patch. This is especially damaging because provider setup is core to the advertised repair use case.

**Recommended action:** Remove retired IDs, avoid hardcoded model routing, validate configured models at startup, and keep a small provider compatibility test that does not require live credentials. Do not claim live provider support until a smoke test with current models runs.

**Expected impact:** Restores the possibility of current provider use, subject to keys and provider API behavior. No live API call was made during this audit.

**Confidence:** High for tracked identifiers and official retirement dates; live gateway operation remains unverified.

**Verification:** Compared tracked defaults and gateway routing to the linked official provider deprecation pages, checked 2026-11-01. No live API request was made.

### ENG-07 — Medium — Advertised policy fields are silently ignored

**Observed:** `policy.yaml` declares fields such as `max_hunks_per_file`, `allowed_commands`, and budgets. `PolicyConfig` defines only version/id, `scope`, and `forbidden_patterns` (`patchbound/core/policy.py:11-56`); checks enforce diff bytes, file count, protected paths, and forbidden added-line patterns (`:109-136`). Pydantic’s default extra-field behavior permits unknown keys to be ignored. `GuardrailEngine.run_inflight` and `run_postflight` are implemented but have no graph/CLI call sites; only preflight is invoked. Token-budget config is not a total per-run accounting mechanism.

**Why it matters:** Users can edit policy thinking commands/hunks/budgets are constrained when those settings do nothing. This creates a false configuration boundary.

**Recommended action:** Use a strict schema that rejects unknown keys. Implement only the settings the product truly needs; delete the rest from the YAML and docs. Enforce command allowlisting only if it fits a clear threat model; otherwise state that commands are user-trusted inputs.

**Expected impact:** Invalid configuration fails loudly; less policy ambiguity. Existing configs with ignored keys will need correction.

**Confidence:** High; source/config comparison and call-site search.

**Verification:** Compared `policy.yaml` keys with `PolicyConfig` fields and `check_diff` enforcement; searched the repository for inflight/postflight call sites.

### ENG-08 — Medium — Temporary checkout lifecycle can collide and leave scratch data behind

**Observed:** CLI investigation IDs derive from repository basename; GitHub IDs derive from issue number (`patchbound/cli/main.py:453-461, 637-645`). `CloneManager.create_disposable_clone` removes an existing target directory before cloning (`patchbound/core/clone.py:69-90`). A cleanup method exists (`:92-99`) but repository-wide search finds no workflow caller. The snapshot records pre-run state but the workflow does not call `verify_host_invariants`; the captured fingerprint also covers HEAD/refs/status text, not untracked file contents (`patchbound/core/clone.py:18-58`).

**Why it matters:** Two runs for the same repository name/issue can delete or reuse the same workspace; concurrent processes can interfere. Scratch data can accumulate. Host-integrity claims exceed what is checked.

**Recommended action:** Create a unique per-run directory with restrictive permissions and an ownership marker; never delete a directory merely because another run chose the same identifier. Ensure cleanup in `finally`, with an opt-in retention mode. Either verify host state after the run or remove the assertion that it is protected.

**Expected impact:** Fewer concurrency failures and less data retention. A retention option is useful for debugging but must not be the default.

**Confidence:** High for the path/lifecycle behavior; no concurrent collision was stress-tested.

**Verification:** Inspected clone path generation/deletion and searched workflow call sites for `cleanup_attempt` and `verify_host_invariants`.

### ENG-09 — Medium — CLI failure semantics and command parsing are unreliable

**Observed:** CLI string commands are split with `str.split()` (`patchbound/cli/main.py:455-461, 637-645`), which loses shell-style quoting. The `VerificationRunner` ignores process status (ENG-01). Several CLI error paths print a message and return rather than providing a nonzero exit status. `setup` accepts `--init-policy` and `--init-env` but the values do not control whether files are initialized (`patchbound/cli/main.py:44-55`). `doctor` marks `uv` required despite pip being an available install workflow (`patchbound/cli/setup.py:99-108`).

**Why it matters:** Users can run a different command than intended, scripts cannot reliably detect failure, and options do not behave as their names suggest.

**Recommended action:** Accept argv as a repeatable/list option or parse with `shlex` and document no shell expansion. Preserve command as an evidence field. Set explicit CLI exit codes for errors and unsuccessful outcomes. Remove dead options or implement their stated behavior.

**Expected impact:** More predictable local and CI use with minimal architecture cost.

**Confidence:** High; source inspection.

**Verification:** Inspected Click argument construction, setup option usage, and doctor checks.

### ENG-10 — Medium — Tests depend on an external sibling checkout and can write outside the repository

**Observed:** `tests/unit/test_synapse_context.py:11-17, 36-42` hardcodes `/Users/nitrousoxide/Code/synapse`. On this host, the test reaches the Synapse index and symbol checks, then invokes its status CLI; that CLI attempts to append to `/Users/nitrousoxide/Code/synapse/.synap/logs/daemon.log` and raises `PermissionError` in the managed workspace. The integration test is marked skipped only when that exact absolute path is absent.

**Why it matters:** Test outcome depends on one developer’s filesystem and neighboring project version; executing a unit test may mutate another repository. CI on Linux will skip it and therefore does not validate the advertised live integration.

**Recommended action:** Unit-test against a temporary fixture or a mocked subprocess. Keep a separately marked integration test that takes an explicit path and is opt-in. Ensure it writes only under a temporary test root.

**Expected impact:** Portable tests and no accidental sibling-repository writes.

**Confidence:** High; locally reproduced failure and traceback.

**Verification:** Ran the full local pytest suite with `.venv/bin` on `PATH`; this test failed after the external status command attempted the sibling-repository log write.

### ENG-11 — Medium — GitHub feature names exceed actual issue/PR behavior

**Observed:** `gh solve` fetches the issue and uses its reproduction hint, but the state passed to the repair graph contains repository path and test command, not the issue title/body (`patchbound/cli/main.py:606-647`). It can open a PR by default (`:580-583, 658-691`). `gh review` checks out a pull request head and runs the configured pipeline but does not inspect base-to-head changes or submit a review (`:701-755`). GitHub client tests patch subprocess rather than exercise a live API (`tests/unit/test_github_client.py`).

**Why it matters:** A command called “solve” may not understand the issue request; a command called “review” does not deliver a review. The automated PR makes this mismatch consequential.

**Recommended action:** Remove or rename these commands until their output matches their names. If retained, make issue intent explicit input, compare base/head, and require human review before publishing. Test GitHub behavior against an isolated test repository or API contract fixture.

**Expected impact:** User expectations align with actual output; avoids unreviewed or irrelevant PRs.

**Confidence:** High for local call path; live GitHub behavior not exercised.

**Verification:** Inspected CLI state construction and GitHub call sites; inspected `tests/unit/test_github_client.py`, which mocks subprocess rather than contacting GitHub.

### ENG-12 — Medium — Evaluation evidence does not establish real repair quality

**Observed:** `tests/integration/test_repair_benchmark.py` exercises five synthetic fixtures. Some supply a candidate patch directly; two represent repairable arithmetic cases. The reported 100% result is over two repairable fixtures, not general model repair quality. The mutator performs textual substitutions rather than AST-aware mutations (`patchbound/eval/mutator.py:13-44`). `BenchmarkRunner` passes an arm name only into the summary and does not implement distinct algorithms (`patchbound/eval/runner.py:17-71`). `EvalFixture.base_commit` is not used by the runner (`patchbound/eval/datasets.py:9-21, runner.py:26-36`). Cost/token figures are constants rather than provider measurements (`runner.py:53-62`).

**Why it matters:** The benchmark cannot support claims of broad accuracy, regression resistance, latency, or cost. Small fixtures bias toward the built-in heuristic and hardcoded outcomes.

**Recommended action:** Delete public performance claims. If product validation continues, create a versioned set of real issue/repo tasks with frozen commits, reproducible commands, baseline policies, blinded scoring, and actual cost/time capture. Compare against simpler workflows and a no-model baseline.

**Expected impact:** Makes investment decisions evidence-based; likely reveals much lower general repair coverage than synthetic tests suggest.

**Confidence:** High for harness behavior; external benchmark validity beyond this repository is unknown.

**Verification:** Inspected fixture definitions, runner arm handling, base-commit use, mutator implementation, and fixed cost/token fields. Ran the benchmark test with the project virtualenv on `PATH`.

### DOC-01 — High — Historical verification reports assert features that source does not implement

**Observed:** `docs/audits/feature-verification-matrix.md:5` says “All Features Verified.” Its rows claim V3 is a full CI suite (`:22`), claim a cryptographic claim-ledger module at `patchbound/ledger/claim_ledger.py` (`:24`, file absent), and claim an autonomous GitHub issue solver at `patchbound/github/issue_solver.py` (`:29`, file absent). The GitHub row says mocked HTTP endpoints, while the checked-in client tests mock subprocess. Other docs also describe no-network execution, a human approval gate, and an independent blind reviewer more strongly than the connected code supports.

**Why it matters:** Future maintainers and users can treat unimplemented or false assurance as verified behavior, making operational and product decisions on inaccurate evidence.

**Recommended action:** Mark prior audit reports historical and invalidated, preserve useful reproduction notes, and replace them with claims tied to present code paths and reproducible tests. Remove absolute links to a different checkout.

**Expected impact:** Lowers false confidence and prevents stale audit output from being reused as release evidence. Historical bug context remains available if archived with a warning.

**Verification:** Read the feature matrix and confirmed the referenced `claim_ledger.py` and `issue_solver.py` files are absent from `patchbound/`; compared reported features against actual call sites.

**Confidence:** High.

## 3. Architecture, data flow, and boundaries

### 3.1 Major functionality status

No major end-to-end feature was fully verified end-to-end during this audit. The status below describes source inspection and local checks; it does not claim a production test. Some low-level utilities have passing unit coverage.

| Major feature | Status | Evidence / limitation |
|---|---|---|
| Anchored patch application and diff generation | Working with limitations | Used by the synthetic repair path and exercised by unit/integration suite; exact patch correctness is not implied. |
| Local policy checks | Working with limitations | Enforces a subset of diff/path/pattern rules; advertised command/hunk/budget keys are not enforced (ENG-07). |
| Test execution result handling | Broken | `/usr/bin/false` retained process exit 1 but produced a zero-failure/zero-executed report (ENG-01). |
| Full CI / V3 assurance | Broken | Direct targeted-command reproduction returned V3 while an unrelated full-suite test failed (ENG-01). |
| Offline repair | Working with limitations | A narrow arithmetic heuristic is exercised by synthetic fixtures; it is not general code repair. |
| Live model repair | Cannot verify | No current provider call was made; configured defaults are retired (ENG-06). |
| “Record/live” LLM replay | Mocked or simulated | Recorder returns literal placeholder responses in those modes (`patchbound/llm/recorder.py:28-44`); it is not connected to provider execution. |
| Human approval | Broken | Approval defaults true and generates an unkeyed digest without human input (ENG-03). |
| Blind semantic review | Not implemented | Connected node performs deterministic pattern/policy checks only (ENG-04). |
| Causal experiment support | Not implemented in workflow | Runner class exists but has no pipeline call site (ENG-04). |
| GitHub issue-to-PR | Partially implemented; live behavior cannot verify | Issue fetch/clone/branch/PR code exists; issue text is not repair context and live GitHub was not exercised (ENG-11). |
| GitHub PR review | Not implemented as a review | Current path runs tests on a ref but does not review base/head diff or post a review (ENG-11). |
| Synapse context | Partially implemented | Synthetic SQLite test exists; machine integration test depends on a sibling checkout and failed during status call (ENG-10). |
| Experiment benchmark | Partially implemented | Synthetic cases run, but arms and cost/performance data do not represent a controlled real-repository evaluation (ENG-12). |
| Telemetry pipeline | Not implemented end-to-end | Dependencies/helper exist, but no connected export pipeline was found. |

### System boundaries

- **CLI:** one local process; no stable remote service API was found.
- **Orchestration:** LangGraph state graph and module-level/global settings.
- **Storage:** local Git clones, report/diff files, optional JSONL audit journal; no required database or durable run service.
- **Model boundary:** provider gateway, but provider versions are stale and the recorder is not a real replay backend.
- **Execution boundary:** local subprocess with user privileges; it is not a sandbox.
- **GitHub boundary:** GitHub CLI/subprocess integration plus branch/PR operations. External behavior was not live-tested.
- **Optional context:** standard local parsing and Synapse index integration.

### Dependency direction and cohesion

The package is modular by folder but the CLI is too large and reaches across configuration, graph, GitHub, reporting, and presentation. Several nodes instantiate concrete services directly and read global settings, which makes isolated testing and per-run configuration harder. There is no meaningful microservice architecture to preserve. A smaller coordinator with explicit dependencies is more appropriate.

### Concurrency and persistence

There is no durable job queue or cross-process coordination. That is acceptable for a local CLI if each run uses unique scratch directories. Current deterministic names and delete-before-create semantics make concurrent runs unsafe. State is in process; recovery after a crash is limited to leftover scratch directories and report files. No distributed persistence is justified by current product scope.

### Performance

No credible performance benchmark exists. Reproduction runs the same command three times; patch verification runs it again; retries can rerun it. Git local clone is used, but clone, suite duration, memory, disk, provider latency, and token usage were not measured. `subprocess.run(capture_output=True)` buffers all output in memory; there is no output cap. Timeouts are configured per command but do not establish total wall-clock or resource bounds. Any performance conclusion beyond these code observations is unknown.

## 4. Security audit

### Verified weaknesses

- **Execution of repository code:** no OS sandbox, network restriction, resource limits, process-tree cleanup, or output cap (ENG-02).
- **Approval bypass by default:** automatic approval and auto-PR defaults (ENG-03).
- **Command scope:** user-supplied command is executable; `policy.yaml` allowed-command settings are not enforced (ENG-07). CLI uses argv rather than shell execution at the runner, which lowers shell metacharacter injection risk, but does not make the selected executable safe.
- **Verification bypass:** false-clean V3 can pass downstream review/export (ENG-01).
- **Secrets:** environment removes most variables but preserves inherited PATH; the execution model is not a security boundary. Secret-pattern scanning of patch text does not protect host credentials from arbitrary test code.
- **Credential store:** `patchbound/core/credentials.py:51-62` writes the key file then applies mode 0600; this is not atomic and has no symlink-safe open. CLI `set-key` accepts a secret as an argument, which may be captured in shell history/process listings. No credential attack was executed.
- **Path checks:** clone IDs receive a containment check, which is useful, but deterministic scratch names and deletion behavior still create collision risks. Patch edit path validation must remain a separately tested boundary.

### Not established

No dependency vulnerability scan was run. No hostile repository or dependency was executed. No external security review was found. The existing adversarial tests exercise application rules, not OS isolation. Therefore this audit does not certify that the package is secure or production-ready.

## 5. Reliability and failure handling

- Test exit code and timeout are dropped before verification (ENG-01).
- Parse uncertainty is converted to zero counts rather than “unknown.”
- Timeout captures output but does not provide process-tree cleanup; child-process behavior was not tested.
- Reproduction runs share one workspace, so stateful tests may contaminate later repetitions (`snapshot_reproduce.py:23-35`).
- Clone cleanup is defined but not used; concurrent runs can delete each other’s directory (ENG-08).
- Graph nodes catch broad exceptions and may turn them into a generic retry delta. This keeps the graph moving but can obscure root cause.
- CLI returns are not consistently mapped to nonzero shell status (ENG-09).
- No durable run checkpoint or crash recovery is needed for a small CLI, but leftover clones should be handled safely.

## 6. Developer experience

The top-level purpose is understandable from the README, but the assurance vocabulary obscures what happens. Installation and setup guide one coherent CLI, while the docs expose model, policy, context, Synapse, GitHub, evidence, and future “stage” options that are not consistently wired. The configuration guide includes fields absent from the schema. `setup --init-policy/--init-env` does not honor those controls. The machine-specific Synapse test and stale provider IDs make first-run behavior less predictable.

Most damaging DX issue is not missing polish: it is output that overstates confidence. Developers cannot trust “V3 CI clean,” “human approved,” or “review passed” without understanding internal implementation details.

## 7. Dependencies and repository hygiene

`pyproject.toml` includes `pydantic`, `pydantic-settings`, `langgraph`, `langchain-core`, Click, Rich, OpenTelemetry API/SDK, PyYAML, `junitparser`, GitPython, and httpx. Source search shows:

- `xml.etree.ElementTree` is used for JUnit parsing; `junitparser` appears unused.
- Git operations use subprocess; GitPython appears unused.
- OpenTelemetry SDK is declared but the API use is limited to an unconnected helper; no end-to-end telemetry pipeline was found.
- `langchain-core` is not directly imported by application code; determine whether it must remain direct based on intended extension API before removing.
- `LLMRecorder` `record` and `live` modes return placeholder strings (`patchbound/llm/recorder.py:28-45`) and are not wired into the gateway. It is not a usable replay system.

Remove a dependency only after confirming it is not part of a published extension contract. The clearest candidates are unused direct dependencies and unused telemetry scaffolding; the consequence is breaking consumers that import an undocumented transitive package through PatchBound, so make any removal a deliberate major/minor packaging choice.

## 8. Documentation and operational workflows

The docs contain multiple architecture/product descriptions and historical audit reports. `docs/audits/feature-verification-matrix.md` labels all features verified, cites a nonexistent `patchbound/github/issue_solver.py`, and describes a broader feature set than code connects. Other audit docs similarly use strong verification claims. Some contain absolute `file:///Users/nitrousoxide/Code/patchbound/...` links that point at a different checkout name. The README/PRD describe no-network execution, rlimits, human approval, a blind reviewer, full V3 suite, and cryptographic ledger more strongly than source supports.

CI is a GitHub Actions workflow on Ubuntu with Python 3.11 and 3.12, Ruff, mypy, pytest, and package smoke checks (`.github/workflows/ci.yml`). This is a reasonable baseline. No macOS or Windows job exists despite “OS Independent” package metadata. CI relies on `uv ... latest`, which makes the toolchain less reproducible. The workflow does not validate live provider/GitHub integration, and the Synapse integration test is skipped on standard Linux.

## 9. Local quality results

| Check | Result | Limit |
|---|---|---|
| Ruff | Passed | Static lint only. |
| Mypy | Passed, 96 source files | Type consistency does not validate product semantics. |
| Pytest, corrected PATH | 79 passed, 1 failed | Failed hard-coded Synapse integration due external log write; see ENG-10. |
| Benchmark test with `.venv/bin` on PATH | Passed | Synthetic fixtures; does not establish real repair quality. |
| Full GitHub Actions workflow | Not run | Local environment is not CI matrix. |
| Live LLM and GitHub | Not run | Credentials/provider/repository behavior remains unverified. |

## 10. Overall engineering decision

This is not a case where small refactoring would fix an otherwise sound assurance product. The core contracts—execution isolation, test result semantics, approval, and verification scope—are either absent or incorrect. A small but honest patch-proposal tool could be rebuilt from a subset of the current code, but continuing the full architecture would preserve misleading boundaries and waste effort. See [TARGET_ARCHITECTURE.md](TARGET_ARCHITECTURE.md) for the smallest plausible replacement and [ROADMAP.md](ROADMAP.md) for contingent work only.
