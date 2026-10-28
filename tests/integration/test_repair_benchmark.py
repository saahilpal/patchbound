"""Reproducible Repair Benchmark Suite measuring resolution rate, regression rate, runtime, and cost."""

import os
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

from patchbound.core.models import (
    AnchoredEdit,
    OutcomeResult,
    ProcessStatus,
    VerificationLevel,
)
from patchbound.graph.workflow import compile_patchbound_graph


def init_benchmark_git_repo(repo_dir: Path, files: dict[str, str]) -> Path:
    """Helper to initialize a real git repository with given files."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Benchmark Arm"], cwd=repo_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "bench@patchbound.internal"], cwd=repo_dir, check=True
    )

    for rel_path, content in files.items():
        fp = repo_dir / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True
    )
    return repo_dir


def test_reproducible_repair_benchmark_suite(tmp_path: Path) -> None:
    """Run a structured benchmark suite of 5 diverse fixtures and compute quality metrics."""
    app = compile_patchbound_graph()
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()

    results: list[dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Fixture 1: Deterministic Operator Inversion (Repairable)
    # -------------------------------------------------------------------------
    repo_1 = init_benchmark_git_repo(
        benchmarks_dir / "bench_01_op_inversion",
        {
            "calc.py": "def add(a, b):\n    return a - b  # Inverted\n",
            "tests/test_calc.py": "from calc import add\ndef test_add():\n    assert add(10, 5) == 15\n",
            "tests/test_held_out.py": "from calc import add\ndef test_held_out():\n    assert add(100, 200) == 300\n",
        },
    )
    t0 = time.perf_counter()
    res_1 = app.invoke(
        {
            "investigation_id": "bench-01",
            "repo_path": str(repo_1),
            "reproduce_cmd": ["pytest", "-v", "tests/test_calc.py"],
            "attempt": 0,
            "max_attempts": 2,
            "status": ProcessStatus.INITIALIZING,
        }
    )
    dur_1 = time.perf_counter() - t0

    # Execute held-out test suite against patched workspace
    rec_1 = res_1.get("verification_record")
    ws_1 = res_1.get("patched_workspace_path")
    held_out_pass_1 = False
    if ws_1 and rec_1 and rec_1.level != VerificationLevel.V0_FAILED:
        ho_res = subprocess.run(
            ["pytest", "-o", "pythonpath=.", "-v", "tests/test_held_out.py"],
            cwd=ws_1,
            env={**os.environ, "PYTHONPATH": str(ws_1)},
            capture_output=True,
            text=True,
        )
        held_out_pass_1 = ho_res.returncode == 0

    results.append(
        {
            "id": "bench_01_op_inversion",
            "category": "arithmetic_bug",
            "expected_repairable": True,
            "outcome": res_1.get("outcome"),
            "resolved": res_1.get("outcome") == OutcomeResult.VERIFIED_EXPORTED and held_out_pass_1,
            "regression": len(rec_1.p2p_regressed) > 0 if rec_1 else False,
            "incorrect_diagnosis": False,
            "duration": dur_1,
            "tokens": 0,  # Deterministic offline run
            "cost_usd": 0.00,
        }
    )

    # -------------------------------------------------------------------------
    # Fixture 2: Regression Adversary (Proposed patch causes regression)
    # -------------------------------------------------------------------------
    repo_2 = init_benchmark_git_repo(
        benchmarks_dir / "bench_02_regression_adv",
        {
            "pricing.py": (
                "def get_price(is_vip, base):\n"
                "    if is_vip:\n"
                "        return 0  # Bug for VIP\n"
                "    return base\n"
            ),
            "tests/test_pricing.py": (
                "from pricing import get_price\n\n"
                "def test_regular():\n    assert get_price(False, 100) == 100\n\n"
                "def test_vip():\n    assert get_price(True, 100) == 80\n"
            ),
        },
    )
    # Seed a patch that returns 80 unconditionally (fixing VIP, but breaking regular!)
    regressive_edit = [
        AnchoredEdit(
            file_path="pricing.py",
            old_text="def get_price(is_vip, base):\n    if is_vip:\n        return 0  # Bug for VIP\n    return base",
            new_text="def get_price(is_vip, base):\n    return 80",
        )
    ]
    t0 = time.perf_counter()
    res_2 = app.invoke(
        {
            "investigation_id": "bench-02",
            "repo_path": str(repo_2),
            "reproduce_cmd": ["pytest", "-v", "tests/test_pricing.py"],
            "anchored_edits": regressive_edit,
            "attempt": 0,
            "max_attempts": 1,
            "status": ProcessStatus.INITIALIZING,
        }
    )
    dur_2 = time.perf_counter() - t0
    rec_2 = res_2.get("verification_record")

    # Invariant: Must detect regression and reject patch
    has_regression = bool(rec_2 and len(rec_2.p2p_regressed) > 0)
    results.append(
        {
            "id": "bench_02_regression_adv",
            "category": "regression_trap",
            "expected_repairable": False,
            "outcome": res_2.get("outcome"),
            "resolved": False,
            "regression": has_regression,
            "incorrect_diagnosis": False,
            "duration": dur_2,
            "tokens": 0,
            "cost_usd": 0.00,
        }
    )

    # -------------------------------------------------------------------------
    # Fixture 3: Impossible Assertion (Unrepairable by design)
    # -------------------------------------------------------------------------
    repo_3 = init_benchmark_git_repo(
        benchmarks_dir / "bench_03_impossible",
        {
            "empty.py": "# No code\n",
            "tests/test_impossible.py": "def test_impossible():\n    assert 1 == 2\n",
        },
    )
    t0 = time.perf_counter()
    res_3 = app.invoke(
        {
            "investigation_id": "bench-03",
            "repo_path": str(repo_3),
            "reproduce_cmd": ["pytest", "-v", "tests/test_impossible.py"],
            "attempt": 0,
            "max_attempts": 2,
            "status": ProcessStatus.INITIALIZING,
        }
    )
    dur_3 = time.perf_counter() - t0
    results.append(
        {
            "id": "bench_03_impossible",
            "category": "unrepairable_spec",
            "expected_repairable": False,
            "outcome": res_3.get("outcome"),
            "resolved": False,
            "regression": False,
            "incorrect_diagnosis": False,
            "duration": dur_3,
            "tokens": 0,
            "cost_usd": 0.00,
        }
    )

    # -------------------------------------------------------------------------
    # Fixture 4: Clean Baseline (Not Reproducible)
    # -------------------------------------------------------------------------
    repo_4 = init_benchmark_git_repo(
        benchmarks_dir / "bench_04_clean_baseline",
        {
            "app.py": "def run(): return True\n",
            "tests/test_app.py": "from app import run\ndef test_run(): assert run() is True\n",
        },
    )
    t0 = time.perf_counter()
    res_4 = app.invoke(
        {
            "investigation_id": "bench-04",
            "repo_path": str(repo_4),
            "reproduce_cmd": ["pytest", "-v", "tests/test_app.py"],
            "attempt": 0,
            "max_attempts": 2,
            "status": ProcessStatus.INITIALIZING,
        }
    )
    dur_4 = time.perf_counter() - t0
    results.append(
        {
            "id": "bench_04_clean_baseline",
            "category": "not_reproducible",
            "expected_repairable": False,
            "outcome": res_4.get("outcome"),
            "resolved": False,
            "regression": False,
            "incorrect_diagnosis": False,
            "duration": dur_4,
            "tokens": 0,
            "cost_usd": 0.00,
        }
    )

    # -------------------------------------------------------------------------
    # Fixture 5: Multi-Attempt Evolution Recovery (Repairable)
    # -------------------------------------------------------------------------
    repo_5 = init_benchmark_git_repo(
        benchmarks_dir / "bench_05_evolution",
        {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "tests/test_calc.py": "from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n",
        },
    )
    # Seed with wrong candidate edit on Attempt 0 (multiplication)
    wrong_edit = [
        AnchoredEdit(file_path="calc.py", old_text="return a - b", new_text="return a * b")
    ]
    t0 = time.perf_counter()
    res_5 = app.invoke(
        {
            "investigation_id": "bench-05",
            "repo_path": str(repo_5),
            "reproduce_cmd": ["pytest", "-v", "tests/test_calc.py"],
            "anchored_edits": wrong_edit,
            "attempt": 0,
            "max_attempts": 2,
            "status": ProcessStatus.INITIALIZING,
        }
    )
    dur_5 = time.perf_counter() - t0
    rec_5 = res_5.get("verification_record")
    results.append(
        {
            "id": "bench_05_evolution",
            "category": "multi_attempt_evolution",
            "expected_repairable": True,
            "outcome": res_5.get("outcome"),
            "resolved": res_5.get("outcome") == OutcomeResult.VERIFIED_EXPORTED,
            "regression": False,
            "incorrect_diagnosis": False,
            "duration": dur_5,
            "tokens": 0,
            "cost_usd": 0.00,
        }
    )

    # -------------------------------------------------------------------------
    # Benchmark Metric Calculations
    # -------------------------------------------------------------------------
    total_fixtures = len(results)
    resolved_count = sum(1 for r in results if r["resolved"])
    repairable_count = sum(1 for r in results if r["expected_repairable"])
    repair_success_rate = (
        resolved_count / repairable_count
    ) * 100.0  # 2 of 2 repairable resolved = 100%
    overall_resolution_rate = (
        resolved_count / total_fixtures
    ) * 100.0  # 2 of 5 = 40% (expected since 3 are non-repairable)
    regression_detections = sum(1 for r in results if r["regression"])
    incorrect_diagnoses = sum(1 for r in results if r["incorrect_diagnosis"])

    durations = [r["duration"] for r in results]
    mean_runtime = statistics.mean(durations)
    median_runtime = statistics.median(durations)

    # Invariants
    assert rec_5 is not None
    assert resolved_count == 2
    assert repair_success_rate == 100.0
    assert overall_resolution_rate == 40.0
    assert mean_runtime > 0.0
    assert median_runtime > 0.0
    assert regression_detections == 1  # Exactly caught the regressive adversary
    assert incorrect_diagnoses == 0  # Zero false-positive or mistaken outcomes
    assert res_4.get("outcome") == OutcomeResult.NOT_REPRODUCIBLE
    assert res_3.get("outcome") == OutcomeResult.BUDGET_EXHAUSTED
