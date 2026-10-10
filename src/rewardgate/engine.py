"""Core evaluation and reward calculation engine interface."""

from __future__ import annotations

from typing import Optional

from rewardgate.config import RewardGateConfig
from rewardgate.scratchpad import ScratchpadAnalyzer
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
        self.scratchpad_analyzer = ScratchpadAnalyzer(
            exempt_scratchpad=self.config.scratchpad_penalty_exempt,
            max_tokens=self.config.max_scratchpad_tokens,
        )

    def calculate_reward(
        self,
        candidate: CodeCandidate,
        test_result: TestResult,
        execution_metrics: Optional[ExecutionMetrics] = None,
        static_report: Optional[StaticAnalysisReport] = None,
        judge_verdict: Optional[JudgeVerdict] = None,
    ) -> GatedRewardBreakdown:
        """Computes hierarchical gated multi-objective scalar reward.

        Enforces the 3 Core Rules:
        1. Tests define correct, not good (gate closes if tests fail).
        2. Execution for speed, judge for remaining (speed is direct measurement).
        3. Assume judge gets hacked until audited (penalize detected gaming).
        """
        # Rule 1: Tests define correct, not good
        if not test_result.passed and self.config.enforce_strict_gating:
            return GatedRewardBreakdown(
                gate_open=False,
                correctness_base=0.0,
                speed_reward=0.0,
                static_reward=0.0,
                judge_reward=0.0,
                hacking_penalty=0.0,
                final_reward=0.0,
                gate_reason=(
                    "Strict gate closed: functional tests failed. "
                    "Scale mismatch prevented: all quality and style rewards clamped to 0.0."
                ),
            )

        # Functional correctness base credit
        correctness_base = self.config.correctness_weight if test_result.passed else 0.0

        # Rule 2: Execution for speed
        speed_score = execution_metrics.speed_score if execution_metrics else 0.0
        speed_reward = self.config.speed_weight * speed_score

        # Static AST maintainability credit
        static_score = static_report.static_score if static_report else 0.0
        static_reward = self.config.static_weight * static_score

        # Scratchpad awareness: analyze comments to avoid penalizing reasoning tokens
        scratch_info = self.scratchpad_analyzer.analyze(candidate.source_code)
        bloat_reduction = 0.0
        if not self.config.scratchpad_penalty_exempt and scratch_info.bloat_factor > 2.0:
            bloat_reduction = 0.1 * (scratch_info.bloat_factor - 2.0)

        # Soft Judge credit
        judge_score = judge_verdict.normalized_score if judge_verdict else 0.0
        judge_reward = self.config.judge_weight * judge_score

        # Rule 3: Assume judge gets hacked until audited
        hacking_penalty = 0.0
        if judge_verdict and judge_verdict.gaming_detected:
            hacking_penalty = self.config.hacking_penalty_weight

        raw_final = (
            correctness_base
            + speed_reward
            + static_reward
            + judge_reward
            - bloat_reduction
            - hacking_penalty
        )
        final_reward = max(0.0, raw_final)

        reasons = [
            f"Gate open (tests passed={test_result.passed})",
            f"base={correctness_base:.2f}",
            f"speed={speed_reward:.2f}",
            f"static={static_reward:.2f}",
            f"judge={judge_reward:.2f}",
        ]
        if hacking_penalty > 0:
            reasons.append(f"hacking_penalty=-{hacking_penalty:.2f}")
        if bloat_reduction > 0:
            reasons.append(f"bloat_reduction=-{bloat_reduction:.2f}")
        if scratch_info.is_scratchpad_load_bearing and self.config.scratchpad_penalty_exempt:
            reasons.append("scratchpad_exempted=True")

        return GatedRewardBreakdown(
            gate_open=True,
            correctness_base=correctness_base,
            speed_reward=speed_reward,
            static_reward=static_reward,
            judge_reward=judge_reward,
            hacking_penalty=hacking_penalty,
            final_reward=final_reward,
            gate_reason="; ".join(reasons),
        )
