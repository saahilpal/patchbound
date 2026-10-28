"""Unit tests for CredentialStore and secure CLI authentication commands."""

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from patchproof.cli.main import main
from patchproof.core.credentials import CredentialStore


def test_credential_store_save_and_load(tmp_path: Path) -> None:
    """Verify that credentials can be saved and loaded with strict 0600 permissions."""
    creds_file = tmp_path / "credentials.json"
    store = CredentialStore(creds_file)

    assert store.load_credentials() == {}

    store.set_key("anthropic", "sk-ant-api03-abcdef1234567890")
    loaded = store.load_credentials()
    assert loaded["anthropic"] == "sk-ant-api03-abcdef1234567890"

    # Verify file permissions (0600: owner read/write only) on POSIX
    if os.name == "posix":
        file_stat = creds_file.stat()
        mode = stat.S_IMODE(file_stat.st_mode)
        # Check that group and other have no permissions (0o600 or 0o700)
        assert mode & 0o077 == 0, f"Expected permissions with no group/other access, got {oct(mode)}"


def test_credential_store_env_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify environment variables take precedence over credentials.json."""
    creds_file = tmp_path / "credentials.json"
    store = CredentialStore(creds_file)
    store.set_key("gemini", "stored-gemini-key")

    assert store.get_key("gemini") == "stored-gemini-key"

    # Set env var
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini-key")
    assert store.get_key("gemini") == "env-gemini-key"

    # PATCHPROOF_ prefixed env var takes highest precedence
    monkeypatch.setenv("PATCHPROOF_GEMINI_API_KEY", "patchproof-env-gemini-key")
    assert store.get_key("gemini") == "patchproof-env-gemini-key"


def test_credential_store_masking() -> None:
    """Verify that sensitive keys are properly masked in UI and logs."""
    assert CredentialStore.mask_key("") == ""
    assert CredentialStore.mask_key("short") == "****"
    masked = CredentialStore.mask_key("sk-ant-api03-abcdef1234567890")
    assert masked.startswith("sk-ant")
    assert masked.endswith("7890")
    assert "..." in masked
    assert "abcdef" not in masked


def test_credential_store_delete(tmp_path: Path) -> None:
    """Verify key deletion."""
    creds_file = tmp_path / "credentials.json"
    store = CredentialStore(creds_file)

    store.set_key("openai", "sk-openai-key")
    assert store.get_key("openai") == "sk-openai-key"

    deleted = store.delete_key("openai")
    assert deleted is True
    assert store.get_key("openai") is None

    # Deleting non-existent key returns False
    assert store.delete_key("openai") is False


def test_cli_auth_status_runs_cleanly(tmp_path: Path) -> None:
    """Verify patchproof auth status CLI command output."""
    runner = CliRunner()
    result = runner.invoke(main, ["auth", "status"])
    assert result.exit_code == 0
    assert "PatchProof Authentication & Credential Store" in result.output
    assert "Anthropic" in result.output
    assert "Gemini" in result.output


def test_cli_auth_set_key_and_logout(tmp_path: Path) -> None:
    """Verify setting and deleting credentials via the CLI."""
    temp_creds = tmp_path / "test_creds.json"
    runner = CliRunner()

    with patch.object(CredentialStore, "CREDENTIALS_FILE", temp_creds), \
         patch("patchproof.cli.main.CredentialStore", return_value=CredentialStore(temp_creds)):
        # 1. Set key via CLI argument
        set_res = runner.invoke(main, ["auth", "set-key", "anthropic", "sk-ant-test-secret-key-1234"])
        assert set_res.exit_code == 0
        assert "Successfully configured anthropic" in set_res.output

        # Verify key was stored
        store = CredentialStore(temp_creds)
        assert store.get_key("anthropic") == "sk-ant-test-secret-key-1234"

        # 2. Logout provider
        logout_res = runner.invoke(main, ["auth", "logout", "anthropic"])
        assert logout_res.exit_code == 0
        assert "Removed stored key for anthropic" in logout_res.output
        assert store.get_key("anthropic") is None


def test_cli_synapse_status_command(tmp_path: Path) -> None:
    """Verify patchproof synapse status runs without throwing exceptions."""
    runner = CliRunner()
    result = runner.invoke(main, ["synapse", "status", str(tmp_path)])
    assert result.exit_code == 0
    assert "Synapse Structural Intelligence Status" in result.output
