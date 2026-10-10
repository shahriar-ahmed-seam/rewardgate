"""RewardGate: Gated Hierarchical RL Reward and Anti-Gaming Evaluation Harness for Code LLMs."""

from rewardgate.adapters import BatchRolloutEvaluator, RewardGateGRPOAdapter
from rewardgate.audit import JudgeAuditor
from rewardgate.config import RewardGateConfig
from rewardgate.engine import RewardGateEngine
from rewardgate.execution import SandboxExecutor
from rewardgate.scratchpad import ScratchpadAnalysis, ScratchpadAnalyzer
from rewardgate.specs import (
    AuditReport,
    CodeCandidate,
    ExecutionMetrics,
    GatedRewardBreakdown,
    JudgeVerdict,
    StaticAnalysisReport,
    TestResult,
)
from rewardgate.static_analysis import StaticCodeAnalyzer

__version__ = "0.1.0"
__all__ = [
    "CodeCandidate",
    "TestResult",
    "ExecutionMetrics",
    "StaticAnalysisReport",
    "JudgeVerdict",
    "GatedRewardBreakdown",
    "AuditReport",
    "RewardGateConfig",
    "RewardGateEngine",
    "SandboxExecutor",
    "ScratchpadAnalyzer",
    "ScratchpadAnalysis",
    "StaticCodeAnalyzer",
    "JudgeAuditor",
    "RewardGateGRPOAdapter",
    "BatchRolloutEvaluator",
]
