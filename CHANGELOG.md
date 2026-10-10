# Changelog

All notable changes to RewardGate are documented in this file.
The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

---

## [0.1.0] - 2026-10-10

### Added
- Canonical RFC-001 data models (`CodeCandidate`, `TestResult`, `ExecutionMetrics`, `StaticAnalysisReport`, `JudgeVerdict`, `GatedRewardBreakdown`, `AuditReport`) in `rewardgate.specs`.
- Hierarchical gated multi-objective RL reward engine enforcing scale mismatch prevention in `rewardgate.engine`.
- Scratchpad-aware token accounting distinguishing chain-of-thought comments from executable code bloat in `rewardgate.scratchpad`.
- High-resolution monotonic sandbox runtime latency profiler and memory tracking in `rewardgate.execution`.
- Deterministic static AST complexity analyzer (McCabe cyclomatic, cognitive nesting depth, Halstead volume/difficulty, bloat factor) in `rewardgate.static_analysis`.
- Anti-gaming judge auditor with semantic-invariant adversarial perturbations (alpha-renaming, docstring stripping) in `rewardgate.audit`.
- HuggingFace TRL `GRPOTrainer` callable reward function adapter and batch rollout evaluator in `rewardgate.adapters`.
- Comprehensive CLI suite powered by Typer and Rich (`eval`, `static`, `profile`, `audit`, `bench`, `serve`, `version`).
- Anti-AI-slop developer telemetry console and audit workbench in `rewardgate.ui`.
- Publication-grade documentation, Mermaid blueprints, and NoFunEval benchmark specification.
