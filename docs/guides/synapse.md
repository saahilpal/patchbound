# Synapse Integration Guide — PatchBound v1.1.0

**Document:** Synapse AST Graph Engine Setup & Usage  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Installation](installation.md) • [Quickstart](quickstart.md) • [Configuration](configuration.md) • [Synapse Integration](synapse.md)

---

## 1. What is Synapse?

**[Synapse (`synap-git`)](https://github.com/saahilpal/synapse)** is an open-source, deterministic Git-aware structural AST retrieval engine created by [@saahilpal](https://github.com/saahilpal).

Unlike traditional vector search, which retrieves chunks based on lexical or semantic similarity, Synapse indexes the target codebase's Abstract Syntax Tree (AST) directly into a local SQLite database (`.synap/synap.db`). It provides:
- **Sub-millisecond Symbol Lookups:** Exact line ranges, signatures, and docstrings.
- **Bidirectional Call Graphs:** Maps who calls a function, and all functions called by it.
- **Impacted Test Prediction:** Computes the transitive reverse dependency closure of any modified file.

---

## 2. Installing & Managing Synapse via CLI

PatchBound includes built-in commands to manage Synapse out of the box:

### Step 1: Install Synapse CLI
```bash
# Automatically install via PatchBound
patchbound synapse install

# Or install manually via pip or uv
pip install synap-git
# or
uv tool install synap-git
```

Verify installation:
```bash
synap --version
```

### Step 2: Index a Repository
Navigate to the root of your codebase and index the AST:
```bash
patchbound synapse index /path/to/project
```
This parses the codebase and writes `.synap/synap.db`.

### Step 3: Inspect Index Health & Call Graphs
Check the indexed statistics:
```bash
patchbound synapse status /path/to/project
```

Expected terminal output:
```
                   ⚡ Synapse Structural Intelligence Status                   
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property                   ┃ Status / Value                                 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Synapse CLI (`synap`)      │ Installed (/Users/.../.local/bin/synap)         │
│ Database Index (`.synap`)  │ Found (.synap/synap.db)                        │
│ Indexed Files              │ 119                                            │
│ Indexed Symbols (AST)      │ 326                                            │
│ Call Graph Edges           │ 552                                            │
└────────────────────────────┴────────────────────────────────────────────────┘
```

### Step 4: Perform Structural AST Queries
Search for functions, methods, classes, or types:
```bash
patchbound synapse search "def calculate_tax"
```

---

## 3. Fallback Guarantees When Synapse is Missing

Synapse is an **optional integration**. 

- If Synapse is not installed or the repository is not indexed:
  - In default `--context auto` mode, PatchBound falls back to `StandardContextProvider` (using native Git diff, file walking, and Python AST parsing).
  - In explicit `--context synapse` mode, PatchBound terminates with exit code 1 and outputs clear remediation instructions.
