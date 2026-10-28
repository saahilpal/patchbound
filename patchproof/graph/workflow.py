"""LangGraph 9-stage StateGraph compilation and transition logic."""

from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from patchproof.core.models import ProcessStatus, VerificationLevel
from patchproof.graph.nodes.export_report import export_report_node
from patchproof.graph.nodes.fixer import fixer_node
from patchproof.graph.nodes.human_approval import human_approval_node
from patchproof.graph.nodes.investigator import investigator_node
from patchproof.graph.nodes.parse_triage import parse_triage_node
from patchproof.graph.nodes.patch_verify import patch_verify_node
from patchproof.graph.nodes.repairability_gate import repairability_gate_node
from patchproof.graph.nodes.review import review_node
from patchproof.graph.nodes.snapshot_reproduce import snapshot_reproduce_node
from patchproof.graph.state import PatchProofState


def check_repairability_route(state: PatchProofState) -> str:
    """Route after repairability gate."""
    if state.get("status") == ProcessStatus.TERMINATED:
        return "export_report"
    return "investigator"


def check_verification_route(state: PatchProofState) -> str:
    """Route after patch verification."""
    record = state.get("verification_record")
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 2)

    if record and record.level != VerificationLevel.V0_FAILED:
        return "review"

    if attempt < max_attempts:
        return "investigator"

    return "export_report"


def check_review_route(state: PatchProofState) -> str:
    """Route after blind review."""
    if state.get("review_status") == "approved":
        return "human_approval"
    return "investigator"


def check_approval_route(state: PatchProofState) -> str:
    """Route after human approval."""
    if state.get("human_approved", False):
        return "export_report"
    return END


def create_patchproof_graph() -> StateGraph[PatchProofState, Any, Any, Any]:
    """Construct and configure the LangGraph 9-stage workflow."""
    workflow = StateGraph(PatchProofState)

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
        {"human_approval": "human_approval", "investigator": "investigator"},
    )

    workflow.add_conditional_edges(
        "human_approval",
        check_approval_route,
        {"export_report": "export_report", END: END},
    )

    workflow.add_edge("export_report", END)

    return workflow


def compile_patchproof_graph() -> CompiledStateGraph[PatchProofState, Any, Any, Any]:
    """Compile executable LangGraph workflow."""
    return create_patchproof_graph().compile()
