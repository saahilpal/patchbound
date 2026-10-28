# Installation Guide — PatchBound v1.1.0

**Document:** Installation, System Requirements, & Setup  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Installation](installation.md) • [Quickstart](quickstart.md) • [Configuration](configuration.md) • [Synapse Integration](synapse.md)

---

## 1. System Requirements

- **Operating System:** Linux (Ubuntu 20.04+, Debian 11+, RHEL/CentOS 8+), macOS (12.0+ Monterey, Ventura, Sonoma, Sequoia).
- **Python Version:** Python 3.11 or 3.12 (CPython).
- **Git Version:** Git 2.30+ (required for local cloning and patch application).
- **Package Manager (Recommended):** [`uv`](https://github.com/astral-sh/uv) (version 0.4.0+).

---

## 2. Installation Methods

### Option A: Install from PyPI (Recommended)
PatchBound is published on PyPI at [pypi.org/project/patchbound](https://pypi.org/project/patchbound/).

Install using `uv` (recommended for isolated tools):
```bash
uv tool install patchbound
```

Or install using standard `pip`:
```bash
pip install patchbound
```

### Option B: Install from Source
```bash
# Clone repository
git clone https://github.com/saahilpal/patchbound.git
cd patchbound

# Sync virtual environment and dependencies using uv
uv sync --extra dev

# Run CLI using uv
uv run patchbound --version
```

---

## 3. Verify Installation (`patchbound doctor`)

After installing, run the built-in diagnostic health checker:
```bash
patchbound doctor
```

Expected diagnostic output:
```
╭──────────────────────────────────────────────────────────────────────╮
│  PatchBound v1.1  · Deterministic Trust Boundary & Bounded AI Repair │
╰──────────────────────────────────────────────────────────────────────╯
Diagnosing System Environment & Integrations...

                🛡️ PatchBound System Diagnostics & Health Check                 
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Subsystem  ┃ Component              ┃ S… ┃ Details / Action                  ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Core       │ Python Version (>=     │ ✓  │ Python 3.12.13                    │
│ Runtime    │ 3.11)                  │ P… │                                   │
│ Core       │ uv Package Manager     │ ✓  │ Installed and found on PATH       │
│ Runtime    │                        │ P… │                                   │
│ Core       │ Git Version Control    │ ✓  │ Configured                        │
│ Integrati… │ GitHub CLI (gh)        │ ✓  │ Authenticated                     │
│ Integrati… │ Synapse AST Graph      │ ✓  │ Synap v2.4.1                      │
│ Storage    │ Ephemeral Sandboxes    │ ✓  │ Writable:                         │
│            │                        │ P… │ /tmp/patchbound-workspaces        │
│ Security   │ Policy Governance      │ ✓  │ Found: policy.yaml                │
│ AI Gateway │ AI Model Providers     │ ⚠  │ No cloud API keys detected; Local │
│            │                        │ W… │ Deterministic Spine active        │
└────────────┴────────────────────────┴────┴───────────────────────────────────┘
```
