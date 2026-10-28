# PatchProof v1.1 System Design & Trust Boundary

> **Document:** Security & Trust Boundary Specification  
> **Classification:** Critical System Architecture  
> **Enforcement:** Hard Invariant Checks

---

## 1. Threat Model & Security Posture

PatchProof executes automated diagnosis and repair on potentially untrusted, broken, or malicious codebases. The core design premise is: **Untrusted code must never compromise the host machine, tamper with the verification oracle, bypass policy gates, or exfiltrate private credentials.**

### Threat Vectors & Defenses

| Threat Vector | Potential Attack | PatchProof v1.1 Deterministic Defense |
| :--- | :--- | :--- |
| **Test Tampering** | Patch modifies `conftest.py`, adds `@skip`, or weakens assertions to pass tests artificially. | **Pinned Oracle:** Deterministic restoration of all test files and configs by commit hash before verification. Hard rejection if patch touches tests. |
| **Malicious Package Scripts** | Compromised dependency executes post-install script on `npm install` or `pip install`. | **Prepare Isolation:** Scripts disabled by default (`--ignore-scripts`, wheels-only `--no-build-isolation`). Allowlisted registry mirror. |
| **Command Injection via LLM** | Model outputs arbitrary shell commands containing `; rm -rf /` or backticks. | **Runner Adapters:** LLM never emits shell strings. Runner commands use typed argv arrays (`['pytest', '-k', test_id]`) strictly matched against allowed templates. |
| **Host Worktree Contamination** | Tool writes to `.git/hooks` or modifies host branch refs. | **Disposable Clone:** Ephemeral clone outside host tree with `core.hooksPath=/dev/null` and pre/post SHA-256 invariant assertion on the host repo. |
| **Data Exfiltration via Egress** | Sensitive environment secrets or proprietary files are sent to LLM APIs. | **Egress Gate:** Regex secret scanner + path denylist + prompt preview mode before any network packet is dispatched to LLM. |

---

## 2. Repository Isolation & Invariant Verification

### 2.1 Why `git worktree add` is Disallowed
`git worktree` creates linked trees that share the primary `.git/objects` and `.git/config` directories. Any write operation in a linked worktree can:
- Trigger host-level git hooks.
- Create stale lock files (`.git/index.lock`).
- Pollute git reflogs and branch heads.

### 2.2 Disposable Clone Protocol
PatchProof implements disposable local cloning:
```bash
# Clone to an isolated ephemeral scratch directory
git clone --local --no-hardlinks \
  -c core.hooksPath=/dev/null \
  file:///path/to/host/repo /tmp/patchproof-workspaces/<id>/attempt-0
```

### 2.3 The Host Invariant Verification
Before starting a run and after terminating, PatchProof executes the **Host Integrity Audit**:
$$\text{HostState} = \text{SHA-256}(\text{HEAD} \parallel \text{refs/heads} \parallel \text{git write-tree} \parallel \text{git status --porcelain})$$

If $\text{HostState}_{\text{post}} \neq \text{HostState}_{\text{pre}}$, PatchProof aborts immediately with an alert and halts the pipeline. The host repository is guaranteed to remain 100% untouched.

---

## 3. Two-Phase Sandbox Architecture

To prevent execution attacks while allowing fast caching, execution is separated into two distinct stages:

```
+-----------------------------------------------------------------------+
| PHASE 1: PREPARE SANDBOX                                              |
| - Network: Outbound allowed ONLY to allowlisted package mirror        |
| - Dependencies: npm ci --ignore-scripts / pip install --only-binary   |
| - Caching: Keyed strictly by SHA-256(lockfile)                        |
| - Secrets: Zero environment secrets mounted                           |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
| PHASE 2: EXECUTE SANDBOX                                              |
| - Network: COMPLETELY DISABLED (--net=none)                           |
| - Root Filesystem: READ-ONLY (ro)                                     |
| - User: Non-root (UID 10001, GID 10001)                               |
| - Capabilities: CAP_DROP_ALL, no-new-privileges                       |
| - Resources: CPU cgroups (2 cores), Mem limit (4GB), Max PIDs (256)   |
| - Scratch Mount: Ephemeral /tmp in-memory tmpfs (max 512MB)           |
+-----------------------------------------------------------------------+
```

### Sandbox Providers
1. **Tier 1 (Production Default):** Rootless container (Podman / Docker with user namespace remapping).
2. **Tier 2 (MicroVM Isolation):** Firecracker or gVisor (`runsc`) for untrusted external multi-tenant execution.
3. **Tier 3 (Local Trusted):** Process isolation (`bwrap` / macOS `sandbox-exec` / subprocess with strict ulimits). All artifacts generated under Tier 3 are explicitly marked with `trusted-local-tier=true`.

---

## 4. Unified Policy Specification (`policy.yaml`)

PatchProof enforces all safety constraints via a single declarative, versioned policy file:

```yaml
version: "1.1.0"
policy_id: "default-strict-v1.1"

scope:
  max_diff_bytes: 16384          # 16 KB max diff
  max_files_modified: 5          # No mega-diffs
  max_hunks_per_file: 4
  protected_paths:
    - ".git/**"
    - ".github/**"
    - ".gitlab/**"
    - "ci/**"
    - "**/*test*/**"
    - "**/conftest.py"
    - "**/pytest.ini"
    - "**/package.json"
    - "**/tsconfig*.json"

forbidden_patterns:
  - id: "pytest_skip"
    regex: "@pytest\\.mark\\.(skip|xfail)"
    description: "Forbidden test skip marker added"
  - id: "ts_ignore"
    regex: "@ts-(ignore|expect-error|nocheck)"
    description: "TypeScript compiler check suppression"
  - id: "python_noqa"
    regex: "#\\s*noqa"
    description: "Linter suppression comment"
  - id: "removed_assertion"
    ast_check: "assert_removal_detector"
    description: "Deletion of existing test or runtime assertion"

allowed_commands:
  - tool: "pytest"
    template: ["pytest", "-v", "--tb=short", "--color=no"]
    allowed_flags: ["-k", "-m", "--maxfail"]
  - tool: "npm_test"
    template: ["npm", "test", "--"]
    allowed_flags: ["--runTestsByPath", "--testNamePattern"]

budgets:
  max_attempts: 2
  max_investigator_steps: 12
  max_total_tokens: 150000
  timeout_seconds_per_test: 120
```

---

## 5. Anchored Edits & Canonical Diff Engine

To eliminate LLM formatting and line offset hallucinations:
1. The **Fixer** outputs anchored edits:
```python
class AnchoredEdit(BaseModel):
    file_path: str
    old_text: str  # Must match exactly one location in the target file
    new_text: str  # Replacement string
```
2. The **Patcher** performs:
   - Reads target file at `attempt_dir / file_path`.
   - Verifies `file_path` is not in `protected_paths`.
   - Counts occurrences of `old_text`. If count $\neq 1$, fails with `AMBIGUOUS_ANCHOR` or `ANCHOR_NOT_FOUND`.
   - Performs exact replacement and writes back to disk.
   - Executes `git diff --no-prefix -U3` on the target workspace.
   - Computes canonical `patch_digest`:
$$\text{PatchDigest} = \text{SHA-256}\left(\text{git rev-parse HEAD:}^{} \parallel \text{CanonicalDiff}\right)$$

---

## 6. Egress Protection & Secret Scrubbing

Before any prompt or context payload is transmitted to an LLM provider:
1. **Secret Scanning:** Scans for high-entropy tokens, AWS keys (`AKIA...`), GitHub personal access tokens (`ghp_...`), private keys (`-----BEGIN RSA PRIVATE KEY-----`), and environment files (`.env`). Matches are replaced with `[REDACTED_SECRET_<TYPE>]`.
2. **Denylist Filter:** Paths matching `.env*`, `*secret*`, `*credential*`, `*id_rsa*` are immediately stripped from LLM context.
3. **Egress Audit Log:** Every outbound LLM call records a SHA-256 hash of the exact sanitized prompt text and token count in the append-only journal.
