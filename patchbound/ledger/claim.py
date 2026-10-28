"""Cryptographic claim ledger data models and typed claims."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ClaimType(StrEnum):
    """Epistemological claim categories."""

    OBSERVED = "observed"  # Raw facts observed directly from deterministic execution
    DERIVED = "derived"  # Deterministically computed from observed facts (e.g. git blame, diff)
    INFERRED = "inferred"  # LLM hypothesis corroborated by interventional experiment
    ASSUMED = "assumed"  # Unverified heuristic or assumption (carries warning)


class CodeCitation(BaseModel):
    """Citation pointing to exact source code at a specific tree hash."""

    file_path: str
    line_start: int
    line_end: int
    tree_hash: str
    exact_quote: str


class ClaimItem(BaseModel):
    """An individual audited claim in the investigation report."""

    claim_id: str
    claim_type: ClaimType
    statement: str
    confidence: str = "medium"  # low, medium, high
    evidence_ids: list[str] = Field(default_factory=list)
    citations: list[CodeCitation] = Field(default_factory=list)
    experiment_id: str | None = None
