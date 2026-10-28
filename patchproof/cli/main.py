"""Command-line interface for PatchProof v1.1."""

import json
from pathlib import Path

import click

from patchproof import __version__
from patchproof.config import settings
from patchproof.context.base import ContextProvider
from patchproof.context.standard import StandardContextProvider
from patchproof.context.synapse import SynapseContextProvider
from patchproof.core.models import ProcessStatus
from patchproof.eval.datasets import DatasetLoader
from patchproof.eval.mutator import SyntheticMutator
from patchproof.eval.report import EvalReporter
from patchproof.eval.runner import BenchmarkRunner
from patchproof.graph.workflow import compile_patchproof_graph
from patchproof.guardrails.engine import GuardrailEngine
from patchproof.ui.console import PatchProofUI, console


@click.group()
@click.version_option(version=__version__, prog_name="patchproof")
def main() -> None:
    """PatchProof: Deterministic Trust Boundary & Bounded AI Repair Engine."""
    pass


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--cmd", default="pytest -v", help="Command to reproduce the failure.")
def diagnose(repo_path: Path, cmd: str) -> None:
    """Run deterministic reproduction and causal diagnosis without applying repairs."""
    PatchProofUI.print_banner()
    console.print(f"[bold cyan]Target Repository:[/bold cyan] {repo_path}")
    console.print(f"[bold cyan]Reproduction Command:[/bold cyan] {cmd}\n")

    # 1. Run Pre-flight Guardrails
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

    # 1. Run Pre-flight Guardrails
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

    # 2. Render Verification Badges and Diffs
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
