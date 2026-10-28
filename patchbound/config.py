"""PatchBound configuration and environment settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for PatchBound."""

    model_config = SettingsConfigDict(
        env_prefix="PATCHBOUND_",
        env_file=".env",
        extra="ignore",
    )

    # Core paths
    workspace_root: Path = Field(
        default=Path("/tmp/patchbound-workspaces"),
        description="Base scratch directory for ephemeral clones",
    )
    cas_storage_dir: Path = Field(
        default=Path("/tmp/patchbound-cas"),
        description="Content-addressed storage directory",
    )
    policy_file: Path = Field(
        default=Path("policy.yaml"),
        description="Path to default security and repair policy",
    )

    # Model configuration
    model_fast: str = Field(
        default="gemini-1.5-flash", description="Fast model for triage/summaries"
    )
    model_strong: str = Field(
        default="gemini-1.5-pro", description="Strong model for Investigator and Fixer"
    )
    model_reviewer: str = Field(
        default="gemini-1.5-pro", description="Model configuration for blind review"
    )

    # Budgets
    max_retries: int = Field(default=2, description="Maximum patch verification retry attempts")
    max_investigator_steps: int = Field(
        default=12, description="Step budget for Investigator agent loop"
    )
    max_tokens_total: int = Field(default=150_000, description="Hard token budget cap per run")
    timeout_seconds_per_test: int = Field(
        default=120, description="Test execution timeout in seconds"
    )

    # Security & Sandboxing
    sandbox_tier: str = Field(
        default="trusted-local",
        description="Sandbox tier: trusted-local, rootless-container, or microvm",
    )
    enable_egress_filter: bool = Field(
        default=True, description="Scrub secrets and deny sensitive paths"
    )
    auto_approve: bool = Field(
        default=True, description="Auto-approve verified patches when policy passes"
    )
    audit_journal_path: Path = Field(
        default=Path(".patchbound_audit.jsonl"), description="Path to cryptographic audit journal"
    )
    context_mode: str = Field(
        default="auto", description="Context provider mode: auto, synapse, or standard"
    )


settings = Settings()
