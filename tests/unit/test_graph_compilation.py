"""Unit tests for LangGraph 9-stage graph compilation."""

from patchbound.graph.workflow import compile_patchbound_graph, create_patchbound_graph


def test_graph_structure() -> None:
    workflow = create_patchbound_graph()
    assert "snapshot_reproduce" in workflow.nodes
    assert "parse_triage" in workflow.nodes
    assert "repairability_gate" in workflow.nodes
    assert "investigator" in workflow.nodes
    assert "fixer" in workflow.nodes
    assert "patch_verify" in workflow.nodes
    assert "review" in workflow.nodes
    assert "human_approval" in workflow.nodes
    assert "export_report" in workflow.nodes


def test_graph_compilation() -> None:
    app = compile_patchbound_graph()
    assert app is not None
