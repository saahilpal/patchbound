"""Benchmark comparison table renderer and evaluation export."""

from rich.table import Table

from patchproof.eval.metrics import EvalMetricsSummary
from patchproof.ui.console import console


class EvalReporter:
    """Renders evaluation summaries and multi-arm comparative benchmarks."""

    @staticmethod
    def print_summary_table(summary: EvalMetricsSummary) -> None:
        """Render terminal table for an evaluation arm."""
        table = Table(
            title=f"Evaluation Results: {summary.arm_name}",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Benchmark Metric", style="dim")
        table.add_column("Score / Count", style="bold")
        table.add_column("Safety / Target", style="cyan")

        fvr_style = "green" if summary.false_verified_rate < 0.01 else "red"
        table.add_row("Total Fixtures Evaluated", str(summary.total_fixtures), "N/A")
        table.add_row("Verified Clean (Level V3)", f"[green]{summary.verified_v3_count}[/green] ({summary.resolution_rate_v3:.1%})", "Maximize")
        table.add_row("Verified Impact (Level V2)", str(summary.verified_v2_count), "Target")
        table.add_row(
            "False-Verified Rate (FVR)",
            f"[{fvr_style}]{summary.false_verified_rate:.2%} [95% CI: {summary.fvr_ci_lower:.2%} - {summary.fvr_ci_upper:.2%}][/{fvr_style}]",
            "< 1.0% (Hard Bound)",
        )
        table.add_row("Abstention Precision", f"{summary.abstention_precision:.1%}", "> 90%")
        table.add_row("Avg Cost / Verified Fix", f"${summary.cost_per_verified_fix:.3f}", "Cost Efficiency")
        table.add_row("Mean Latency", f"{summary.mean_duration_seconds:.2f}s", "Latency")

        console.print(table)

    @staticmethod
    def render_markdown_comparison(summaries: list[EvalMetricsSummary]) -> str:
        """Render side-by-side markdown table comparing multiple evaluation arms."""
        lines = [
            "# PatchProof Benchmark Comparative Evaluation",
            "",
            "| Evaluation Arm | Total | V3 Resolved (%) | False-Verified Rate (FVR) | Cost / Fix ($) | Latency (s) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for s in summaries:
            lines.append(
                f"| **{s.arm_name}** | {s.total_fixtures} | {s.resolution_rate_v3:.1%} | "
                f"**{s.false_verified_rate:.2%}** [{s.fvr_ci_lower:.1%}, {s.fvr_ci_upper:.1%}] | "
                f"${s.cost_per_verified_fix:.3f} | {s.mean_duration_seconds:.1f}s |"
            )
        lines.append("")
        return "\n".join(lines)
