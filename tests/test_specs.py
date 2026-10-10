"""Unit tests for RewardGate RFC data models and specification validation."""

import pytest
from pydantic import ValidationError

from rewardgate.config import RewardGateConfig
from rewardgate.engine import RewardGateEngine
from rewardgate.specs import (
    CodeCandidate,
    ExecutionMetrics,
    JudgeVerdict,
    StaticAnalysisReport,
    TestResult,
)


def test_code_candidate_immutability():
    candidate = CodeCandidate(
        candidate_id="cand-001",
        problem_id="prob-fib",
        source_code="def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)",
    )
    assert candidate.candidate_id == "cand-001"
    assert candidate.language == "python"

    with pytest.raises(ValidationError):
        # Frozen models cannot be mutated
        candidate.source_code = "modified"


def test_test_result_validation():
    res = TestResult(
        passed=True,
        total_tests=5,
        passed_tests=5,
        failed_tests=0,
    )
    assert res.passed is True
    assert res.failed_tests == 0

    with pytest.raises(ValidationError):
        # Negative test count must fail
        TestResult(passed=False, total_tests=-1)


def test_execution_metrics_bounds():
    metrics = ExecutionMetrics(
        wall_clock_seconds=0.045,
        cpu_time_seconds=0.040,
        peak_memory_bytes=1048576,
        speed_score=0.92,
    )
    assert metrics.speed_score == 0.92

    with pytest.raises(ValidationError):
        # speed_score > 1.0 must fail validation
        ExecutionMetrics(wall_clock_seconds=0.1, speed_score=1.5)


def test_static_analysis_report():
    report = StaticAnalysisReport(
        syntax_valid=True,
        cyclomatic_complexity=3,
        cognitive_complexity=2,
        halstead_volume=120.5,
        halstead_difficulty=4.2,
        loc=15,
        ast_node_count=45,
        bloat_ratio=1.1,
        static_score=0.88,
    )
    assert report.syntax_valid is True
    assert report.cyclomatic_complexity == 3


def test_gated_reward_scale_mismatch_prevention():
    config = RewardGateConfig()
    engine = RewardGateEngine(config)

    candidate = CodeCandidate(
        candidate_id="cand-fail",
        problem_id="prob-sort",
        source_code="def sort(): pass",
    )

    # Failed tests should produce 0.0 reward, preventing trading correctness for soft style
    failed_test = TestResult(passed=False, total_tests=10, passed_tests=8, failed_tests=2)
    high_judge = JudgeVerdict(raw_score=0.95, normalized_score=0.95)
    fast_speed = ExecutionMetrics(wall_clock_seconds=0.001, speed_score=1.0)
    clean_static = StaticAnalysisReport(syntax_valid=True, static_score=0.95)

    reward = engine.calculate_reward(
        candidate=candidate,
        test_result=failed_test,
        execution_metrics=fast_speed,
        static_report=clean_static,
        judge_verdict=high_judge,
    )

    assert reward.gate_open is False
    assert reward.final_reward == 0.0
    assert "Strict gate closed" in reward.gate_reason


def test_gated_reward_success_path():
    config = RewardGateConfig(
        correctness_weight=1.0,
        speed_weight=0.3,
        static_weight=0.2,
        judge_weight=0.1,
    )
    engine = RewardGateEngine(config)

    candidate = CodeCandidate(
        candidate_id="cand-pass",
        problem_id="prob-sort",
        source_code="def quicksort(arr): return arr",
    )

    passed_test = TestResult(passed=True, total_tests=10, passed_tests=10, failed_tests=0)
    judge = JudgeVerdict(raw_score=0.8, normalized_score=0.8)
    speed = ExecutionMetrics(wall_clock_seconds=0.01, speed_score=0.9)
    static_rep = StaticAnalysisReport(syntax_valid=True, static_score=0.85)

    reward = engine.calculate_reward(
        candidate=candidate,
        test_result=passed_test,
        execution_metrics=speed,
        static_report=static_rep,
        judge_verdict=judge,
    )

    assert reward.gate_open is True
    # Expected: 1.0 + (0.3 * 0.9) + (0.2 * 0.85) + (0.1 * 0.8) = 1.0 + 0.27 + 0.17 + 0.08 = 1.52
    assert pytest.approx(reward.final_reward, 0.001) == 1.52
