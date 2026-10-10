"""Unit tests for TRL GRPOTrainer adapter and batch evaluation."""

import json
from pathlib import Path

from rewardgate.adapters import BatchRolloutEvaluator, RewardGateGRPOAdapter
from rewardgate.config import RewardGateConfig


def test_grpo_adapter_signature_and_rewards():
    config = RewardGateConfig(
        correctness_weight=1.0,
        speed_weight=0.2,
        static_weight=0.1,
    )
    adapter = RewardGateGRPOAdapter(config=config)

    prompts = [
        "Write a function add(a, b)",
        "Write a function multiply(a, b)",
    ]
    completions = [
        "def add(a, b): return a + b",
        "def multiply(a, b): return 0  # wrong",
    ]
    tests = [
        "assert add(1, 2) == 3",
        "assert multiply(2, 3) == 6",
    ]

    rewards = adapter(prompts, completions, tests=tests)

    assert len(rewards) == 2
    assert isinstance(rewards[0], float)
    assert isinstance(rewards[1], float)

    # First completion passes tests -> reward > 1.0
    assert rewards[0] >= 1.0
    # Second completion fails tests -> strictly 0.0
    assert rewards[1] == 0.0


def test_batch_rollout_evaluator(tmp_path: Path):
    evaluator = BatchRolloutEvaluator()
    items = [
        {
            "problem_id": "prob-sum",
            "source_code": "def sum_list(xs): return sum(xs)",
            "test_code": "assert sum_list([1, 2, 3]) == 6",
            "baseline_latency": 0.005,
        },
        {
            "problem_id": "prob-fail",
            "source_code": "def sum_list(xs): return 0",
            "test_code": "assert sum_list([1, 2, 3]) == 6",
            "baseline_latency": 0.005,
        },
    ]

    trace_file = tmp_path / "traces.jsonl"
    summary = evaluator.evaluate_batch(items, output_trace_path=trace_file)

    assert summary["total_items"] == 2
    assert summary["passed_items"] == 1
    assert summary["pass_rate"] == 0.5
    assert trace_file.exists()

    with open(trace_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    assert len(lines) == 2
    assert lines[0]["passed"] is True
    assert lines[1]["passed"] is False
    assert lines[1]["final_reward"] == 0.0
