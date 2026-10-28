# Quickstart Tutorial — PatchBound v1.1.0

**Document:** 5-Minute Practical Walkthrough  
**Status:** Approved & Verified (v1.1.0)  
**Index:** [Installation](installation.md) • [Quickstart](quickstart.md) • [Configuration](configuration.md) • [Synapse Integration](synapse.md)

---

## 1. Overview

In this 5-minute walkthrough, you will create a minimal repository containing a broken Python function and an automated test. You will then run `patchbound repair` to observe:
1. Baseline failure reproduction in a disposable scratch sandbox (`/tmp/patchbound-workspaces`).
2. Deterministic AST investigation and repair synthesis.
3. Verification against pinned test oracles (Level V3 CI-Clean).
4. Patch export and optional host application.

---

## 2. Step-by-Step Walkthrough

### Step 1: Create a Disposable Example Project
Run the following in your terminal:
```bash
# 1. Create a temporary project directory
mkdir -p /tmp/quickstart-demo/tests
cd /tmp/quickstart-demo

# 2. Initialize a git repository
git init -b main
git config user.name "Quickstart User"
git config user.email "user@quickstart.local"

# 3. Create a buggy implementation
cat <<'EOF' > calc.py
def add(a, b):
    return a - b  # Bug: subtracted instead of added
EOF

# 4. Create a test file
cat <<'EOF' > tests/test_calc.py
from calc import add

def test_add():
    assert add(10, 5) == 15
EOF

# 5. Commit initial state
git add .
git commit -m "feat: initial calculator implementation"
```

If you run `pytest tests/test_calc.py`, the test fails with:
`AssertionError: assert 5 == 15`.

---

### Step 2: Run PatchBound Repair (Dry-Run Mode)
Execute `patchbound repair` pointing to the directory, passing the reproduction command and specifying `--export-diff fix.diff`:

```bash
patchbound repair /tmp/quickstart-demo \
  --cmd "pytest -v tests/test_calc.py" \
  --export-diff fix.diff
```

### Observed Terminal Output:
```
╭──────────────────────────────────────────────────────────────────────╮
│  PatchBound v1.1  · Deterministic Trust Boundary & Bounded AI Repair │
╰──────────────────────────────────────────────────────────────────────╯
Target Repository: /tmp/quickstart-demo
Reproduction Command: pytest -v tests/test_calc.py

                   Verification Summary                   
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                    ┃ Value                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Outcome Level             │   VERIFICATION LEVEL: V3   │
│ F2P Tests Flipped         │ 1 passed / 1 total         │
│ P2P Regressions           │ 0 (Clean)                  │
│ Tests Skipped Delta       │ 0                          │
│ Flake-Checked             │ ✓ Yes                      │
│ Oracle Integrity (Pinned) │ ✓ Verified                 │
│ Policy Clean              │ ✓ Yes                      │
│ Patch Digest              │ `80d5e597ca309091...`      │
└───────────────────────────┴────────────────────────────┘
╭──────────────────────────── Canonical Patch Diff ────────────────────────────╮
│   1 diff --git calc.py calc.py                                               │
│   2 index 5c81c35..0a419b7 100644                                            │
│   3 --- calc.py                                                              │
│   4 +++ calc.py                                                              │
│   5 @@ -1,2 +1,2 @@                                                          │
│   6  def add(a, b):                                                          │
│   7 -    return a - b  # Bug: subtracted instead of added                    │
│   8 +    return a + b  # Bug: subtracted instead of added                    │
│   9                                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯

Pipeline Terminated. Final Outcome: verified_exported
Verified Patch Digest: `80d5e597ca309091ac239d7f5d427362500e9fbcca049c583955141970875c18`
Approval Signature: `6f680ad34414507ab35896d80ce6a2f781df6ef5c1d67de437a495a142c413f0`
Patch Exported To: `fix.diff`
```

---

### Step 3: Inspect the Generated Patch
Inspect the generated patch file:
```bash
cat fix.diff
```
```diff
diff --git calc.py calc.py
index 5c81c35..0a419b7 100644
--- calc.py
+++ calc.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b  # Bug: subtracted instead of added
+    return a + b  # Bug: subtracted instead of added
```

Notice that during the dry run, the target repository (`/tmp/quickstart-demo`) was **not modified**. Check with:
```bash
git -C /tmp/quickstart-demo status --porcelain
# (Output is empty: host repository remains 100% clean)
```

---

### Step 4: Apply Verified Patch to Host
To automatically apply the verified patch directly to the target working tree once verification and human approval pass, supply the `--apply` flag:

```bash
patchbound repair /tmp/quickstart-demo \
  --cmd "pytest -v tests/test_calc.py" \
  --apply
```

Run `pytest` in `/tmp/quickstart-demo` to verify:
```bash
cd /tmp/quickstart-demo
pytest -v tests/test_calc.py
# tests/test_calc.py::test_add PASSED [100%]
```

The bug is repaired, verified, and safely integrated.
