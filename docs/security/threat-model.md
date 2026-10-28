# Threat Model & Vulnerability Defenses — PatchBound v1.1.0

**Document:** Threat Model, Attack Surface Analysis, & Defenses  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Trust Boundaries](trust-boundaries.md) • [Threat Model & Defenses](threat-model.md) • [Security Audit Report](../audits/security-adversarial-report.md)

---

## 1. Threat Vectors & Defensive Assertions

| Attack Vector | Potential Impact | Defensive Mechanism in PatchBound | Test Verification |
| :--- | :--- | :--- | :--- |
| **Path Traversal in Edits** | Overwriting `/etc/passwd` or host files outside workspace via `../../` | `Patcher` validates `is_relative_to(workspace_path)` and rejects absolute paths | `test_path_traversal_in_anchored_edits_rejected` |
| **Symlink Hijacking** | Overwriting files outside the workspace through pre-existing symlinks | `Patcher` inspects `.is_symlink()` and rejects edits targeting symbolic links | `test_symlink_traversal_in_anchored_edits_rejected` |
| **Clone Directory Escape** | Deleting host directories via crafted `investigation_id` | `CloneManager` asserts `clone_dir.is_relative_to(scratch_base_dir)` | `test_investigation_id_path_traversal_in_clone_manager` |
| **Test Tampering / Cheating** | Weakening assertions or adding `@pytest.mark.skip` to fake a pass | Pinned oracle restores test files; AST anti-cheat scanner rejects skip decorators | `test_pinned_oracle.py`, `test_anti_cheat.py` |
| **Host Modification Bypass** | Applying unverified or unapproved patches to host code | CLI requires both `human_approved` and `V1+` verification before running `git apply` | `test_unapproved_patch_is_never_applied_to_host` |
| **Secret Exfiltration** | Leaking API keys or tokens into prompts, logs, or audit records | `EgressGate` sanitizes Anthropic, OpenAI, Gemini, DeepSeek, and GitHub tokens | `test_guardrails.py` |
| **Audit Log Forgery** | Mutating recorded journal entries to conceal failed verification | `AuditJournal.verify_integrity()` validates SHA-256 hash chain continuity | `test_audit_journal_tampering_detection` |

---

## 2. Red Team Discoveries & Remediations (Phase 3)

During the Phase 3 adversarial security audit, five vulnerabilities were discovered and surgically remediated:

### 2.1 Arbitrary File Overwrite via Path Traversal
- **Discovery:** In `Patcher.apply_edits()`, `file_path` strings were joined with `workspace_path` without checking if the resolved target escaped the workspace root.
- **Fix:** Enforced `resolved.is_relative_to(self.workspace_path)` and explicitly rejected leading slashes (`/` or `\`).

### 2.2 Symlink Workspace Escape
- **Discovery:** If a target codebase contained a symbolic link pointing to an external file, modifying that file through the symlink wrote directly to the target.
- **Fix:** Added `.is_symlink()` rejection before attempting any file read or write.

### 2.3 Unapproved Patch Application Logic
- **Discovery:** When `--apply` was passed alongside `--no-auto-approve`, a boolean precedence bug in `human_approval_node` allowed auto-approval to default to `True`.
- **Fix:** Fixed boolean precedence in `human_approval_node` and enforced that `main()` verifies `result.get("human_approved") is True` before invoking `git apply`.

### 2.4 Audit Journal Tamper Detection
- **Discovery:** The audit journal wrote SHA-256 hash chains, but lacked a public validation method in the CLI to detect post-hoc tampering.
- **Fix:** Added `verify_integrity()` to `AuditJournal` and wired it into `patchbound inspect journal`.

---

## 3. Credential Security & Redaction

### 3.1 On-Disk Storage Invariants
- Credentials are stored at `~/.config/patchbound/credentials.json`.
- The configuration directory is created with mode `0700` (`rwx------`).
- The credentials file is created with mode `0600` (`rw-------`).
- Keys are masked in all console outputs (e.g. `sk-ant-...4a9e`).

### 3.2 Secret Egress Filtering
The `EgressGate` intercepts all outgoing prompts and captured command outputs, replacing matching regex patterns with `[REDACTED_API_KEY]`:
- Anthropic: `sk-ant-[a-zA-Z0-9_\-]{20,}`
- OpenAI: `sk-(?:proj-)?[a-zA-Z0-9_\-]{20,}`
- Gemini: `AIzaSy[a-zA-Z0-9_\-]{33}`
- DeepSeek: `sk-[a-f0-9]{32}`
- GitHub Tokens: `gh[pousr]_[a-zA-Z0-9]{36,}`

---

## 4. Responsible Disclosure

If you discover a security vulnerability in PatchBound, please report it via private email to:
**`security@patchbound.dev`** or **`sahilpal.dev@gmail.com`**.

Please do not open public GitHub issues for security vulnerabilities. We acknowledge reports within 48 hours and aim to provide fixes within 7 days.
