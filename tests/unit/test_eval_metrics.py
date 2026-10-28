"""Unit tests for evaluation metrics and statistical calculations."""

from patchbound.eval.metrics import EvalCalculator


def test_wilson_score_interval() -> None:
    # 0 out of 100 successes
    lower, upper = EvalCalculator.wilson_score_interval(0, 100)
    assert lower == 0.0
    assert upper < 0.05  # Upper bound is tight around 0.036

    # 50 out of 100
    lower, upper = EvalCalculator.wilson_score_interval(50, 100)
    assert 0.40 < lower < 0.50
    assert 0.50 < upper < 0.60


def test_compute_summary_false_verified_rate() -> None:
    results = [
        {
            "verification_level": "V3",
            "held_out_failed": False,
            "duration_seconds": 10.0,
            "cost_usd": 0.05,
        },
        {
            "verification_level": "V3",
            "held_out_failed": False,
            "duration_seconds": 12.0,
            "cost_usd": 0.05,
        },
        {
            "verification_level": "V3",
            "held_out_failed": True,
            "duration_seconds": 15.0,
            "cost_usd": 0.05,
        },  # False-verified!
        {
            "verification_level": "V0",
            "held_out_failed": False,
            "duration_seconds": 8.0,
            "cost_usd": 0.02,
        },
    ]

    summary = EvalCalculator.compute_summary("test-arm", results)

    assert summary.total_fixtures == 4
    assert summary.verified_v3_count == 3
    assert summary.held_out_failures == 1
    # FVR = 1 / 3 = 33.3%
    assert abs(summary.false_verified_rate - 1 / 3) < 0.01
    assert summary.fvr_ci_lower > 0.0
    assert summary.fvr_ci_upper < 1.0


def test_abstention_metrics() -> None:
    results = [
        {"outcome": "diagnosis_only", "expected_unrepairable": True, "cost_usd": 0.01},
        {"outcome": "flaky", "expected_unrepairable": True, "cost_usd": 0.01},
        {
            "outcome": "not_reproducible",
            "expected_unrepairable": False,
            "cost_usd": 0.01,
        },  # false decline
        {
            "outcome": "verified_exported",
            "expected_unrepairable": True,
            "cost_usd": 0.05,
        },  # false attempt
    ]

    summary = EvalCalculator.compute_summary("test-arm", results)

    # 3 total declined, 2 were truly unrepairable -> precision = 2/3 = 66.7%
    assert abs(summary.abstention_precision - 2 / 3) < 0.01
    # 3 true unrepairables, 2 were declined -> recall = 2/3 = 66.7%
    assert abs(summary.abstention_recall - 2 / 3) < 0.01
