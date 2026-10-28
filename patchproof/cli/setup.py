"""First-time setup, health check diagnostics, and system readiness verification."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from rich.table import Table

from patchproof.config import settings
from patchproof.github.client import GitHubClient
from patchproof.ui.console import console


class DiagnosticCheck:
    """Represents a single system readiness check."""

    def __init__(self, name: str, category: str, required: bool = True):
        self.name = name
        self.category = category
        self.required = required
        self.passed: bool = False
        self.warning: bool = False
        self.message: str = ""
        self.remedy: str = ""


class SetupManager:
    """Orchestrates first-time setup, environment provisioning, and health diagnostics."""

    DEFAULT_POLICY_YAML = """# PatchProof Security & Repair Policy (Strict Default)
version: "1.1.0"
policy_id: "default-strict-v1.1"

scope:
  max_diff_bytes: 16384
  max_files_modified: 5
  protected_paths:
    - ".git/**"
    - ".github/**"
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
"""

    DEFAULT_ENV_TEMPLATE = """# PatchProof Environment Settings
# LLM Providers (At least one required for autonomous reasoning; deterministic mode works without keys)
PATCHPROOF_ANTHROPIC_API_KEY=
PATCHPROOF_GEMINI_API_KEY=
PATCHPROOF_OPENAI_API_KEY=

# GitHub Authentication (gh CLI keyring is preferred; or personal access token)
GITHUB_TOKEN=

# Model Routing
PATCHPROOF_MODEL_FAST=gemini-1.5-flash
PATCHPROOF_MODEL_STRONG=claude-3-7-sonnet-20250219
PATCHPROOF_MODEL_REVIEWER=claude-3-5-sonnet-20241022

# Operational Budgets
PATCHPROOF_MAX_RETRIES=2
PATCHPROOF_TIMEOUT_SECONDS_PER_TEST=120
PATCHPROOF_AUTO_APPROVE=true
"""

    @classmethod
    def run_diagnostics(cls) -> list[DiagnosticCheck]:
        """Perform non-destructive system readiness checks across all subsystems."""
        checks: list[DiagnosticCheck] = []

        # 1. Python Runtime Check
        py_check = DiagnosticCheck("Python Version (>= 3.11)", "Core Runtime", required=True)
        py_ver = sys.version_info
        if py_ver >= (3, 11):
            py_check.passed = True
            py_check.message = f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}"
        else:
            py_check.passed = False
            py_check.message = f"Python {py_ver.major}.{py_ver.minor} (Upgrade required)"
            py_check.remedy = "Install Python 3.11+ using pyenv or brew install python@3.12"
        checks.append(py_check)

        # 2. Package & Environment Manager (uv)
        uv_check = DiagnosticCheck("uv Package Manager", "Core Runtime", required=True)
        if shutil.which("uv"):
            uv_check.passed = True
            uv_check.message = "Installed and found on PATH"
        else:
            uv_check.passed = False
            uv_check.message = "Missing"
            uv_check.remedy = "Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"
        checks.append(uv_check)

        # 3. Git Version Control & User Identity
        git_check = DiagnosticCheck("Git Version Control", "Core Runtime", required=True)
        if shutil.which("git"):
            try:
                user_name = subprocess.check_output(["git", "config", "user.name"], text=True).strip()
                user_email = subprocess.check_output(["git", "config", "user.email"], text=True).strip()
                git_check.passed = True
                git_check.message = f"Configured for {user_name} <{user_email}>"
            except Exception:
                git_check.warning = True
                git_check.message = "Installed, but user.name or user.email not configured"
                git_check.remedy = "Run: git config --global user.name '...' && git config --global user.email '...'"
        else:
            git_check.passed = False
            git_check.message = "Missing"
            git_check.remedy = "Install git via brew install git"
        checks.append(git_check)

        # 4. GitHub CLI (gh)
        gh_check = DiagnosticCheck("GitHub CLI (gh)", "Integrations", required=False)
        gh_client = GitHubClient()
        if gh_client.cli_bin:
            if gh_client.is_authenticated():
                gh_check.passed = True
                user = gh_client.get_authenticated_user()
                gh_check.message = f"Authenticated as @{user}"
            else:
                gh_check.warning = True
                gh_check.message = "Installed, but not logged in"
                gh_check.remedy = "Run: gh auth login"
        else:
            gh_check.warning = True
            gh_check.message = "Not found on PATH"
            gh_check.remedy = "Install via: brew install gh && gh auth login"
        checks.append(gh_check)

        # 5. Synapse AST Structural Graph (synap)
        syn_check = DiagnosticCheck("Synapse AST Graph (synap)", "Integrations", required=False)
        if shutil.which("synap"):
            syn_check.passed = True
            try:
                ver_out = subprocess.check_output(["synap", "--version"], text=True).strip()
                syn_check.message = ver_out
            except Exception:
                syn_check.message = "Installed on PATH"
        else:
            syn_check.warning = True
            syn_check.message = "Not installed (Optional; Standard AST fallback active)"
            syn_check.remedy = "Synapse provides deep call-graph indexing for complex repos"
        checks.append(syn_check)

        # 6. Scratch Storage & Workspace Directories
        storage_check = DiagnosticCheck("Ephemeral Sandboxes & CAS", "Storage", required=True)
        try:
            settings.workspace_root.mkdir(parents=True, exist_ok=True)
            settings.cas_storage_dir.mkdir(parents=True, exist_ok=True)
            storage_check.passed = True
            storage_check.message = f"Writable: {settings.workspace_root}"
        except Exception as e:
            storage_check.passed = False
            storage_check.message = f"Permission error: {e}"
            storage_check.remedy = f"Ensure write permissions for {settings.workspace_root}"
        checks.append(storage_check)

        # 7. Policy Configuration
        policy_check = DiagnosticCheck("Policy Governance (policy.yaml)", "Security", required=True)
        if settings.policy_file.exists():
            policy_check.passed = True
            policy_check.message = f"Found: {settings.policy_file}"
        else:
            policy_check.warning = True
            policy_check.message = "Missing default policy file"
            policy_check.remedy = "Run 'patchproof setup --init-policy' to generate default strict policy"
        checks.append(policy_check)

        # 8. AI Model Providers
        llm_check = DiagnosticCheck("AI Model Providers", "AI Gateway", required=False)
        anthropic_key = os.environ.get("PATCHPROOF_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        gemini_key = os.environ.get("PATCHPROOF_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        openai_key = os.environ.get("PATCHPROOF_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")

        active_providers: list[str] = []
        if anthropic_key:
            active_providers.append("Anthropic (Claude 3.7)")
        if gemini_key:
            active_providers.append("Gemini (1.5 Pro / 2.0)")
        if openai_key:
            active_providers.append("OpenAI (GPT-4o)")

        if active_providers:
            llm_check.passed = True
            llm_check.message = f"Active: {', '.join(active_providers)}"
        else:
            llm_check.warning = True
            llm_check.message = "No cloud API keys detected; Local Deterministic Spine active"
            llm_check.remedy = "Set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env for autonomous reasoning"
        checks.append(llm_check)

        return checks

    @classmethod
    def render_diagnostics_table(cls, checks: list[DiagnosticCheck]) -> None:
        """Render diagnostic results in an intuitive Rich table."""
        table = Table(title="🛡️ PatchProof System Diagnostics & Health Check", title_style="bold cyan")
        table.add_column("Subsystem", style="bold white", width=20)
        table.add_column("Component", style="cyan", width=32)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Details / Action", style="dim", width=42)

        for c in checks:
            if c.passed:
                status = "[bold green]✓ PASS[/bold green]"
                details = c.message
            elif c.warning:
                status = "[bold yellow]⚠ WARN[/bold yellow]"
                details = f"{c.message} ([yellow]{c.remedy}[/yellow])"
            else:
                status = "[bold red]✗ FAIL[/bold red]"
                details = f"[red]{c.message}[/red] - {c.remedy}"

            table.add_row(c.category, c.name, status, details)

        console.print(table)

    @classmethod
    def initialize_defaults(cls, project_dir: Path) -> dict[str, Any]:
        """Bootstrap default policy, workspace paths, and environment template."""
        created: list[str] = []

        # 1. Create policy.yaml
        policy_path = project_dir / "policy.yaml"
        if not policy_path.exists():
            policy_path.write_text(cls.DEFAULT_POLICY_YAML, encoding="utf-8")
            created.append("policy.yaml")

        # 2. Create .env.example
        env_example = project_dir / ".env.example"
        if not env_example.exists():
            env_example.write_text(cls.DEFAULT_ENV_TEMPLATE, encoding="utf-8")
            created.append(".env.example")

        # 3. Create .env if missing
        env_path = project_dir / ".env"
        if not env_path.exists():
            env_path.write_text(cls.DEFAULT_ENV_TEMPLATE, encoding="utf-8")
            created.append(".env")

        # 4. Provision workspace directories
        settings.workspace_root.mkdir(parents=True, exist_ok=True)
        settings.cas_storage_dir.mkdir(parents=True, exist_ok=True)

        return {
            "created_files": created,
            "workspace_dir": str(settings.workspace_root),
            "cas_dir": str(settings.cas_storage_dir),
        }
