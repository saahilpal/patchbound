"""Statistical metrics and evaluation scoring engine for program repair systems."""

import math
from pydantic import BaseModel, Field


class EvalMetricsSummary(BaseModel):
    """Statistical summary of an evaluation run across an arm."""

    arm_name: str
    total_fixtures: int = 0
    reproduced_count: int = 0
    verified_v1_count: int = 0
    verified_v2_count: int = 0
    verified_v3_count: int = 0
    held_out_failures: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    mean_duration_seconds: float = 0.0

    # Derived metrics
    resolution_rate_v3: float = Field(default=0.0, description="Percentage of fixtures verified at V3")
    false_verified_rate: float = Field(default=0.0, description="FVR: verified patches failing held-out tests")
    fvr_ci_lower: float = 0.0
    fvr_ci_upper: float = 0.0
    cost_per_verified_fix: float = 0.0
    abstention_precision: float = 0.0
    abstention_recall: float = 0.0


class EvalCalculator:
    """Computes statistical metrics with Wilson score intervals and bootstrap bounds."""

    @staticmethod
    def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
        """Compute Wilson score binomial confidence interval."""
        if trials == 0:
            return 0.0, 0.0

        # z-score for confidence level
        z = 1.96 if confidence == 0.95 else 2.576
        p = successes / trials
        denominator = 1 + z**2 / trials
        centre = (p + z**2 / (2 * trials)) / denominator
        spread = z * math.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2)) / denominator

        lower = max(0.0, centre - spread)
        upper = min(1.0, centre + spread)
        return lower, upper

    @classmethod
    def compute_summary(
        cls,
        arm_name: str,
        results: list[dict],
    ) -> EvalMetricsSummary:
        """Compute aggregate benchmark metrics across a collection of fixture outcomes."""
        summary = EvalMetricsSummary(arm_name=arm_name, total_fixtures=len(results))
        if not results:
            return summary

        durations = []
        verified_any = 0
        held_out_fails = 0
        true_unrepairable = 0
        declined_unrepairable = 0
        total_declined = 0

        for r in results:
            summary.total_cost_usd += r.get("cost_usd", 0.0)
            summary.total_tokens += r.get("tokens", 0)
            durations.append(r.get("duration_seconds", 0.0))

            level = r.get("verification_level", "V0")
            if level == "V1":
                summary.verified_v1_count += 1
                verified_any += 1
            elif level == "V2":
                summary.verified_v2_count += 1
                verified_any += 1
            elif level == "V3":
                summary.verified_v3_count += 1
                verified_any += 1

            if r.get("held_out_failed", False):
                held_out_fails += 1

            is_expected_unrepairable = r.get("expected_unrepairable", False)
            if is_expected_unrepairable:
                true_unrepairable += 1

            if r.get("outcome") in ("diagnosis_only", "flaky", "not_reproducible"):
                total_declined += 1
                if is_expected_unrepairable:
                    declined_unrepairable += 1

        summary.held_out_failures = held_out_fails
        summary.mean_duration_seconds = sum(durations) / len(durations) if durations else 0.0

        if summary.total_fixtures > 0:
            summary.resolution_rate_v3 = summary.verified_v3_count / summary.total_fixtures

        # False-Verified Rate = held_out_failures / verified_any
        if verified_any > 0:
            summary.false_verified_rate = held_out_fails / verified_any
            lower, upper = cls.wilson_score_interval(held_out_fails, verified_any)
            summary.fvr_ci_lower = lower
            summary.fvr_ci_upper = upper
        else:
            summary.false_verified_rate = 0.0

        # Cost per verified fix
        total_fixes = summary.verified_v3_count or summary.verified_v2_count or 1
        summary.cost_per_verified_fix = summary.total_cost_usd / total_fixes

        # Abstention precision & recall
        if total_declined > 0:
            summary.abstention_precision = declined_unrepairable / total_declined
        if true_unrepairable > 0:
            summary.abstention_recall = declined_unrepairable / true_unrepairable

        return summary
