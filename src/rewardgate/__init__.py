"""RewardGate: Gated Hierarchical RL Reward and Anti-Gaming Evaluation Harness for Code LLMs."""

from rewardgate.config import RewardGateConfig
from rewardgate.engine import RewardGateEngine
from rewardgate.scratchpad import ScratchpadAnalysis, ScratchpadAnalyzer
from rewardgate.specs import (
    CodeCandidate,
    ExecutionMetrics,
    GatedRewardBreakdown,
    JudgeVerdict,
    StaticAnalysisReport,
    TestResult,
)

__version__ = "0.1.0"
__all__ = [
    "CodeCandidate",
    "TestResult",
    "ExecutionMetrics",
    "StaticAnalysisReport",
    "JudgeVerdict",
    "GatedRewardBreakdown",
    "RewardGateConfig",
    "RewardGateEngine",
    "ScratchpadAnalyzer",
    "ScratchpadAnalysis",
]
