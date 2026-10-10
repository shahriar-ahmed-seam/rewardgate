"""HuggingFace TRL GRPOTrainer adapter and batch rollout evaluator.

Integrates RewardGate with reinforcement learning pipelines (GRPO, PPO) and
exports structured JSONL telemetry traces.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from rewardgate.config import RewardGateConfig
from rewardgate.engine import RewardGateEngine
from rewardgate.execution import SandboxExecutor
from rewardgate.specs import (
    CodeCandidate,
    GatedRewardBreakdown,
)
from rewardgate.static_analysis import StaticCodeAnalyzer


class RewardGateGRPOAdapter:
    """Callable reward function compatible with HuggingFace TRL GRPOTrainer.

    Signature conforms to:
    def reward_func(prompts: list[str], completions: list[Any], **kwargs) -> list[float]
    """

    def __init__(
        self,
        config: Optional[RewardGateConfig] = None,
        test_suite_map: Optional[Dict[str, str]] = None,
    ) -> None:
        self.config = config or RewardGateConfig()
        self.engine = RewardGateEngine(self.config)
        self.executor = SandboxExecutor(
            timeout_seconds=self.config.execution_timeout_seconds,
            memory_mb=self.config.execution_memory_mb,
        )
        self.static_analyzer = StaticCodeAnalyzer()
        self.test_suite_map = test_suite_map or {}

    def __call__(
        self,
        prompts: List[str],
        completions: List[Union[str, List[Dict[str, str]]]],
        **kwargs: Any,
    ) -> List[float]:
        """Calculates scalar gated rewards for rollout completion batches."""
        rewards: List[float] = []

        # If tests are provided in kwargs (e.g. from dataset columns)
        tests = kwargs.get("tests", [])

        for i, (prompt, completion) in enumerate(zip(prompts, completions)):
            code_text = self._extract_code(completion)
            test_code = (
                tests[i]
                if i < len(tests)
                else self.test_suite_map.get(prompt, "assert True")
            )

            candidate = CodeCandidate(
                candidate_id=f"rollout-{i}",
                problem_id=f"prob-{i}",
                source_code=code_text,
            )

            test_res, exec_metrics = self.executor.execute(code_text, test_code)
            static_rep = self.static_analyzer.analyze(code_text)

            breakdown = self.engine.calculate_reward(
                candidate=candidate,
                test_result=test_res,
                execution_metrics=exec_metrics,
                static_report=static_rep,
                judge_verdict=None,
            )
            rewards.append(breakdown.final_reward)

        return rewards

    @staticmethod
    def _extract_code(completion: Union[str, List[Dict[str, str]]]) -> str:
        """Extracts raw string content from chat completion format or raw string."""
        if isinstance(completion, list):
            # Chat messages format [{"role": "assistant", "content": "..."}]
            for msg in reversed(completion):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    return msg.get("content", "")
            return ""
        return str(completion)


class BatchRolloutEvaluator:
    """Evaluates batches of candidate completions and generates telemetry reports."""

    def __init__(self, config: Optional[RewardGateConfig] = None) -> None:
        self.config = config or RewardGateConfig()
        self.engine = RewardGateEngine(self.config)
        self.executor = SandboxExecutor(
            timeout_seconds=self.config.execution_timeout_seconds,
            memory_mb=self.config.execution_memory_mb,
        )
        self.static_analyzer = StaticCodeAnalyzer()

    def evaluate_batch(
        self,
        items: List[Dict[str, Any]],
        output_trace_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Runs evaluation over a list of task dicts.

        Each item must contain:
        - "problem_id": str
        - "source_code": str
        - "test_code": str
        - optional "baseline_latency": float
        """
        results: List[Dict[str, Any]] = []
        total_passed = 0
        total_items = len(items)
        latencies: List[float] = []
        complexities: List[int] = []

        for idx, item in enumerate(items):
            pid = item.get("problem_id", f"item-{idx}")
            src = item.get("source_code", "")
            test = item.get("test_code", "assert True")
            base_lat = item.get("baseline_latency", None)

            candidate = CodeCandidate(
                candidate_id=f"cand-{idx}",
                problem_id=pid,
                source_code=src,
            )

            test_res, exec_metrics = self.executor.execute(
                source_code=src,
                test_code=test,
                baseline_wall_clock=base_lat,
            )
            static_rep = self.static_analyzer.analyze(src)

            breakdown: GatedRewardBreakdown = self.engine.calculate_reward(
                candidate=candidate,
                test_result=test_res,
                execution_metrics=exec_metrics,
                static_report=static_rep,
            )

            if test_res.passed:
                total_passed += 1
            latencies.append(exec_metrics.wall_clock_seconds)
            complexities.append(static_rep.cyclomatic_complexity)

            record = {
                "candidate_id": candidate.candidate_id,
                "problem_id": pid,
                "passed": test_res.passed,
                "final_reward": breakdown.final_reward,
                "gate_open": breakdown.gate_open,
                "speed_reward": breakdown.speed_reward,
                "static_reward": breakdown.static_reward,
                "wall_clock_seconds": exec_metrics.wall_clock_seconds,
                "cyclomatic_complexity": static_rep.cyclomatic_complexity,
                "cognitive_complexity": static_rep.cognitive_complexity,
                "bloat_ratio": static_rep.bloat_ratio,
                "scratchpad_tokens": static_rep.scratchpad_comment_tokens,
                "gate_reason": breakdown.gate_reason,
            }
            results.append(record)

        pass_rate = (total_passed / total_items) if total_items > 0 else 0.0
        median_lat = sorted(latencies)[len(latencies) // 2] if latencies else 0.0
        mean_cc = (sum(complexities) / len(complexities)) if complexities else 0.0

        summary = {
            "total_items": total_items,
            "passed_items": total_passed,
            "pass_rate": pass_rate,
            "median_latency_seconds": median_lat,
            "mean_cyclomatic_complexity": mean_cc,
            "records": results,
        }

        if output_trace_path:
            p = Path(output_trace_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                for rec in results:
                    f.write(json.dumps(rec) + "\n")

        return summary
