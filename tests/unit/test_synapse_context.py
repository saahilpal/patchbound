"""Unit tests for the SynapseContextProvider and its attachment with the Synapse project."""

import sqlite3
from pathlib import Path

import pytest

from patchproof.context.synapse import SynapseContextProvider


@pytest.mark.skipif(
    not Path("/Users/nitrousoxide/Code/synapse").exists(),
    reason="Local Synapse repository required for full workspace integration test",
)
def test_synapse_provider_attaches_to_synapse_project() -> None:
    synapse_repo = Path("/Users/nitrousoxide/Code/synapse")
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


def test_synapse_provider_with_synthetic_sqlite_index(tmp_path: Path) -> None:
    """Verify Synapse AST symbol querying and reverse dependency analysis using a synthetic DB."""
    synap_dir = tmp_path / ".synap"
    synap_dir.mkdir(parents=True)
    db_file = synap_dir / "synap.db"

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("CREATE TABLE files (file_id INTEGER PRIMARY KEY, path TEXT);")
    cur.execute("CREATE TABLE symbols (symbol_id INTEGER PRIMARY KEY, file_id INTEGER, name TEXT, kind TEXT, start_line INTEGER, end_line INTEGER);")
    cur.execute("CREATE TABLE edges (source_symbol INTEGER, target_symbol INTEGER, kind TEXT);")

    cur.execute("INSERT INTO files VALUES (1, 'src/auth.py'), (2, 'tests/test_auth.py');")
    cur.execute("INSERT INTO symbols VALUES (101, 1, 'verify_token', 'function', 10, 25);")
    cur.execute("INSERT INTO symbols VALUES (102, 2, 'test_verify_token_valid', 'function', 5, 12);")
    cur.execute("INSERT INTO edges VALUES (102, 101, 'calls');")
    conn.commit()
    conn.close()

    provider = SynapseContextProvider(tmp_path)
    assert provider.is_synapse_indexed() is True

    # Test symbol definition resolution
    symbols = provider.find_symbol_definitions("verify_token")
    assert len(symbols) == 1
    assert symbols[0].file_path == "src/auth.py"
    assert symbols[0].line_start == 10
    assert symbols[0].line_end == 25

    # Test impacted test discovery via reverse call edges
    impacted = provider.get_impacted_tests(["src/auth.py"])
    assert "tests/test_auth.py" in impacted


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

