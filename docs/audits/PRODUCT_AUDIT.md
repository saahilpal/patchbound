# PatchBound: Product Audit

**Audit date:** 2026-11-01  
**Evidence labels:** **Verified** means visible in tracked code or reproduced locally. **Inferred** means a reasoned product judgment. **Unknown** means the repository provides no reliable evidence.

## 1. Original problem and actual product

The README and PRD frame the problem as unsafe, probabilistic AI code repair: a model may make a patch that appears to fix one issue while changing tests, hiding failures, or regressing other behavior. The intended answer is a constrained repair workflow with reproducible failures, anchored edits, test-oracle protection, policy checks, verification tiers, a reviewer, an approval gate, and an audit record. See `README.md` and `docs/PRD.md`, especially the product doctrine and architecture claims.

That is a coherent problem statement, but the implemented product is narrower and less reliable:

1. A user supplies a repository and reproduction command through the CLI.
2. PatchBound clones the repository into a scratch directory and runs the command.
3. Heuristic investigation searches for symbols or words derived from test output.
4. A configured provider may propose a change; offline fallback handles a very small arithmetic pattern.
5. The change is applied to another disposable clone and the supplied command is run again.
6. A report and diff may be emitted; CLI `--apply` can apply the diff to the host repository.

The `gh solve` command fetches an issue, selects a reproduction hint or defaults to `pytest -v`, clones the repository, then invokes this same flow. It does not pass the issue body/title into the investigation or repair state (`patchbound/cli/main.py:606-647`). With `--auto-pr` defaulting to true, it can push a branch and create a PR after the workflow says it succeeded (`patchbound/cli/main.py:575-585, 658-691`).

The `gh review` command is not a review service: it checks out a PR head and runs tests, but does not compare the PR diff against its base, call a blind reviewer, or submit a GitHub review (`patchbound/cli/main.py:701-755`).

## 2. Target user and use cases

### Target user implied by the repository

The docs aim at developers and teams that want automated repair with confidence, especially maintainers of repositories where tests and policy should constrain a generated patch. GitHub issue-to-PR automation is also implied by the CLI and PRD.

### What is verified about users

Nothing in the repository demonstrates actual users, interviews, design partners, repeated use, support demand, payment, or willingness to replace an established coding assistant. The README’s audience and PRD personas are product hypotheses, not user evidence.

### Plausible first user, if the idea is retested

An engineer who already has a deterministic failing test and wants one proposed patch applied in a disposable checkout, with exact command/exit status/output and a reviewable diff. This is narrower than “autonomous issue solver” and matches the path the implementation attempts to support. It remains a hypothesis until a real maintainer uses it on their own repository.

## 3. Actual value proposition

The strongest possible value proposition is not “AI repair” by itself. Coding assistants already generate code. A defensible claim could be: “PatchBound records what was run, preserves the resulting diff, and refuses to call a patch clean unless a configured verification command actually completed successfully.”

The current implementation fails that claim: `VerificationRunner` discards the process exit code; the parser can return zero failures for an unrecognized failing command; `patch_verify_node` supplies an empty impacted-test set and labels all flags true; and `VerificationEvaluator` can call a targeted test command V3 / CI-clean. The direct V3 false-positive reproduction is recorded as ENG-01.

So the product’s claimed trust advantage is presently a label, not a demonstrated user benefit.

## 4. Product-market assumptions and gaps

| Assumption | Status | What the repository shows |
|---|---|---|
| Developers will install another CLI for generated repair | Unknown | No install/adoption data or design-partner evidence. |
| A multi-stage repair state machine is more useful than a coding assistant plus tests | Not demonstrated | No comparative study or real-codebase evaluation. |
| A separate “trust layer” is worth maintaining | Plausible, unvalidated | User need is real, but current trust claims are not backed by execution semantics. |
| Synapse call-graph context materially improves repair | Not demonstrated | No controlled benchmark with/without Synapse; the feature depends on an external local checkout/index. |
| A cryptographic claim ledger increases trust | Not demonstrated | The claim objects are typed records; exported evidence is much thinner than the docs imply. |
| Teams want automatic issue-to-PR operation | Unknown | No customer evidence; existing assistants already target this workflow. |
| “V1/V2/V3” is understandable and useful to buyers | Doubtful | V3 currently does not mean a full CI run; the terminology risks misleading users. |

### Missing product capabilities for the promise being made

- A required, explicit distinction among target test, impacted tests, and full configured CI.
- A truthful execution record including exact command, exit code, timeout, test count, parser confidence, and raw output/artifact pointer.
- Reproducible clean snapshots for each baseline run.
- A real isolation boundary for untrusted dependency builds and test code.
- An explicit human review event bound to the final patch and the evidence, with a real identity source if called a signature.
- A safe and understandable failure mode when tests cannot be parsed or the command exits abnormally.
- Evidence on representative repositories rather than only tiny synthetic fixtures.

Adding dashboards, more model roles, or more status levels does not address these gaps.

## 5. Is there a simpler way?

For an individual developer, the native workflow is already simple: create a branch or Git worktree, ask a coding assistant to make a change, run the targeted and broader tests, inspect the diff, and use CI/PR review. PatchBound only earns a place if it measurably reduces risk or effort beyond this flow.

For an organization, the simplest plausible product is a CI job or GitHub App that records a patch artifact and trustworthy test evidence. That might be more useful than a separate local agent, but this is an unvalidated direction and would require a real security boundary for untrusted execution. It is not a recommendation to build the App before validating demand.

## 6. Competitive and alternative analysis

The following are direct capability comparisons from official product documentation, checked 2026-11-01. They establish overlap, not that every alternative is better for every team.

| Alternative | What it already covers | Where PatchBound could be better | Current assessment |
|---|---|---|---|
| [GitHub Copilot coding agent / app](https://docs.github.com/en/copilot/how-tos/github-copilot-app/managing-issues-and-pull-requests) | Can work from GitHub issues, make repository changes, and open PRs with CI/review workflow context. | A genuinely stronger, auditable verification contract and explicit policy constraints. | PatchBound overlaps the issue-to-PR workflow but does not currently deliver the stronger verification needed to differentiate. |
| [OpenAI Codex cloud](https://help-lb.openai.com/en/articles/20001545-using-codex-cloud) | Runs code tasks in isolated managed workspaces and lets users ask for changes, bug investigation, and tests. | A local, provider-neutral workflow or specialized evidence semantics, if proven valuable. | Strong overlap in delegate-a-task-and-review-output. PatchBound’s local subprocess is not an equivalent isolation boundary. |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | Research/open-source issue-to-code repair agent. Its project notes direct new users toward the simpler mini-swe-agent successor. | Better deterministic test evidence, policy constraints, or narrower integration for a defined user. | Relevant open-source baseline; PatchBound has no comparative results. |
| [Aider test/lint workflow](https://aider.chat/docs/usage/lint-test.html) | Terminal-based coding workflow with user-configured lint/test commands. | A safer runner and verifiable test-scope result. | For an individual engineer, Aider plus ordinary test execution is simpler than PatchBound’s graph and ledger layers. |
| Git branch/worktree + local tests + CI + human PR review | Provides isolation from the working tree, executable checks, review, and durable CI status in existing tooling. | Reduce setup and produce stronger evidence without adding friction. | Already solves much of the ordinary workflow. PatchBound must show a material improvement to justify another dependency. |

**Inference:** Based on the documented feature overlap, a new standalone CLI faces a high switching bar. No repository evidence shows that PatchBound currently clears that bar.

## 7. Product waste and positioning

### Remove from the product promise

- **“Untrusted code sandbox,” “no network,” “rlimits,” or equivalent guarantee:** the code does not implement OS isolation. See ENG-02.
- **“Full CI clean / V3”** unless and until a configured full command is run and its exit status and coverage are known. See ENG-01.
- **“Human-approved” / “cryptographic approval”** for the generated hash. There is no human identity or approval event. See ENG-03.
- **“Blind reviewer,” “causal experiment,” and “cryptographic claim ledger”** descriptions that imply connected work not present in the pipeline. See ENG-04 and ENG-05.
- **“Autonomous issue solver” and “PR reviewer”** as current capabilities. The issue text is not repair context and the PR review command does not review or post a review.

Removing these claims lowers the apparent product scope, but avoids asking users to trust outputs whose semantics are wrong. It may require a major version/documentation rewrite if external integrations rely on current names.

### Defer until there is a validated adopter

- Multi-language support, enterprise controls, dashboards, persistent state, remote workers, further model providers, and broad GitHub automation.
- Synapse integration as a differentiator; no evidence it improves repairs or saves more time than its setup/portability costs.
- Any additional agent, memory, vector retrieval, reflection, or planning loop.

### Recommended positioning if discovery finds demand

“A small patch proposal runner that preserves the exact patch and truthful test evidence for review.” Do not market it as autonomous repair, secure execution, full-CI verification, or a cryptographic approval system until those properties are actually implemented and independently checked.

## 8. Conclusion

The problem is worth solving; the current product is not proven worth maintaining. The existing alternatives make a broad issue-to-PR assistant difficult to justify, while the narrow trust differentiator is not implemented correctly. The rational next step is not more feature development. It is a short validation effort with named maintainers and a real repository workflow. Without that evidence, abandon the standalone product direction.
