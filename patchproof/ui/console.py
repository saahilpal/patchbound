"""Modern Rich terminal UI components, status boards, and interactive prompts."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from patchproof.core.models import VerificationLevel, VerificationRecord

console = Console()


class PatchProofUI:
    """Delivers a high-polish developer experience via rich terminal components."""

    @staticmethod
    def print_banner() -> None:
        """Render PatchProof header banner."""
        banner_text = (
            "[bold white on blue] PatchProof v1.1 [/bold white on blue] "
            "[dim]· Deterministic Trust Boundary & Bounded AI Repair[/dim]"
        )
        console.print(Panel(banner_text, border_style="blue", expand=False))

    @staticmethod
    def print_stage_start(stage_num: int, stage_name: str, kind: str) -> None:
        """Print stage execution header."""
        color = "cyan" if "Deterministic" in kind else "magenta"
        console.print(f"\n[bold {color}]▶ Stage {stage_num}: {stage_name}[/bold {color}] [dim]({kind})[/dim]")

    @staticmethod
    def print_verification_badge(record: VerificationRecord) -> None:
        """Render verification level badge and metrics table."""
        level_colors = {
            VerificationLevel.V3_CI_CLEAN: "bold green on black",
            VerificationLevel.V2_IMPACT: "bold blue on black",
            VerificationLevel.V1_TARGET: "bold yellow on black",
            VerificationLevel.V0_FAILED: "bold red on black",
        }
        style = level_colors.get(record.level, "white")
        badge = f"[{style}]  VERIFICATION LEVEL: {record.level.value}  [/{style}]"

        table = Table(title="Verification Summary", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="bold")

        table.add_row("Outcome Level", badge)
        table.add_row("F2P Tests Flipped", f"[green]{len(record.f2p_passed)} passed[/green] / {len(record.f2p_executed)} total")
        table.add_row("P2P Regressions", f"[red]{len(record.p2p_regressed)}[/red]" if record.p2p_regressed else "[green]0 (Clean)[/green]")
        table.add_row("Tests Skipped Delta", str(record.total_skipped))
        table.add_row("Flake-Checked", "✓ Yes" if record.flags.flake_checked else "✗ No")
        table.add_row("Oracle Integrity (Pinned)", "✓ Verified" if record.flags.pinned_tests else "✗ Modified")
        table.add_row("Policy Clean", "✓ Yes" if record.flags.policy_clean else "✗ Violations")
        table.add_row("Patch Digest", f"`{record.patch_digest[:16]}...`" if record.patch_digest else "N/A")

        console.print(table)

    @staticmethod
    def render_diff(canonical_diff: str) -> None:
        """Render syntax-highlighted git diff."""
        if not canonical_diff:
            console.print("[dim]No diff generated.[/dim]")
            return
        syntax = Syntax(canonical_diff, "diff", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="[bold]Canonical Patch Diff[/bold]", border_style="yellow"))

    @staticmethod
    def prompt_human_approval(record: VerificationRecord, canonical_diff: str) -> bool:
        """Interactive terminal prompt for Human-in-the-Loop approval."""
        PatchProofUI.render_diff(canonical_diff)
        console.print("\n[bold yellow]⚠ HUMAN APPROVAL REQUIRED (Stage 8 Gate)[/bold yellow]")
        console.print(f"Patch is verified at level [bold green]{record.level.value}[/bold green].")
        console.print("[dim]Approval cryptographically binds your decision to the patch digest and policy.[/dim]\n")

        from rich.prompt import Confirm
        return Confirm.ask("[bold]Do you approve this patch for export?[/bold]", default=True)
