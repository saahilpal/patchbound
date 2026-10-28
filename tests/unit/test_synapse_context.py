"""Unit tests for the SynapseContextProvider and its attachment with the Synapse project."""

from pathlib import Path

from patchproof.context.synapse import SynapseContextProvider


def test_synapse_provider_attaches_to_synapse_project() -> None:
    synapse_repo = Path("/Users/nitrousoxide/Code/synapse")
    assert synapse_repo.exists(), "Synapse repo must exist at /Users/nitrousoxide/Code/synapse"

    provider = SynapseContextProvider(synapse_repo)

    # 1. Verification of database index attachment
    assert provider.is_synapse_indexed() is True
    assert provider.db_path is not None
    assert provider.db_path.name == "synap.db"

    # 2. Verification of CLI attachment
    assert provider.is_cli_available() is True

    # 3. Verification of symbol resolution from Synapse AST index
    symbols = provider.find_symbol_definitions("HybridRetrievalEngine")
    assert len(symbols) > 0
    match = symbols[0]
    assert match.symbol_name == "HybridRetrievalEngine"
    assert "retrieval/engine.py" in match.file_path
    assert match.line_start > 0
    assert match.line_end >= match.line_start

    # 4. Verification of synap status JSON
    status = provider.get_status()
    assert status is not None
    assert status.get("files", 0) > 0
    assert status.get("symbols", 0) > 0
    assert status.get("mode") == "active"


def test_synapse_provider_clean_fallback_on_unindexed_repo(temp_workspace: Path) -> None:
    # A temp repository with no .synap database
    provider = SynapseContextProvider(temp_workspace)

    assert provider.is_synapse_indexed() is False

    # Should safely fallback to StandardContextProvider for symbols
    symbols = provider.find_symbol_definitions("add")
    assert len(symbols) > 0
    assert symbols[0].symbol_name == "add"
    assert "calculator.py" in symbols[0].file_path

    # Safe fallback for read_file and grep
    content = provider.read_file("calculator.py")
    assert "def add" in content

    matches = provider.grep_search("def add")
    assert len(matches) > 0
