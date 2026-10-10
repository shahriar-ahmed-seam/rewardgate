"""Unit tests for RewardGateEngine rule adherence and reward calculation."""

import pytest

from rewardgate.config import RewardGateConfig
from rewardgate.engine import RewardGateEngine
from rewardgate.specs import (
    CodeCandidate,
    ExecutionMetrics,
    JudgeVerdict,
    StaticAnalysisReport,
    TestResult,
)


def test_rule_1_tests_define_correct_not_good():
    """Rule 1: If tests fail, gate is strictly closed regardless of soft scores."""
    config = RewardGateConfig(
        correctness_weight=1.0,
        speed_weight=0.5,
        static_weight=0.5,
        judge_weight=0.5,
        enforce_strict_gating=True,
    )
    engine = RewardGateEngine(config)

    candidate = CodeCandidate(
        candidate_id="cand-001",
        problem_id="prob-1",
        source_code="def solve(): return 42",
    )
    failed_test = TestResult(passed=False, total_tests=5, passed_tests=4, failed_tests=1)
    speed = ExecutionMetrics(wall_clock_seconds=0.001, speed_score=1.0)
    static = StaticAnalysisReport(syntax_valid=True, static_score=1.0)
    judge = JudgeVerdict(raw_score=1.0, normalized_score=1.0)

    breakdown = engine.calculate_reward(
        candidate,
        failed_test,
        execution_metrics=speed,
        static_report=static,
        judge_verdict=judge,
    )

    assert breakdown.gate_open is False
    assert breakdown.final_reward == 0.0
    assert "Strict gate closed" in breakdown.gate_reason


def test_rule_2_execution_for_speed():
    """Rule 2: Execution speed directly modulates the reward when gate is open."""
    config = RewardGateConfig(
        correctness_weight=1.0,
        speed_weight=0.4,
        static_weight=0.0,
        judge_weight=0.0,
    )
    engine = RewardGateEngine(config)
    candidate = CodeCandidate(
        candidate_id="cand-speed",
        problem_id="p",
        source_code="def f(): pass",
    )
    passed_test = TestResult(passed=True, total_tests=1, passed_tests=1, failed_tests=0)

    fast_metrics = ExecutionMetrics(wall_clock_seconds=0.002, speed_score=0.95)
    slow_metrics = ExecutionMetrics(wall_clock_seconds=2.500, speed_score=0.10)

    fast_res = engine.calculate_reward(candidate, passed_test, execution_metrics=fast_metrics)
    slow_res = engine.calculate_reward(candidate, passed_test, execution_metrics=slow_metrics)

    assert fast_res.speed_reward > slow_res.speed_reward
    assert pytest.approx(fast_res.final_reward, 0.01) == 1.0 + (0.4 * 0.95)
    assert pytest.approx(slow_res.final_reward, 0.01) == 1.0 + (0.4 * 0.10)


def test_rule_3_assume_judge_hacked_until_audited():
    """Rule 3: If judge gaming is flagged, hacking penalty is deducted."""
    config = RewardGateConfig(
        correctness_weight=1.0,
        judge_weight=0.2,
        hacking_penalty_weight=0.5,
    )
    engine = RewardGateEngine(config)
    candidate = CodeCandidate(
        candidate_id="cand-hack",
        problem_id="p",
        source_code="def f(): pass",
    )
    passed_test = TestResult(passed=True, total_tests=1, passed_tests=1, failed_tests=0)

    hacked_judge = JudgeVerdict(
        raw_score=0.95,
        normalized_score=0.95,
        gaming_detected=True,
        feedback="Adversarial perturbation detected score fluctuation on variable renaming.",
    )

    res = engine.calculate_reward(candidate, passed_test, judge_verdict=hacked_judge)

    assert res.gate_open is True
    assert res.hacking_penalty == 0.5
    # Expected: 1.0 + (0.2 * 0.95) - 0.5 = 1.0 + 0.19 - 0.5 = 0.69
    assert pytest.approx(res.final_reward, 0.01) == 0.69
    assert "hacking_penalty=-0.50" in res.gate_reason
