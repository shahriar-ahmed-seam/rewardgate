"""Core evaluation and reward calculation engine interface."""

from __future__ import annotations

from typing import Optional

from rewardgate.config import RewardGateConfig
from rewardgate.specs import (
    CodeCandidate,
    ExecutionMetrics,
    GatedRewardBreakdown,
    JudgeVerdict,
    StaticAnalysisReport,
    TestResult,
)


class RewardGateEngine:
    """Unified engine coordinating test execution, static analysis, and gated reward computation."""

    def __init__(self, config: Optional[RewardGateConfig] = None) -> None:
        self.config = config or RewardGateConfig()

    def calculate_reward(
        self,
        candidate: CodeCandidate,
        test_result: TestResult,
        execution_metrics: Optional[ExecutionMetrics] = None,
        static_report: Optional[StaticAnalysisReport] = None,
        judge_verdict: Optional[JudgeVerdict] = None,
    ) -> GatedRewardBreakdown:
        """Computes hierarchical gated multi-objective scalar reward."""
        if not test_result.passed and self.config.enforce_strict_gating:
            return GatedRewardBreakdown(
                gate_open=False,
                correctness_base=0.0,
                speed_reward=0.0,
                static_reward=0.0,
                judge_reward=0.0,
                hacking_penalty=0.0,
                final_reward=0.0,
                gate_reason="Strict gate closed: functional tests failed.",
            )

        # Base correctness reward
        correctness_base = self.config.correctness_weight if test_result.passed else 0.0

        # Gated components
        speed_score = execution_metrics.speed_score if execution_metrics else 0.0
        speed_reward = self.config.speed_weight * speed_score

        static_score = static_report.static_score if static_report else 0.0
        static_reward = self.config.static_weight * static_score

        judge_score = judge_verdict.normalized_score if judge_verdict else 0.0
        judge_reward = self.config.judge_weight * judge_score

        # Reward hacking penalty
        hacking_penalty = 0.0
        if judge_verdict and judge_verdict.gaming_detected:
            hacking_penalty = self.config.hacking_penalty_weight

        final_reward = max(
            0.0,
            correctness_base + speed_reward + static_reward + judge_reward - hacking_penalty,
        )

        return GatedRewardBreakdown(
            gate_open=True,
            correctness_base=correctness_base,
            speed_reward=speed_reward,
            static_reward=static_reward,
            judge_reward=judge_reward,
            hacking_penalty=hacking_penalty,
            final_reward=final_reward,
            gate_reason="Gate open: functional tests verified; quality rewards credited.",
        )
