# Trust Boundaries & Sandboxing — PatchBound v1.1.0

**Document:** Security Boundaries, Sandbox Isolation, & Host Invariants  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Trust Boundaries](trust-boundaries.md) • [Threat Model & Defenses](threat-model.md) • [Architecture Overview](../architecture/overview.md)

---

## 1. Core Security Tenet

PatchBound operates on potentially untrusted, compromised, or flawed software repositories. The guiding security principle is:

> **Untrusted code or AI-generated edits must never compromise the host operating system, bypass verification oracles, alter host Git history without explicit consent, or exfiltrate private credentials.**

Every candidate patch is isolated in an ephemeral, out-of-tree sandbox until it has passed all verification levels (V1–V3) and been explicitly approved by a human operator.

---

## 2. Ephemeral Sandbox Isolation

### 2.1 Why `git worktree` is Disallowed
Many developer tools use `git worktree add` for branching. In an autonomous repair system, shared worktrees introduce fatal security risks:
- They share `.git/hooks`, allowing malicious scripts to execute on checkout or commit.
- They share lockfiles (`.git/index.lock`), risking host lock contention.
- Writes in a linked worktree can modify refs and branch heads in the primary repository.

### 2.2 Disposable Scratch Clones
PatchBound mandates independent scratch directories located in `/tmp/patchbound-workspaces/<investigation_id>/attempt-<n>`.
Cloning enforces the following security invariants:
1. **Hook Neutralization:** `git clone --local -c core.hooksPath=/dev/null` ensures no pre-commit or post-checkout hooks can execute.
2. **Scratch Path Containment:** All clone operations validate that the resolved path is strictly contained within `scratch_base_dir`:
   ```python
   clone_dir = (self.scratch_base_dir / investigation_id / f"attempt-{attempt}").resolve()
   if not clone_dir.is_relative_to(self.scratch_base_dir):
       raise ValueError(f"Path traversal detected in investigation ID: {investigation_id}")
   ```
3. **Environment Scrubbing:** Test execution runners strip dangerous environment variables (`PYTHONPATH`, `NODE_PATH`, `LD_PRELOAD`, `DYLD_INSERT_LIBRARIES`).

---

## 3. Host Working Tree Immutability

### 3.1 Host Integrity Check
Before any work begins, PatchBound captures the cryptographic state of the host repository:
$$\text{HostState} = \text{SHA-256}(\text{HEAD} \parallel \text{refs/heads} \parallel \text{git status --porcelain})$$

During normal operation:
- Diagnosis, context extraction, patch application, and verification run strictly inside `/tmp/patchbound-workspaces`.
- If an investigation fails, times out, or exhausts its retry budget, the scratch workspace is discarded and the host repository remains 100% clean.

### 3.2 Controlled Patch Application (`--apply`)
A patch is applied to the host repository if and only if:
1. The verification record is **not** `V0_FAILED` (must satisfy at least `V1_F2P`).
2. The user passed the explicit `--apply` flag.
3. The human approval gate is satisfied (`result.get("human_approved") is True`).
4. The patch is applied using `git apply -p0` directly, which rejects malformed hunks.

If `--no-auto-approve` is passed and the operator rejects the change, the host repository remains untouched.
