# RFC Specification: RewardGate Protocol Standard (RFC-001)

## 1. Scope and Purpose

This document establishes the canonical data exchange protocol, schema definitions, and bounding invariants for RewardGate: a hierarchical gated multi-objective reinforcement learning reward engine and evaluation harness for post-training code LLMs.

The specification guarantees mathematical consistency across training rollouts (e.g., GRPO, PPO, ReMax), preventing scale mismatch between discrete correctness indicators and continuous quality objectives.

## 2. Mathematical Formalization

### 2.1 The Gated Reward Equation

Let $C$ represent a generated code candidate for problem $P$. Let $T(C)$ denote the binary outcome of sandboxed unit and functional test executions:

$$
T(C) = \begin{cases} 
1 & \text{if } \text{failed\_tests} = 0 \text{ and } \text{passed\_tests} > 0 \\
0 & \text{otherwise}
\end{cases}
$$

Let $S_{\text{speed}}(C) \in [0.0, 1.0]$ denote the normalized execution runtime score, $S_{\text{static}}(C) \in [0.0, 1.0]$ denote the deterministic AST maintainability score, and $S_{\text{judge}}(C) \in [0.0, 1.0]$ denote the soft LLM judge score.

The total scalar reward $R(C)$ dispatched to the policy loss is formalized as:

$$
R(C) = T(C) \times \left( w_{\text{base}} + w_{\text{speed}} \cdot S_{\text{speed}}(C) + w_{\text{static}} \cdot S_{\text{static}}(C) + w_{\text{judge}} \cdot S_{\text{judge}}(C) \right) - \mathbb{I}(\text{HackingDetected}) \cdot P_{\text{penalty}}
$$

Where:
- $w_{\text{base}} \ge 0$: Base weight for passing all functional test cases.
- $w_{\text{speed}} \ge 0$: Weight for sandboxed wall-clock execution efficiency.
- $w_{\text{static}} \ge 0$: Weight for deterministic AST complexity and maintainability.
- $w_{\text{judge}} \ge 0$: Weight for soft readability and stylistic review.
- $P_{\text{penalty}} \ge 0$: Deduction applied when invariant perturbation tests reveal reward gaming.

### 2.2 Scale Mismatch Mitigation Invariant

When $T(C) = 0$, all quality rewards MUST evaluate to 0.0:

$$
\forall C \text{ s.t. } T(C) = 0 \implies R(C) = 0.0
$$

This invariant prevents policy collapse wherein the model trades brittle functional correctness on hard edge cases for superficial soft formatting rewards.

## 3. Schema Definitions

### 3.1 CodeCandidate Schema

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `candidate_id` | `string` | Non-empty | Unique identifier for candidate completion |
| `problem_id` | `string` | Non-empty | Benchmark task or unit test identifier |
| `source_code` | `string` | Non-empty | Raw generation content (including scratchpads) |
| `language` | `string` | Default: `"python"` | Programming language runtime |
| `entrypoint` | `string` or `null` | Optional | Callable function or class name |
| `metadata` | `object` | Key-value mapping | Rollout metadata (step, temperature, model) |

### 3.2 TestResult Schema

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `passed` | `boolean` | Required | True if and only if 100% of tests passed |
| `total_tests` | `integer` | $\ge 0$ | Total number of test assertions evaluated |
| `passed_tests` | `integer` | $\ge 0$ | Number of passed test assertions |
| `failed_tests` | `integer` | $\ge 0$ | Number of failed assertions or exceptions |
| `error_type` | `string` or `null` | Optional | Error classification (Timeout, SyntaxError, etc.) |
| `stdout` | `string` | Default: `""` | Sandboxed process stdout trace |
| `stderr` | `string` | Default: `""` | Sandboxed process stderr trace |

### 3.3 ExecutionMetrics Schema

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `wall_clock_seconds` | `float` | $\ge 0.0$ | High-resolution monotonic elapsed time |
| `cpu_time_seconds` | `float` | $\ge 0.0$ | Cumulative CPU user and system duration |
| `peak_memory_bytes` | `integer` | $\ge 0$ | Peak process resident memory usage |
| `baseline_wall_clock_seconds` | `float` or `null` | $\ge 0.0$ | Reference solution wall-clock baseline |
| `speed_score` | `float` | $0.0 \le s \le 1.0$ | Bounded execution efficiency score |
| `timeout_triggered` | `boolean` | Default: `false` | True if killed by sandbox watchdog |
| `oom_triggered` | `boolean` | Default: `false` | True if killed by memory limiter |

### 3.4 StaticAnalysisReport Schema

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `syntax_valid` | `boolean` | Required | True if syntax tree parses without error |
| `cyclomatic_complexity` | `integer` | $\ge 1$ | McCabe cyclomatic complexity count |
| `cognitive_complexity` | `integer` | $\ge 0$ | Structural cognitive nesting depth |
| `halstead_volume` | `float` | $\ge 0.0$ | Halstead program volume |
| `halstead_difficulty` | `float` | $\ge 0.0$ | Halstead difficulty metric |
| `loc` | `integer` | $\ge 0$ | Non-blank, non-comment lines of code |
| `ast_node_count` | `integer` | $\ge 0$ | Count of concrete AST syntax nodes |
| `bloat_ratio` | `float` | $\ge 0.0$ | AST density ratio relative to baseline |
| `scratchpad_comment_tokens`| `integer` | $\ge 0$ | Tokens identified as reasoning scratchpad |
| `static_score` | `float` | $0.0 \le s \le 1.0$ | Composite AST maintainability score |

### 3.5 JudgeVerdict Schema

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `judge_model` | `string` | Required | Evaluator model identifier |
| `raw_score` | `float` | $0.0 \le s \le 1.0$ | Uncalibrated soft score from judge |
| `normalized_score` | `float` | $0.0 \le s \le 1.0$ | Bounded, calibrated quality score |
| `feedback` | `string` | Default: `""` | Qualitative diagnostic justification |
| `perturbation_invariant` | `boolean` | Default: `true` | Stability across semantic-invariant rewrites |
| `gaming_detected` | `boolean` | Default: `false` | True if invariant variance exceeds threshold |

### 3.6 GatedRewardBreakdown Schema

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `gate_open` | `boolean` | Required | True only if functional tests passed |
| `correctness_base` | `float` | $\ge 0.0$ | Primary functional reward credit |
| `speed_reward` | `float` | $\ge 0.0$ | Credit for direct execution runtime |
| `static_reward` | `float` | $\ge 0.0$ | Credit for deterministic AST maintainability |
| `judge_reward` | `float` | $\ge 0.0$ | Credit for soft judge assessment |
| `hacking_penalty` | `float` | $\ge 0.0$ | Deduction for detected judge manipulation |
| `final_reward` | `float` | $\ge 0.0$ | Scalar reward scalar dispatched to policy |
| `gate_reason` | `string` | Descriptive | Audit diagnostic explanation |
