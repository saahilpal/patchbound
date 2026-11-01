# PatchBound: Decision-Gated Roadmap

**Primary recommendation remains G — ABANDON the standalone product.** This is a closure and validation plan, not a commitment to build the target architecture. Effort estimates are rough engineer-week estimates for one experienced engineer; they are not measured. Do not start P1+ implementation unless product discovery produces a named adopter and a concrete repository workflow.

## P0 — Correct unsafe or misleading behavior before any further use

| Work | Estimate | Dependencies | Exit condition |
|---|---:|---|---|
| Stop using or advertising “V3 / CI clean,” “sandbox,” “human approved,” “blind reviewer,” and “cryptographic approval/ledger” as current guarantees. Mark historical “all features verified” audit docs invalidated. | 0.5–1 week | None | README/CLI/docs consistently describe observed behavior; `gh solve` auto-PR is disabled or clearly gated before any public use. |
| Correct verifier semantics: preserve exit code/timeouts, classify parse failures as inconclusive, distinguish target/impacted/full command scope, and require explicit full command for full-suite label. | 1–2 weeks | Define report contract | Reproductions for nonzero/no-output, zero tests, timeout, targeted-only pass with unrelated failure, and full command produce correct outcomes. |
| Remove default automatic approval/publishing; require explicit user action for apply or PR. Remove the fake signature or rename it as a non-authenticating digest. | 0.5–1 week | Correct verifier semantics | No external side effect occurs from defaults; report explains the action and evidence. |
| Replace retired model IDs in config/examples and stop hardcoding provider model names. Validate configured model before repair begins. | 0.5–1 week | Choose whether LLM repair remains | Current supported model configuration is verified through a controlled provider smoke test before claiming live support. |
| Make policy schema strict and remove advertised but unenforced keys. | 0.5–1 week | Decide narrow policy requirements | Unknown fields fail at load time; every documented field has a test and enforcement path. |

These items reduce immediate misrepresentation; completing them does not validate demand or make execution secure.

## P1 — Validate the product before continued engineering

| Work | Estimate | Dependencies | Exit condition |
|---|---:|---|---|
| Interview and observe 5–8 maintainers in one chosen segment (for example, teams with reproducible CI failures and strict review policy). Ask them to use a prototype workflow on their own issue. | 2–3 weeks | Name a segment and recruit users | At least two maintainers commit to repeated use or a design partnership; otherwise stop product work. This threshold is a decision rule, not a market statistic. |
| Compare the narrow prototype against their current assistant + branch/worktree + tests + CI flow. Measure setup time, accepted patches, engineer review time, false-clean outcomes, and total cost. | 2–4 weeks | P0 verifier contract; willing users | Evidence shows a material workflow improvement and no false-clean results in the evaluation set. |
| If and only if untrusted repositories are in-scope, implement an OS-enforced execution backend and threat model. | 3–6 weeks, platform dependent | Product validation; supported OS choice | Independent review verifies filesystem, network, process, and resource boundaries on supported platform(s). |

## P2 — Quality work only after the P1 gate passes

| Work | Estimate | Dependencies | Exit condition |
|---|---:|---|---|
| Replace LangGraph with a transparent coordinator; narrow CLI to repair/verify/report; return stable process exit codes. | 1–2 weeks | Product validation | New engineer can follow one documented flow; script callers get reliable status. |
| Make workspace creation unique, permission-restricted, collision-safe, and cleaned in all paths. | 1 week | Runner/report lifecycle | Concurrent run test cannot delete or overwrite another run; no stale scratch directory after success/failure unless retained explicitly. |
| Make Synapse integration, LLM recorder, unused ledger/experiment/reviewer pieces removable; delete unused dependencies after API compatibility review. | 1–2 weeks | Decide final scope; check package consumers | Runtime dependency list matches actual direct imports; historical docs no longer imply removed features. |
| Make tests hermetic and CI toolchain reproducible. Add only tests tied to the new contract and supported platform. | 1–2 weeks | Runner and CLI stabilized | Linux CI passes; no test depends on a sibling repo or user-specific absolute path. |
| Replace synthetic benchmark claims with a versioned real-repository task set and simple baselines. | 3–6 weeks | User validation and frozen tasks | Results include failures, task-level outcomes, runtime, model/provider, and actual cost; no unsupported accuracy headline. |

## P3 — Future opportunities, contingent on repeated use

- A GitHub integration that opens a draft PR only after verified evidence and explicit review, if users ask for it.
- Additional providers only when a user workflow requires them and compatibility tests can be maintained.
- A richer evidence export or authenticated signature only when a compliance or audit requirement is demonstrated.
- Broader language/test-runner support only when real adopters supply representative repositories.

## NEVER — Do not build without a new, specific justification

- More agents, planning loops, reflection loops, model roles, or “blind reviewer” layers before a measured quality gain.
- Vector databases, embeddings, long-term memory, or RAG infrastructure for this local narrow workflow.
- Persistent orchestration services, background worker fleets, event buses, or microservices.
- A claim ledger, experiment engine, content-addressed store, or cryptographic approval layer without a real consumer and verifiable threat model.
- Enterprise dashboards, multi-tenant control planes, or broad admin features before repeated customer use.
- Automatic merge, default PR publishing, or “full CI verified” labels based on partial commands.
- More configuration fields that are silently ignored or not enforced.
- Synapse as a required dependency or differentiator without comparative repair evidence.
- A larger benchmark score from synthetic fixtures presented as general repair accuracy.

## Stop condition

If no named design partner or internal adopter is willing to run the narrow workflow on real repository tasks after the P1 discovery window, stop product work. Archive the repository as a prototype, preserve the audit and migration notes, and reuse only isolated patch/policy code where it is demonstrably better than a small fresh implementation.
