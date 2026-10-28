"""Command-line interface for PatchProof v1.1."""

import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import click
from rich.table import Table

from patchproof import __version__
from patchproof.cli.setup import SetupManager
from patchproof.config import settings
from patchproof.context.base import ContextProvider
from patchproof.context.standard import StandardContextProvider
from patchproof.context.synapse import SynapseContextProvider
from patchproof.core.credentials import CredentialStore
from patchproof.core.models import OutcomeResult, ProcessStatus, VerificationLevel
from patchproof.eval.datasets import DatasetLoader
from patchproof.eval.mutator import SyntheticMutator
from patchproof.eval.report import EvalReporter
from patchproof.eval.runner import BenchmarkRunner
from patchproof.github.client import GitHubClient, GitHubClientError
from patchproof.graph.workflow import compile_patchproof_graph
from patchproof.guardrails.engine import GuardrailEngine
from patchproof.ui.console import PatchProofUI, console


@click.group()
@click.version_option(version=__version__, prog_name="patchproof")
def main() -> None:
    """PatchProof: Deterministic Trust Boundary & Bounded AI Repair Engine."""
    pass


# ---------------------------------------------------------------------------
# Setup & Health Check Diagnostics
# ---------------------------------------------------------------------------

@main.command()
@click.option("--init-policy", is_flag=True, default=True, help="Create default policy.yaml if missing.")
@click.option("--init-env", is_flag=True, default=True, help="Create .env template if missing.")
def setup(init_policy: bool, init_env: bool) -> None:
    """Guided first-time project setup, configuration, and environment bootstrapping."""
    PatchProofUI.print_banner()
    console.print("[bold cyan]Running First-Time Setup & Diagnostics...[/bold cyan]\n")

    current_dir = Path.cwd()
    res = SetupManager.initialize_defaults(current_dir)
    if res["created_files"]:
        for f in res["created_files"]:
            console.print(f"[bold green]✓ Initialized default configuration:[/bold green] `{f}`")
    else:
        console.print("[dim]Configuration files (policy.yaml, .env) already exist.[/dim]")

    console.print(f"[bold green]✓ Workspace sandboxes verified:[/bold green] `{res['workspace_dir']}`\n")

    checks = SetupManager.run_diagnostics()
    SetupManager.render_diagnostics_table(checks)

    console.print("\n[bold green]Setup Complete.[/bold green] You are ready to run PatchProof!")


@main.command()
def doctor() -> None:
    """Run non-destructive diagnostic health checks across all subsystems."""
    PatchProofUI.print_banner()
    console.print("[bold cyan]Diagnosing System Environment & Integrations...[/bold cyan]\n")

    checks = SetupManager.run_diagnostics()
    SetupManager.render_diagnostics_table(checks)


# ---------------------------------------------------------------------------
# Authentication & Credentials Management (0600 Permissions)
# ---------------------------------------------------------------------------

@main.group()
def auth() -> None:
    """Manage local API keys and authentication credentials securely (0600 permissions)."""
    pass


@auth.command(name="login")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["anthropic", "gemini", "openai", "deepseek", "github"]),
    help="Target provider to configure.",
)
def auth_login(provider: str | None) -> None:
    """Interactively configure API keys with masked input stored in ~/.config/patchproof/credentials.json."""
    PatchProofUI.print_banner()
    console.print("[bold cyan]Secure API Key Credential Setup[/bold cyan]")
    console.print("[dim]Keys are stored in ~/.config/patchproof/credentials.json with strict 0600 (owner-only) permissions.[/dim]\n")

    store = CredentialStore()
    providers_to_prompt = [provider] if provider else ["anthropic", "gemini", "openai", "deepseek", "github"]

    labels = {
        "anthropic": "Anthropic API Key (ANTHROPIC_API_KEY)",
        "gemini": "Google Gemini API Key (GEMINI_API_KEY)",
        "openai": "OpenAI API Key (OPENAI_API_KEY)",
        "deepseek": "DeepSeek API Key (DEEPSEEK_API_KEY)",
        "github": "GitHub Token (GITHUB_TOKEN or PAT)",
    }

    configured_count = 0
    for p in providers_to_prompt:
        existing = store.get_key(p)
        status_hint = f" [dim](currently: {store.mask_key(existing)})[/dim]" if existing else ""
        prompt_label = f"Enter {labels.get(p, p)}{status_hint}"

        value = click.prompt(
            prompt_label,
            default="" if existing else "",
            show_default=False,
            hide_input=True,
        )

        if value and value.strip():
            store.set_key(p, value.strip())
            console.print(f"[bold green]✓ Saved {p} key:[/bold green] `{store.mask_key(value.strip())}`")
            configured_count += 1
        elif existing:
            console.print(f"[dim]Retained existing {p} key.[/dim]")
        else:
            console.print(f"[dim]Skipped {p}.[/dim]")

    console.print(f"\n[bold green]Credentials updated securely.[/bold green] Storage: `{store.file_path}` (mode 0600)")


@auth.command(name="set-key")
@click.argument("provider", type=click.Choice(["anthropic", "gemini", "openai", "deepseek", "github"]))
@click.argument("key", required=False)
def auth_set_key(provider: str, key: str | None) -> None:
    """Set or update an API key for a single provider."""
    store = CredentialStore()
    if not key:
        key = click.prompt(f"Enter API key for {provider.upper()}", hide_input=True)

    if not key or not key.strip():
        console.print("[bold red]Error:[/bold red] API key cannot be empty.")
        return

    store.set_key(provider, key.strip())
    masked = store.mask_key(key.strip())
    console.print(f"[bold green]✓ Successfully configured {provider}:[/bold green] `{masked}`")
    console.print(f"[dim]Stored in {store.file_path} with 0600 permissions.[/dim]")


@auth.command(name="status")
def auth_status() -> None:
    """Display configured credentials, their active source, and masked previews."""
    PatchProofUI.print_banner()
    store = CredentialStore()
    status = store.get_status()

    table = Table(title="🔑 PatchProof Authentication & Credential Store", title_style="bold cyan")
    table.add_column("Provider", style="bold white", width=14)
    table.add_column("Env Variable", style="dim", width=22)
    table.add_column("Status", justify="center", width=14)
    table.add_column("Source", style="cyan", width=18)
    table.add_column("Masked Key", style="yellow", width=18)

    for provider, data in status.items():
        is_active = data["active"]
        stat_display = "[bold green]Configured[/bold green]" if is_active else "[dim]Not Set[/dim]"
        table.add_row(
            provider.capitalize(),
            data["env_var"],
            stat_display,
            data["source"],
            data["masked"],
        )

    console.print(table)
    console.print(f"\n[dim]Credentials file: {store.file_path} (mode 0600)[/dim]")


@auth.command(name="logout")
@click.argument("provider", required=False, type=click.Choice(["anthropic", "gemini", "openai", "deepseek", "github", "all"]))
def auth_logout(provider: str | None) -> None:
    """Remove stored credentials from ~/.config/patchproof/credentials.json."""
    store = CredentialStore()
    if not provider or provider == "all":
        if click.confirm("Are you sure you want to remove ALL stored credentials?", default=False):
            store.save_credentials({})
            console.print("[bold green]✓ All stored credentials have been removed.[/bold green]")
        else:
            console.print("[dim]Aborted.[/dim]")
    else:
        if store.delete_key(provider):
            console.print(f"[bold green]✓ Removed stored key for {provider}.[/bold green]")
        else:
            console.print(f"[yellow]No stored key found for {provider}.[/yellow]")


# ---------------------------------------------------------------------------
# Synapse Structural AST Graph Integration
# ---------------------------------------------------------------------------

@main.group()
def synapse() -> None:
    """Manage and inspect Synapse structural AST graph intelligence."""
    pass


@synapse.command(name="status")
@click.argument("repo_path", type=click.Path(path_type=Path), default=Path("."))
def synapse_status(repo_path: Path) -> None:
    """Inspect Synapse AST index status, symbol database, and caller graph for a repo."""
    PatchProofUI.print_banner()
    provider = SynapseContextProvider(repo_path)

    table = Table(title="⚡ Synapse Structural Intelligence Status", title_style="bold cyan")
    table.add_column("Property", style="bold white", width=26)
    table.add_column("Status / Value", style="cyan", width=46)

    cli_status = f"[bold green]Installed ({provider.cli_bin})[/bold green]" if provider.is_cli_available() else "[bold yellow]Not Found on PATH[/bold yellow]"
    table.add_row("Synapse CLI (`synap`)", cli_status)

    if provider.is_synapse_indexed() and provider.db_path:
        table.add_row("Database Index (`.synap/synap.db`)", f"[bold green]Found[/bold green] ({provider.db_path})")
        try:
            conn = sqlite3.connect(f"file:{provider.db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM symbols")
            sym_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM files")
            file_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM edges")
            edge_count = cur.fetchone()[0]
            conn.close()

            table.add_row("Indexed Files", str(file_count))
            table.add_row("Indexed Symbols (AST)", str(sym_count))
            table.add_row("Call Graph Edges", str(edge_count))
        except Exception as e:
            table.add_row("DB Stats Error", str(e))
    else:
        table.add_row("Database Index (`.synap/synap.db`)", "[dim]Not Indexed in this workspace[/dim]")

    console.print(table)
    if not provider.is_cli_available():
        console.print("\n[yellow]💡 Tip:[/yellow] Install Synapse to accelerate symbol search and reverse impact analysis:")
        console.print("   [bold cyan]pip install synap-git[/bold cyan]  or  [bold cyan]uv tool install synap-git[/bold cyan]")
        console.print("   Repository: [link=https://github.com/saahilpal/synapse]https://github.com/saahilpal/synapse[/link]")
    elif not provider.is_synapse_indexed():
        console.print("\n[yellow]💡 Tip:[/yellow] Index this repository to activate deep AST callgraphs:")
        console.print(f"   [bold cyan]synap init && synap index[/bold cyan] (or run [bold cyan]patchproof synapse index {repo_path}[/bold cyan])")


@synapse.command(name="install")
def synapse_install() -> None:
    """Guide or execute installation of the Synapse AST engine (synap-git)."""
    PatchProofUI.print_banner()
    console.print("[bold cyan]Installing Synapse Structural Retrieval Engine (by @saahilpal)...[/bold cyan]\n")
    console.print("Synapse powers PatchProof's caller-callee call graph traversal and impacted test prediction.")
    console.print("Repository: [bold cyan]https://github.com/saahilpal/synapse[/bold cyan]\n")

    try:
        console.print("Running [bold yellow]pip install synap-git[/bold yellow]...")
        subprocess.run([sys.executable, "-m", "pip", "install", "synap-git"], check=True, capture_output=True, text=True)
        console.print("[bold green]✓ Synapse successfully installed![/bold green]")
        console.print("Verify with: [cyan]synap --version[/cyan]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Installation failed:[/bold red] {e.stderr or e.stdout}")
        console.print("\nYou can install manually via:")
        console.print("  [cyan]pip install synap-git[/cyan]")
        console.print("  [cyan]uv tool install synap-git[/cyan]")


@synapse.command(name="index")
@click.argument("repo_path", type=click.Path(path_type=Path), default=Path("."))
def synapse_index(repo_path: Path) -> None:
    """Initialize and index a target repository using Synapse AST graph generator."""
    PatchProofUI.print_banner()
    synap_bin = shutil.which("synap")
    if not synap_bin:
        console.print("[bold red]Synapse CLI (`synap`) not found on PATH.[/bold red]")
        console.print("Run [bold cyan]patchproof synapse install[/bold cyan] or [bold cyan]pip install synap-git[/bold cyan] first.")
        return

    target = repo_path.resolve()
    console.print(f"Indexing target repository: [bold cyan]{target}[/bold cyan]")
    try:
        subprocess.run([synap_bin, "init", str(target)], check=False)
        subprocess.run([synap_bin, "index", str(target)], check=True)
        console.print("\n[bold green]✓ Repository successfully indexed by Synapse![/bold green]")
        console.print(f"Index created at: `{target / '.synap' / 'synap.db'}`")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Indexing failed:[/bold red] {e}")


@synapse.command(name="search")
@click.argument("query", type=str)
@click.option("--path", type=click.Path(path_type=Path), default=Path("."))
def synapse_search(query: str, path: Path) -> None:
    """Search for symbols, callers, and code elements via Synapse."""
    provider = SynapseContextProvider(path)
    result = provider.search_structural(query)
    console.print(result)


# ---------------------------------------------------------------------------
# Core Pipeline Execution (Diagnose, Repair, Run)
# ---------------------------------------------------------------------------

@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--cmd", default="pytest -v", help="Command to reproduce the failure.")
def diagnose(repo_path: Path, cmd: str) -> None:
    """Run deterministic reproduction and causal diagnosis without applying repairs."""
    PatchProofUI.print_banner()
    console.print(f"[bold cyan]Target Repository:[/bold cyan] {repo_path}")
    console.print(f"[bold cyan]Reproduction Command:[/bold cyan] {cmd}\n")

    guardrails = GuardrailEngine()
    guardrails.run_preflight(repo_path, settings.workspace_root)

    app = compile_patchproof_graph()
    initial_state = {
        "investigation_id": f"diag-{repo_path.name}",
        "repo_path": str(repo_path),
        "reproduce_cmd": cmd.split(),
        "attempt": 0,
        "max_attempts": 1,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)
    outcome = result.get("outcome")
    console.print(f"\n[bold green]Diagnosis Complete.[/bold green] Outcome: [bold yellow]{outcome}[/bold yellow]")
    if result.get("final_report_markdown"):
        console.print(result.get("final_report_markdown"))


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--cmd", default="pytest -v", help="Command to reproduce the failure.")
@click.option("--export-diff", type=click.Path(path_type=Path), default=None, help="File to export verified patch.")
@click.option("--max-retries", default=settings.max_retries, type=int, help="Maximum repair retry attempts.")
@click.option("--auto-approve/--no-auto-approve", default=True, help="Auto-approve verified patch when policy passes.")
def repair(repo_path: Path, cmd: str, export_diff: Path | None, max_retries: int, auto_approve: bool) -> None:
    """Run full 9-stage pipeline: reproduction, investigation, repair, verification & approval."""
    PatchProofUI.print_banner()
    console.print(f"[bold cyan]Target Repository:[/bold cyan] {repo_path}")
    console.print(f"[bold cyan]Reproduction Command:[/bold cyan] {cmd}\n")

    guardrails = GuardrailEngine()
    guardrails.run_preflight(repo_path, settings.workspace_root)

    app = compile_patchproof_graph()
    initial_state = {
        "investigation_id": f"rep-{repo_path.name}",
        "repo_path": str(repo_path),
        "reproduce_cmd": cmd.split(),
        "attempt": 0,
        "max_attempts": max_retries,
        "auto_approve": auto_approve,
        "export_path": str(export_diff) if export_diff else None,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    record = result.get("verification_record")
    diff = result.get("canonical_diff", "")
    if record:
        PatchProofUI.print_verification_badge(record)
    if diff:
        PatchProofUI.render_diff(diff)

    outcome = result.get("outcome")
    console.print(f"\n[bold green]Pipeline Terminated.[/bold green] Final Outcome: [bold cyan]{outcome}[/bold cyan]")
    if result.get("patch_digest"):
        console.print(f"[bold yellow]Verified Patch Digest:[/bold yellow] `{result.get('patch_digest')}`")
    if result.get("approval_signature"):
        console.print(f"[bold yellow]Approval Signature:[/bold yellow] `{result.get('approval_signature')}`")
    if result.get("exported_patch_path"):
        console.print(f"[bold green]Patch Exported To:[/bold green] `{result.get('exported_patch_path')}`")


@main.command(name="run")
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--cmd", default="pytest -v", help="Command to reproduce the failure.")
@click.option("--export-diff", type=click.Path(path_type=Path), default=None, help="File to export verified patch.")
@click.pass_context
def run_alias(ctx: click.Context, repo_path: Path, cmd: str, export_diff: Path | None) -> None:
    """Alias for repair command."""
    ctx.forward(repair)


# ---------------------------------------------------------------------------
# GitHub Subsystem (gh solve, gh review)
# ---------------------------------------------------------------------------

@main.group()
def gh() -> None:
    """GitHub integrations: solve issues, review pull requests, and post audit proofs."""
    pass


@gh.command(name="solve")
@click.argument("issue_ref", type=str)
@click.option("--cmd", default=None, help="Reproduction test command (inferred from issue if omitted)")
@click.option("--auto-pr/--no-auto-pr", default=True, help="Open a verified pull request upon success")
@click.option("--branch", default=None, help="Custom head branch name for PR")
def gh_solve(issue_ref: str, cmd: str | None, auto_pr: bool, branch: str | None) -> None:
    """Autonomous issue solver: clone repo, reproduce, repair, verify, and open verified PR."""
    PatchProofUI.print_banner()

    # Parse issue reference: "owner/repo#123" or "owner/repo/issues/123"
    match = re.search(r"([^/#\s]+/[^/#\s]+)(?:#|/issues/)?(\d+)?", issue_ref)
    if not match or not match.group(2):
        console.print("[bold red]Invalid issue reference.[/bold red] Use format: [cyan]owner/repo#123[/cyan]")
        return

    owner_repo = match.group(1)
    issue_number = int(match.group(2))

    client = GitHubClient()
    if not client.is_authenticated():
        console.print("[bold red]GitHub CLI not authenticated.[/bold red] Run [yellow]gh auth login[/yellow] first.")
        return

    console.print(f"[bold cyan]Fetching Issue:[/bold cyan] {owner_repo}#{issue_number}")
    try:
        issue = client.fetch_issue(owner_repo, issue_number)
        console.print(f"[bold white]{issue.title}[/bold white] (Author: @{issue.author})\n")
    except GitHubClientError as e:
        console.print(f"[bold red]Failed to fetch issue:[/bold red] {e}")
        return

    # Infer test reproduction command
    test_cmd = cmd
    if not test_cmd:
        if issue.reproduction_hints:
            test_cmd = issue.reproduction_hints[0]
            console.print(f"[dim]Inferred reproduction command from issue:[/dim] [yellow]{test_cmd}[/yellow]")
        else:
            test_cmd = "pytest -v"
            console.print(f"[dim]Defaulting reproduction command to:[/dim] [yellow]{test_cmd}[/yellow]")

    # Clone repository to ephemeral sandbox
    clone_target = settings.workspace_root / f"gh-{owner_repo.replace('/', '-')}-issue-{issue_number}"
    console.print(f"[bold cyan]Cloning Repository:[/bold cyan] {owner_repo} -> {clone_target}...")
    client.clone_repo(owner_repo, clone_target)

    # Execute LangGraph Pipeline
    app = compile_patchproof_graph()
    initial_state = {
        "investigation_id": f"gh-{issue_number}",
        "repo_path": str(clone_target),
        "reproduce_cmd": test_cmd.split(),
        "attempt": 0,
        "max_attempts": settings.max_retries,
        "auto_approve": True,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    record = result.get("verification_record")
    diff = result.get("canonical_diff", "")
    outcome = result.get("outcome")

    if record:
        PatchProofUI.print_verification_badge(record)
    if diff:
        PatchProofUI.render_diff(diff)

    if outcome == OutcomeResult.VERIFIED_EXPORTED and auto_pr and diff:
        pr_branch = branch or f"patchproof/fix-issue-{issue_number}"
        commit_msg = f"fix: resolve {owner_repo}#{issue_number} (verified by PatchProof)"
        digest = str(result.get("patch_digest", ""))
        signature = str(result.get("approval_signature", ""))

        console.print(f"\n[bold green]Pushing verified fix branch:[/bold green] `{pr_branch}`...")
        try:
            client.create_and_push_branch(clone_target, pr_branch, commit_msg, diff, signature)

            # Build rich PR description
            claims = result.get("claims", [])
            claims_table_lines = ["| Claim ID | Type | Confidence | Statement |", "| :--- | :--- | :--- | :--- |"]
            for c in claims:
                claims_table_lines.append(f"| `{c.claim_id}` | `{c.claim_type.value}` | {c.confidence} | {c.statement} |")

            pr_body = GitHubClient.format_pr_body(
                investigation_id=f"gh-{issue_number}",
                issue_number=issue_number,
                verification_level=record.level.value if record else "V3",
                patch_digest=digest,
                approval_signature=signature,
                claims_markdown="\n".join(claims_table_lines),
            )

            pr_title = f"fix: resolve #{issue_number} - {issue.title[:60]}"
            pr_url = client.create_pull_request(clone_target, pr_title, pr_body, head_branch=pr_branch)
            console.print(f"\n[bold green]🎉 Verified Pull Request Created:[/bold green] [bold cyan]{pr_url}[/bold cyan]")
        except Exception as e:
            console.print(f"[bold red]Failed to create PR:[/bold red] {e}")
    else:
        console.print(f"\n[bold yellow]Outcome:[/bold yellow] {outcome}")


@gh.command(name="review")
@click.argument("pr_ref", type=str)
@click.option("--cmd", default="pytest -v", help="Verification command to execute against PR")
def gh_review(pr_ref: str, cmd: str) -> None:
    """Review and verify an incoming PR with anti-cheat checks and test oracles."""
    PatchProofUI.print_banner()

    match = re.search(r"([^/#\s]+/[^/#\s]+)(?:#|/pull/)?(\d+)?", pr_ref)
    if not match or not match.group(2):
        console.print("[bold red]Invalid PR reference.[/bold red] Use format: [cyan]owner/repo#42[/cyan]")
        return

    owner_repo = match.group(1)
    pr_number = int(match.group(2))

    client = GitHubClient()
    console.print(f"[bold cyan]Inspecting PR:[/bold cyan] {owner_repo}#{pr_number}")
    try:
        pr = client.fetch_pr(owner_repo, pr_number)
        console.print(f"[bold white]{pr.title}[/bold white] (Head branch: `{pr.head_branch}`)\n")
    except GitHubClientError as e:
        console.print(f"[bold red]Failed to fetch PR:[/bold red] {e}")
        return

    clone_target = settings.workspace_root / f"gh-{owner_repo.replace('/', '-')}-pr-{pr_number}"
    console.print(f"[bold cyan]Cloning PR Head Branch:[/bold cyan] `{pr.head_branch}`...")
    client.clone_repo(owner_repo, clone_target, ref=pr.head_branch)

    # Run verification pipeline
    app = compile_patchproof_graph()
    initial_state = {
        "investigation_id": f"gh-pr-{pr_number}",
        "repo_path": str(clone_target),
        "reproduce_cmd": cmd.split(),
        "attempt": 0,
        "max_attempts": 1,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)
    record = result.get("verification_record")
    if record:
        PatchProofUI.print_verification_badge(record)

    verdict_badge = f"Verified `{record.level.value}`" if (record and record.level != VerificationLevel.V0_FAILED) else "Verification Failed"
    console.print(f"\n[bold green]Review Complete.[/bold green] Verdict: [bold yellow]{verdict_badge}[/bold yellow]")


# ---------------------------------------------------------------------------
# Inspect Subsystem (symbols, journal)
# ---------------------------------------------------------------------------

@main.group()
def inspect() -> None:
    """Inspect AST symbols, call graphs, or cryptographic audit logs."""
    pass


@inspect.command(name="symbols")
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("query", type=str)
def inspect_symbols(repo_path: Path, query: str) -> None:
    """Look up symbol definition in repository using Synapse/Standard provider."""
    provider: ContextProvider = SynapseContextProvider(repo_path) if (repo_path / ".synap" / "synap.db").exists() else StandardContextProvider(repo_path)
    console.print(f"Using provider: [bold cyan]{provider.name}[/bold cyan]")
    syms = provider.find_symbol_definitions(query)
    if syms:
        sym = syms[0]
        console.print(f"[bold green]Found:[/bold green] `{sym.symbol_name}` ({sym.kind}) in [bold yellow]{sym.file_path}:{sym.line_start}-{sym.line_end}[/bold yellow]")
    else:
        console.print(f"[yellow]No symbol found matching '{query}'.[/yellow]")


@inspect.command(name="journal")
@click.option("--journal", type=click.Path(path_type=Path), default=settings.audit_journal_path, help="Path to audit journal.")
def inspect_journal(journal: Path) -> None:
    """Inspect the cryptographic hash-chained audit journal."""
    if not journal.exists():
        console.print(f"[yellow]No journal found at {journal}[/yellow]")
        return

    lines = journal.read_text(encoding="utf-8").splitlines()
    console.print(f"[bold cyan]Audit Journal:[/bold cyan] {journal} ({len(lines)} records)\n")
    for idx, line in enumerate(lines, 1):
        record = json.loads(line)
        console.print(f"[[bold cyan]#{idx}[/bold cyan]] [yellow]{record.get('event_type')}[/yellow] - Hash: `{record.get('entry_hash', '')[:16]}...`")
        console.print(f"     Payload: {json.dumps(record.get('payload', {}))}")


# ---------------------------------------------------------------------------
# Eval Subsystem (run, inject)
# ---------------------------------------------------------------------------

@main.group()
def eval() -> None:
    """Evaluation benchmark runner and synthetic bug injector."""
    pass


@eval.command(name="run")
@click.option("--dataset", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True, help="Path to JSONL benchmark dataset.")
@click.option("--arm", default="patchproof-v1.1-spine", help="Name of evaluation arm.")
def eval_run(dataset: Path, arm: str) -> None:
    """Run benchmark evaluation suite across test fixtures."""
    PatchProofUI.print_banner()
    console.print(f"[bold magenta]Running Benchmark Suite:[/bold magenta] {dataset}")
    console.print(f"[bold magenta]Evaluation Arm:[/bold magenta] {arm}\n")

    fixtures = DatasetLoader.load_jsonl(dataset)
    console.print(f"Loaded [bold green]{len(fixtures)}[/bold green] benchmark fixtures.")

    runner = BenchmarkRunner(arm_name=arm)
    summary = runner.run_suite(fixtures)

    EvalReporter.print_summary_table(summary)


@eval.command(name="inject")
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--target", required=True, help="Target relative source file to mutate.")
@click.option("--cmd", default="pytest -v", help="Test command to validate bug reproduction.")
@click.option("--output", type=click.Path(path_type=Path), default=Path("injected_fixture.json"), help="Output fixture file.")
def eval_inject(repo_path: Path, target: str, cmd: str, output: Path) -> None:
    """Inject a validated synthetic bug into a clean repository."""
    PatchProofUI.print_banner()
    console.print(f"Injecting validated mutation into [bold cyan]{target}[/bold cyan]...")

    mutator = SyntheticMutator(repo_path)
    fixture = mutator.inject_validated_bug(
        fixture_id=f"synth-{Path(target).stem}",
        target_rel_path=target,
        test_command=cmd.split(),
    )

    if fixture:
        output.write_text(fixture.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[bold green]✓ Synthetic bug injected and validated![/bold green] Saved to {output}")
    else:
        console.print("[bold red]✗ Could not find a mutation that cleanly flips existing tests to FAIL.[/bold red]")


if __name__ == "__main__":
    main()
