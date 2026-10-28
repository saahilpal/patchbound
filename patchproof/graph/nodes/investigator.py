"""Stage 4: Investigator (Bounded Causal Investigation Loop)."""

import subprocess
from pathlib import Path
from typing import Any

from patchproof.context.base import ContextProvider
from patchproof.context.standard import StandardContextProvider
from patchproof.context.synapse import SynapseContextProvider
from patchproof.core.models import ProcessStatus
from patchproof.graph.state import PatchProofState
from patchproof.ledger.claim import ClaimItem, ClaimType, CodeCitation
from patchproof.ledger.validator import CitationFabricationError, GroundingValidator


def _get_context_provider(repo_path: Path) -> ContextProvider:
    """Select the best available context provider (preferring Synapse if available)."""
    synapse_db = repo_path / ".synap" / "synap.db"
    if synapse_db.exists():
        return SynapseContextProvider(repo_path)
    return StandardContextProvider(repo_path)


def _get_git_head(repo_path: Path) -> str:
    """Retrieve current commit SHA of the repository."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return out
    except Exception:
        return "0" * 40


def investigator_node(state: PatchProofState) -> dict[str, Any]:
    """Stage 4: Investigate root cause using AST context, causal hypotheses, and the Claim Ledger."""
    repo_path = Path(str(state.get("repo_path", "."))).resolve()
    active_sig = state.get("active_failure_signature")
    attempt = int(state.get("attempt", 0))
    failure_delta = state.get("failure_delta")
    f2p = state.get("f2p_test_ids", [])
    test_id = active_sig.test_id if active_sig else (f2p[0] if f2p else "unknown")

    context_provider = _get_context_provider(repo_path)
    head_sha = _get_git_head(repo_path)

    new_claims: list[ClaimItem] = []
    new_hypotheses: list[str] = []

    # 1. OBSERVED: Baseline failure claim
    obs_claim = ClaimItem(
        claim_id=f"CLM-OBS-{attempt}",
        claim_type=ClaimType.OBSERVED,
        statement=f"Test '{test_id}' failed with {active_sig.error_type if active_sig else 'error'}: {active_sig.normalized_message if active_sig else 'non-zero exit'}.",
        evidence_ids=[f"EV-BASELINE-ATT-{attempt}"],
        confidence="high",
    )
    new_claims.append(obs_claim)

    # 2. DERIVED: AST and Symbol definition discovery
    symbol_name = ""
    target_file = ""
    exact_quote = ""
    line_start = 1
    line_end = 1

    # Attempt to locate target symbol from stack frame, test id, or failure signature
    candidates: list[str] = []

    # 1. Top stack frame function if non-test
    if active_sig and active_sig.top_frame and active_sig.top_frame.function_name:
        fn = active_sig.top_frame.function_name
        if not fn.startswith("test_") and fn != "<module>" and not fn.endswith("Error"):
            candidates.append(fn)

    # 2. Test ID symbol (e.g. tests/test_calc.py::test_subtract -> subtract)
    if test_id and "::" in test_id:
        fn_part = test_id.split("::")[-1]
        if fn_part.startswith("test_"):
            candidates.append(fn_part[5:])
        else:
            candidates.append(fn_part)

    # 3. Clean tokens from failure message excluding common python exceptions
    if active_sig and active_sig.normalized_message:
        ignored = {
            "assertionerror", "typeerror", "valueerror", "indexerror", "keyerror",
            "zerodivisionerror", "failed", "assert", "where", "expected", "got", "true", "false", "none"
        }
        for w in active_sig.normalized_message.split():
            clean_w = w.strip("(),:'\"[]{}")
            if len(clean_w) > 2 and clean_w.lower() not in ignored and clean_w.isidentifier():
                candidates.append(clean_w)

    for cand in candidates:
        sym_defs = context_provider.find_symbol_definitions(cand)
        if sym_defs:
            # Prefer definitions in implementation files over test files
            non_test_defs = [s for s in sym_defs if not s.file_path.startswith("test")]
            sym_def = non_test_defs[0] if non_test_defs else sym_defs[0]
            symbol_name = sym_def.symbol_name
            target_file = sym_def.file_path
            line_start = sym_def.line_start
            line_end = sym_def.line_end
            exact_quote = sym_def.symbol_name
            break

    # If symbol was located, construct a grounded citation
    if target_file and head_sha != "0" * 40:
        citation = CodeCitation(
            file_path=target_file,
            line_start=line_start,
            line_end=line_end,
            tree_hash=head_sha,
            exact_quote=exact_quote,
        )
        der_claim = ClaimItem(
            claim_id=f"CLM-DER-{attempt}",
            claim_type=ClaimType.DERIVED,
            statement=f"Symbol '{symbol_name}' identified at {target_file}:{line_start}-{line_end} via {context_provider.name}.",
            evidence_ids=[f"EV-AST-ATT-{attempt}"],
            citations=[citation],
            confidence="high",
        )
        # Attempt mechanical citation validation against git tree
        try:
            validator = GroundingValidator(repo_path)
            validator.validate_claim(der_claim)
            new_claims.append(der_claim)
        except CitationFabricationError:
            # If quote did not match exactly, downgrade without citation
            der_claim.citations = []
            der_claim.confidence = "medium"
            new_claims.append(der_claim)
        except Exception:
            der_claim.citations = []
            new_claims.append(der_claim)

    # 3. INFERRED: Evolving causal hypothesis based on attempts and failure delta
    if attempt > 0 and failure_delta:
        if failure_delta.delta_type == "SAME_FAILURE":
            hypo = (
                f"Attempt {attempt} Hypothesis: Prior patch failed to flip {test_id} to pass. "
                f"Root cause requires alternative branch or return value adjustment in {target_file or test_id}."
            )
        elif failure_delta.delta_type == "POLICY_OR_APPLICATION_ERROR":
            hypo = (
                f"Attempt {attempt} Hypothesis: Prior patch triggered rejection: {failure_delta.guidance}. "
                f"Next repair must strictly anchor in non-protected implementation files."
            )
        else:
            hypo = (
                f"Attempt {attempt} Hypothesis: Addressing failure delta '{failure_delta.delta_type}' "
                f"with refined logic in {target_file or 'target implementation'}."
            )
    else:
        hypo = f"Hypothesis 1: Root cause of {test_id} is located in {target_file or 'the implementation under test'}."

    new_hypotheses.append(hypo)

    inf_claim = ClaimItem(
        claim_id=f"CLM-INF-{attempt}",
        claim_type=ClaimType.INFERRED,
        statement=hypo,
        evidence_ids=[f"EV-HYPO-ATT-{attempt}"],
        confidence="medium" if attempt == 0 else "high",
    )
    new_claims.append(inf_claim)

    return {
        "status": ProcessStatus.INVESTIGATING,
        "hypotheses": new_hypotheses,
        "claims": new_claims,
        "evidence_ids": [f"EV-ATTEMPT-{attempt}-01"],
    }
