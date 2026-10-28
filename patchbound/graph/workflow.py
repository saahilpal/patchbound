"""LangGraph 9-stage StateGraph compilation and transition logic."""

from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from patchbound.core.models import ProcessStatus, VerificationLevel
from patchbound.graph.nodes.export_report import export_report_node
from patchbound.graph.nodes.fixer import fixer_node
from patchbound.graph.nodes.human_approval import human_approval_node
from patchbound.graph.nodes.investigator import investigator_node
from patchbound.graph.nodes.parse_triage import parse_triage_node
from patchbound.graph.nodes.patch_verify import patch_verify_node
from patchbound.graph.nodes.repairability_gate import repairability_gate_node
from patchbound.graph.nodes.review import review_node
from patchbound.graph.nodes.snapshot_reproduce import snapshot_reproduce_node
from patchbound.graph.state import PatchBoundState


def check_repairability_route(state: PatchBoundState) -> str:
    """Route after repairability gate."""
    if state.get("status") == ProcessStatus.TERMINATED:
        return "export_report"
    return "investigator"


def check_verification_route(state: PatchBoundState) -> str:
    """Route after patch verification."""
    record = state.get("verification_record")
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 2)

    if record and record.level != VerificationLevel.V0_FAILED:
        return "review"

    if attempt < max_attempts:
        return "investigator"

    return "export_report"


def check_review_route(state: PatchBoundState) -> str:
    """Route after blind review."""
    attempt = int(state.get("attempt", 0))
    max_attempts = int(state.get("max_attempts", 2))
    if state.get("review_status") == "approved":
        return "human_approval"
    if attempt < max_attempts:
        return "investigator"
    return "export_report"


def check_approval_route(state: PatchBoundState) -> str:
    """Route after human approval."""
    return "export_report"


def create_patchbound_graph() -> StateGraph[PatchBoundState, Any, Any, Any]:
    """Construct and configure the LangGraph 9-stage workflow."""
    workflow = StateGraph(PatchBoundState)

    # 1. Register all 9 nodes
    workflow.add_node("snapshot_reproduce", snapshot_reproduce_node)
    workflow.add_node("parse_triage", parse_triage_node)
    workflow.add_node("repairability_gate", repairability_gate_node)
    workflow.add_node("investigator", investigator_node)
    workflow.add_node("fixer", fixer_node)
    workflow.add_node("patch_verify", patch_verify_node)
    workflow.add_node("review", review_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("export_report", export_report_node)

    # 2. Add deterministic linear and conditional edges
    workflow.set_entry_point("snapshot_reproduce")
    workflow.add_edge("snapshot_reproduce", "parse_triage")
    workflow.add_edge("parse_triage", "repairability_gate")

    workflow.add_conditional_edges(
        "repairability_gate",
        check_repairability_route,
        {"investigator": "investigator", "export_report": "export_report"},
    )

    workflow.add_edge("investigator", "fixer")
    workflow.add_edge("fixer", "patch_verify")

    workflow.add_conditional_edges(
        "patch_verify",
        check_verification_route,
        {"review": "review", "investigator": "investigator", "export_report": "export_report"},
    )

    workflow.add_conditional_edges(
        "review",
        check_review_route,
        {
            "human_approval": "human_approval",
            "investigator": "investigator",
            "export_report": "export_report",
        },
    )

    workflow.add_conditional_edges(
        "human_approval",
        check_approval_route,
        {"export_report": "export_report"},
    )

    workflow.add_edge("export_report", END)

    return workflow


def compile_patchbound_graph() -> CompiledStateGraph[PatchBoundState, Any, Any, Any]:
    """Compile executable LangGraph workflow."""
    return create_patchbound_graph().compile()
