"""Canonical RFC data models and specification schemas for RewardGate."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CodeCandidate(BaseModel):
    """Represents a code candidate submitted for evaluation or RL reward attribution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str = Field(
        ...,
        description="Unique identifier for the generated code completion.",
    )
    problem_id: str = Field(
        ...,
        description="Identifier of the task, benchmark item, or unit test suite.",
    )
    source_code: str = Field(
        ...,
        description="Full generation content including docstrings, reasoning comments, and code.",
    )
    language: str = Field(
        default="python",
        description="Target programming language (defaults to 'python').",
    )
    entrypoint: Optional[str] = Field(
        default=None,
        description="Optional entrypoint function or class name.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional auxiliary generation metadata (temperature, step, model id).",
    )


class TestResult(BaseModel):
    """Outcome of sandboxed unit and functional test executions."""

    __test__ = False
    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool = Field(
        ...,
        description="Strict boolean indicating whether 100% of functional tests passed.",
    )
    total_tests: int = Field(
        default=0,
        ge=0,
        description="Total number of evaluated test assertions or cases.",
    )
    passed_tests: int = Field(
        default=0,
        ge=0,
        description="Number of passed test assertions or cases.",
    )
    failed_tests: int = Field(
        default=0,
        ge=0,
        description="Number of failed test assertions or cases.",
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Error classification (e.g. Timeout, SyntaxError, AssertionError).",
    )
    stdout: str = Field(default="", description="Captured standard output from sandbox.")
    stderr: str = Field(default="", description="Captured standard error from sandbox.")


class ExecutionMetrics(BaseModel):
    """Deterministic runtime latency and memory metrics captured in sandbox."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    wall_clock_seconds: float = Field(
        ...,
        ge=0.0,
        description="Direct execution wall-clock time in seconds measured via monotonic clock.",
    )
    cpu_time_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="CPU user + system time in seconds.",
    )
    peak_memory_bytes: int = Field(
        default=0,
        ge=0,
        description="Peak memory consumption in bytes during test execution.",
    )
    baseline_wall_clock_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Reference baseline implementation wall-clock time for normalization.",
    )
    speed_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Normalized speed score bounded in [0.0, 1.0].",
    )
    timeout_triggered: bool = Field(
        default=False,
        description="Flag indicating sandbox process was killed due to execution timeout.",
    )
    oom_triggered: bool = Field(
        default=False,
        description="Flag indicating sandbox process was killed due to memory limit breach.",
    )


class StaticAnalysisReport(BaseModel):
    """Deterministic AST complexity and structural bloat analysis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    syntax_valid: bool = Field(
        ...,
        description="Whether the code parses successfully into a valid AST.",
    )
    cyclomatic_complexity: int = Field(
        default=1,
        ge=1,
        description="McCabe cyclomatic complexity computed over AST branching nodes.",
    )
    cognitive_complexity: int = Field(
        default=0,
        ge=0,
        description="Cognitive complexity metric accounting for nesting depth.",
    )
    halstead_volume: float = Field(
        default=0.0,
        ge=0.0,
        description="Halstead program volume metric based on operators and operands.",
    )
    halstead_difficulty: float = Field(
        default=0.0,
        ge=0.0,
        description="Halstead difficulty metric.",
    )
    loc: int = Field(
        default=0,
        ge=0,
        description="Executable lines of code (excluding blank lines and pure comments).",
    )
    ast_node_count: int = Field(
        default=0,
        ge=0,
        description="Total AST node count.",
    )
    bloat_ratio: float = Field(
        default=1.0,
        ge=0.0,
        description="Ratio of AST nodes to minimum required structure relative to baseline.",
    )
    scratchpad_comment_tokens: int = Field(
        default=0,
        ge=0,
        description="Tokens accounted for as reasoning comments / scratchpad thoughts.",
    )
    static_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite static maintainability score bounded in [0.0, 1.0].",
    )


class JudgeVerdict(BaseModel):
    """Audited LLM judge evaluation report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    judge_model: str = Field(
        default="none",
        description="Model identifier of the evaluation judge.",
    )
    raw_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Raw soft quality score assigned by judge in [0.0, 1.0].",
    )
    normalized_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Gated and calibrated soft score.",
    )
    feedback: str = Field(
        default="",
        description="Qualitative feedback provided by judge.",
    )
    perturbation_invariant: bool = Field(
        default=True,
        description="True if judge verdict remained stable under semantic-invariant rewrites.",
    )
    gaming_detected: bool = Field(
        default=False,
        description="True if adversarial perturbation revealed reward hacking.",
    )


class GatedRewardBreakdown(BaseModel):
    """Decomposition of the hierarchical gated multi-objective RL reward."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_open: bool = Field(
        ...,
        description="Gate condition (True only if 100% of functional tests passed).",
    )
    correctness_base: float = Field(
        default=0.0,
        description="Base reward for functional correctness.",
    )
    speed_reward: float = Field(
        default=0.0,
        description="Gated reward component for direct execution runtime efficiency.",
    )
    static_reward: float = Field(
        default=0.0,
        description="Gated reward component for AST complexity and maintainability.",
    )
    judge_reward: float = Field(
        default=0.0,
        description="Gated reward component for soft judge review (clamped to 0 if gate closed).",
    )
    hacking_penalty: float = Field(
        default=0.0,
        ge=0.0,
        description="Deduction applied if reward hacking or judge manipulation is detected.",
    )
    final_reward: float = Field(
        ...,
        description="Final scalar reward dispatched to the RL policy (e.g. GRPO / PPO loss).",
    )
    gate_reason: str = Field(
        default="",
        description="Diagnostic explanation of gating decision and reward breakdown.",
    )


class AuditReport(BaseModel):
    """Audit report for judge robustness and NoFunEval metrics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str = Field(..., description="Target candidate identifier.")
    baseline_score: float = Field(..., description="Baseline judge score on unperturbed code.")
    perturbed_scores: List[float] = Field(
        default_factory=list,
        description="Judge scores across semantic-invariant perturbations.",
    )
    score_variance: float = Field(
        default=0.0,
        ge=0.0,
        description="Variance of judge scores across invariant rewrites.",
    )
    gaming_detected: bool = Field(
        default=False,
        description="Whether score variance exceeds the maximum acceptable tolerance.",
    )
    nofun_latency_factor: float = Field(
        default=1.0,
        ge=0.0,
        description="Ratio of candidate latency to baseline latency.",
    )
    nofun_bloat_factor: float = Field(
        default=1.0,
        ge=0.0,
        description="Ratio of AST complexity to baseline complexity.",
    )
    gaming_resistance_index: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Score between 0.0 and 1.0 indicating resistance to judge manipulation.",
    )
