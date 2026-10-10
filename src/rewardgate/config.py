"""Runtime configuration and reward hyperparameter weights for RewardGate."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RewardGateConfig(BaseModel):
    """Configuration governing hierarchical reward calculation and audit thresholds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Gated Reward Formulation Weights
    correctness_weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Base reward weight granted when all functional tests pass.",
    )
    speed_weight: float = Field(
        default=0.3,
        ge=0.0,
        description="Weight for execution runtime efficiency (direct wall-clock measurement).",
    )
    static_weight: float = Field(
        default=0.2,
        ge=0.0,
        description="Weight for deterministic AST maintainability and complexity.",
    )
    judge_weight: float = Field(
        default=0.1,
        ge=0.0,
        description="Weight for soft judge evaluation (strictly gated behind correctness).",
    )
    hacking_penalty_weight: float = Field(
        default=0.5,
        ge=0.0,
        description="Penalty deducted if adversarial perturbation detects reward hacking.",
    )

    # Sandbox and Isolation Limits
    execution_timeout_seconds: float = Field(
        default=5.0,
        gt=0.0,
        description="Maximum wall-clock execution time permitted for sandbox test runner.",
    )
    execution_memory_mb: int = Field(
        default=512,
        gt=16,
        description="Maximum memory allocated to isolated execution process in megabytes.",
    )

    # Scratchpad and Comment Accounting
    scratchpad_penalty_exempt: bool = Field(
        default=True,
        description="Exempt reasoning comments and thought scratchpads from code bloat penalty.",
    )
    max_scratchpad_tokens: int = Field(
        default=4096,
        ge=0,
        description="Upper boundary for reasoning scratchpad tokens before compression alert.",
    )

    # Anti-Hacking and Audit Thresholds
    judge_variance_threshold: float = Field(
        default=0.05,
        ge=0.0,
        description="Maximum allowed judge score variance across semantic-invariant rewrites.",
    )
    enforce_strict_gating: bool = Field(
        default=True,
        description="Strict gate: if tests fail, speed/static/judge rewards are 0.0.",
    )
