# Security Policy

PatchBound is designed to enforce deterministic trust boundaries, prevent test gaming, and safely sandbox autonomous AI code repair. We take security vulnerabilities seriously.

---

## 🛡️ Supported Versions

We actively support the latest minor release with security patches:

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| < 1.1.0 | :x:                |

---

## 🔒 Reporting a Vulnerability

If you discover a security vulnerability—such as an anti-cheat bypass, credential egress leak, or sandbox escape—please **do not disclose it publicly** via GitHub issues.

Instead, please send an encrypted or direct email to:

📧 **sahilpal.dev@gmail.com** (Subject: `[PatchBound Security] <Vulnerability Summary>`)

Please include:
1. A description of the vulnerability.
2. Steps to reproduce or proof-of-concept repository.
3. Impact assessment (e.g., test gaming, arbitrary code execution, credential egress).
4. Any proposed fixes or remediations.

### Response Time

- **Initial Acknowledgement:** Within 24–48 hours.
- **Triage & Assessment:** Within 72 hours.
- **Security Advisory & Patch:** We will coordinate a CVE and coordinated disclosure timeline (typically 14–30 days).

---

## 🛡️ Security Architecture Guarantees

PatchBound enforces the following security invariants:
- **Sandbox Isolation:** Clones run in isolated ephemeral directories (`/tmp/patchbound-workspaces`) with `core.hooksPath=/dev/null` and scrubbed environment variables.
- **Credential Storage:** User API keys are stored in `~/.config/patchbound/credentials.json` with strict `0600` owner-only permissions.
- **Secret Egress Filtering:** Regex and entropy filters redact API keys, tokens, and private keys before any data is sent to external LLM providers.
- **Pinned Test Oracles:** Test files and test configurations are cryptographically protected and restored to prevent patches from tampering with test suites.
