# Configuration & Credentials — PatchBound v1.1.0

**Document:** Configuration, Declarative Policy, & Credential Security  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Installation](installation.md) • [Quickstart](quickstart.md) • [Configuration](configuration.md) • [Synapse Integration](synapse.md)

---

## 1. Zero-Trust Credential Store

PatchBound manages API keys and authentication tokens without environment variable leakage or plain-text exposure.

### Filesystem Invariants:
- **Location:** `~/.config/patchbound/credentials.json`
- **Directory Mode:** `0700` (`drwx------`, owner-only read/write/execute)
- **File Mode:** `0600` (`-rw-------`, owner-only read/write)
- **Console Echo:** Keys are entered with hidden input (`click.prompt(hide_input=True)`) and masked on display (`sk-ant-...4a9e`).

---

## 2. Authentication CLI Commands

```bash
# Interactive guided login (prompts for keys securely)
patchbound auth login

# Set key for a specific provider
patchbound auth set-key anthropic
patchbound auth set-key gemini
patchbound auth set-key openai
patchbound auth set-key deepseek
patchbound auth set-key github

# Check configured providers and sources
patchbound auth status

# Safely delete keys
patchbound auth logout anthropic
patchbound auth logout all
```

### Status Output Example:
```
                🔑 PatchBound Authentication & Credential Store                 
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Provider   ┃ Env Variable       ┃   Status   ┃ Source         ┃ Masked Key    ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Anthropic  │ ANTHROPIC_API_KEY  │ Configured │ credentials.json│ sk-ant-...4a9e│
│ Gemini     │ GEMINI_API_KEY     │ Configured │ credentials.json│ AIzaSy...9b12 │
│ Openai     │ OPENAI_API_KEY     │ Configured │ credentials.json│ sk-proj...7f88│
│ Deepseek   │ DEEPSEEK_API_KEY   │  Not Set   │ missing        │ Not set       │
│ Github     │ GITHUB_TOKEN       │ Configured │ environment    │ ghp_...d81a   │
└────────────┴────────────────────┴────────────┴────────────────┴───────────────┘
```

---

## 3. Credential Precedence Hierarchy

PatchBound resolves credentials in the following strict order of precedence:
1. `PATCHBOUND_<PROVIDER>_API_KEY` (Explicit application-scoped environment variable)
2. `<PROVIDER>_API_KEY` (Standard provider environment variable, e.g. `ANTHROPIC_API_KEY`)
3. `~/.config/patchbound/credentials.json` (Local encrypted/isolated credential store)

---

## 4. Declarative Policy Configuration (`policy.yaml`)

PatchBound behavior can be configured via a local or global `policy.yaml` file:

```yaml
version: "1.1"

# Sandboxing and execution limits
sandbox:
  base_dir: "/tmp/patchbound-workspaces"
  timeout_seconds: 120
  memory_limit_mb: 4096
  allow_network: false

# Verification and anti-cheat policies
verification:
  default_level: "V3"
  enforce_pinned_oracle: true
  reject_skip_decorators: true
  max_attempts: 2
  flake_check_iterations: 3

# Security and secret redaction
security:
  redact_secrets: true
  allow_git_hooks: false
  require_human_approval: true

# Context retrieval provider (auto | synapse | standard)
context:
  provider: "auto"
```
