"""Command-line interface for PatchProof v1.1."""

from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from patchproof import __version__
from patchproof.config import settings
from patchproof.core.models import ProcessStatus
from patchproof.graph.workflow import compile_patchproof_graph

console = Console()


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
    console.print(Panel(f"[bold green]PatchProof Diagnosis[/bold green]\nTarget: {repo_path}\nCommand: {cmd}"))
    
    app = compile_patchproof_graph()
    initial_state = {
        "investigation_id": "diag-001",
        "repo_path": str(repo_path),
        "reproduce_cmd": cmd.split(),
        "attempt": 0,
        "max_attempts": 1,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)
    console.print(f"[bold cyan]Outcome:[/bold cyan] {result.get('outcome')}")
    if result.get("final_report_markdown"):
        console.print(result.get("final_report_markdown"))


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--cmd", default="pytest -v", help="Command to reproduce the failure.")
def repair(repo_path: Path, cmd: str) -> None:
    """Run full 9-stage pipeline: reproduction, investigation, repair, verification & approval."""
    console.print(Panel(f"[bold green]PatchProof Repair Pipeline[/bold green]\nTarget: {repo_path}\nCommand: {cmd}"))

    app = compile_patchproof_graph()
    initial_state = {
        "investigation_id": "rep-001",
        "repo_path": str(repo_path),
        "reproduce_cmd": cmd.split(),
        "attempt": 0,
        "max_attempts": settings.max_retries,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)
    console.print(f"[bold cyan]Outcome:[/bold cyan] {result.get('outcome')}")
    if result.get("patch_digest"):
        console.print(f"[bold yellow]Patch Digest:[/bold yellow] {result.get('patch_digest')}")


if __name__ == "__main__":
    main()
