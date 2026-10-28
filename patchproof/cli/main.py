"""Command-line interface for PatchProof v1.1."""

import json
import re
from pathlib import Path

import click

from patchproof import __version__
from patchproof.cli.setup import SetupManager
from patchproof.config import settings
from patchproof.context.base import ContextProvider
from patchproof.context.standard import StandardContextProvider
from patchproof.context.synapse import SynapseContextProvider
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
