"""Command Line Interface for RewardGate: Gated RL Reward and Evaluation Harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

import rewardgate
from rewardgate.adapters import BatchRolloutEvaluator
from rewardgate.audit import JudgeAuditor
from rewardgate.config import RewardGateConfig
from rewardgate.engine import RewardGateEngine
from rewardgate.execution import SandboxExecutor
from rewardgate.specs import CodeCandidate
from rewardgate.static_analysis import StaticCodeAnalyzer

app = typer.Typer(
    name="rewardgate",
    help="RewardGate: Gated Hierarchical RL Reward & Anti-Gaming Evaluation Harness",
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Print package version and standard protocol details."""
    ver = rewardgate.__version__
    console.print(f"[bold white]RewardGate[/bold white] version [cyan]{ver}[/cyan]")
    console.print("Protocol: RFC-001 Gated Multi-Objective RL Formulation")


@app.command()
def eval(
    file: Path = typer.Argument(..., help="Path to code completion file"),
    tests: Path = typer.Option(..., "--tests", "-t", help="Path to test harness file"),
    baseline: Optional[Path] = typer.Option(None, "--baseline", "-b", help="Baseline code"),
    timeout: float = typer.Option(5.0, "--timeout", help="Execution timeout in seconds"),
) -> None:
    """Evaluate code candidate and compute gated hierarchical reward."""
    if not file.exists():
        console.print(f"[bold red][ERROR][/bold red] Candidate file '{file}' does not exist.")
        raise typer.Exit(code=1)
    if not tests.exists():
        console.print(f"[bold red][ERROR][/bold red] Test file '{tests}' does not exist.")
        raise typer.Exit(code=1)

    source_code = file.read_text(encoding="utf-8")
    test_code = tests.read_text(encoding="utf-8")
    baseline_lat = None
    if baseline and baseline.exists():
        executor_base = SandboxExecutor(timeout_seconds=timeout)
        _, base_metrics = executor_base.execute(baseline.read_text(encoding="utf-8"), test_code)
        baseline_lat = base_metrics.wall_clock_seconds

    config = RewardGateConfig(execution_timeout_seconds=timeout)
    engine = RewardGateEngine(config)
    executor = SandboxExecutor(timeout_seconds=timeout)
    static_analyzer = StaticCodeAnalyzer()

    candidate = CodeCandidate(
        candidate_id=file.stem,
        problem_id=tests.stem,
        source_code=source_code,
    )

    test_res, exec_metrics = executor.execute(
        source_code=source_code,
        test_code=test_code,
        baseline_wall_clock=baseline_lat,
    )
    static_rep = static_analyzer.analyze(source_code)
    breakdown = engine.calculate_reward(
        candidate=candidate,
        test_result=test_res,
        execution_metrics=exec_metrics,
        static_report=static_rep,
    )

    # Format output table
    gate_status = (
        "[bold green][GATE OPEN][/bold green]"
        if breakdown.gate_open
        else "[bold red][GATE CLOSED][/bold red]"
    )
    console.print(f"\nTarget: [bold cyan]{file.name}[/bold cyan] | Status: {gate_status}")

    table = Table(title="RewardGate Telemetry Breakdown", header_style="bold magenta")
    table.add_column("Component", style="dim")
    table.add_column("Metric Value", justify="right")
    table.add_column("Reward Contribution", justify="right")
    table.add_column("Details", style="dim")

    table.add_row(
        "Functional Correctness",
        "PASSED" if test_res.passed else "FAILED",
        f"{breakdown.correctness_base:+.2f}",
        f"{test_res.passed_tests}/{test_res.total_tests} assertions",
    )
    table.add_row(
        "Execution Runtime",
        f"{exec_metrics.wall_clock_seconds * 1000:.2f} ms",
        f"{breakdown.speed_reward:+.2f}",
        f"speed_score={exec_metrics.speed_score:.3f}",
    )
    table.add_row(
        "Static Maintainability",
        f"CC={static_rep.cyclomatic_complexity}, Cog={static_rep.cognitive_complexity}",
        f"{breakdown.static_reward:+.2f}",
        f"bloat_ratio={static_rep.bloat_ratio:.2f}",
    )
    table.add_row(
        "Scratchpad Tokens",
        f"{static_rep.scratchpad_comment_tokens} tokens",
        "+0.00",
        "Exempted reasoning tokens",
    )
    table.add_row(
        "Gaming Penalty",
        f"{breakdown.hacking_penalty:.2f}",
        f"{-breakdown.hacking_penalty:+.2f}",
        "Audited invariant check",
    )
    table.add_section()
    final_str = (
        f"[bold green]{breakdown.final_reward:.4f}[/bold green]"
        if breakdown.gate_open
        else "[bold red]0.0000[/bold red]"
    )
    table.add_row(
        "[bold white]FINAL SCALAR REWARD[/bold white]",
        "",
        final_str,
        breakdown.gate_reason,
    )
    console.print(table)


@app.command()
def static(file: Path = typer.Argument(..., help="Path to code file")) -> None:
    """Analyze deterministic AST complexity, Halstead metrics, and code bloat."""
    if not file.exists():
        console.print(f"[bold red][ERROR][/bold red] File '{file}' does not exist.")
        raise typer.Exit(code=1)

    code = file.read_text(encoding="utf-8")
    analyzer = StaticCodeAnalyzer()
    rep = analyzer.analyze(code)

    table = Table(title=f"Static AST Analysis: {file.name}", header_style="bold blue")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")
    table.add_column("Status", justify="left")

    stat_flag = "[PASSED]" if rep.syntax_valid else "[FAILED]"
    table.add_row("Syntax Validity", str(rep.syntax_valid), stat_flag)
    table.add_row("Lines of Code (LOC)", str(rep.loc), "Executable non-blank statements")
    table.add_row("McCabe Complexity", str(rep.cyclomatic_complexity), "Branch points + 1")
    table.add_row("Cognitive Complexity", str(rep.cognitive_complexity), "Nesting structural depth")
    table.add_row("Halstead Volume", f"{rep.halstead_volume:.1f}", "Operator / operand vocab")
    table.add_row("Halstead Difficulty", f"{rep.halstead_difficulty:.2f}", "Error proneness index")
    table.add_row("AST Node Count", str(rep.ast_node_count), "Total parsed syntax elements")
    table.add_row("Bloat Ratio", f"{rep.bloat_ratio:.2f}", "Nodes relative to expectation")
    table.add_row("Scratchpad Tokens", str(rep.scratchpad_comment_tokens), "Protected tokens")
    table.add_row("Static Score (S_static)", f"{rep.static_score:.3f}", "Bounded in [0.0, 1.0]")
    console.print(table)


@app.command()
def profile(
    file: Path = typer.Argument(..., help="Path to code file"),
    tests: Path = typer.Option(..., "--tests", "-t", help="Path to test harness file"),
    timeout: float = typer.Option(5.0, "--timeout", help="Execution timeout in seconds"),
) -> None:
    """Profile isolated execution latency, CPU duration, and peak memory."""
    if not file.exists() or not tests.exists():
        console.print("[bold red][ERROR][/bold red] Code or test file not found.")
        raise typer.Exit(code=1)

    executor = SandboxExecutor(timeout_seconds=timeout)
    test_res, metrics = executor.execute(
        file.read_text(encoding="utf-8"),
        tests.read_text(encoding="utf-8"),
    )

    table = Table(title=f"Sandbox Execution Profile: {file.name}", header_style="bold green")
    table.add_column("Profile Dimension", style="dim")
    table.add_column("Measured Value", justify="right")

    table.add_row("Functional Status", "PASSED" if test_res.passed else "FAILED")
    table.add_row("Wall-Clock Elapsed", f"{metrics.wall_clock_seconds * 1000:.3f} ms")
    table.add_row("CPU Time", f"{metrics.cpu_time_seconds * 1000:.3f} ms")
    table.add_row("Peak Traced Memory", f"{metrics.peak_memory_bytes / 1024:.2f} KB")
    table.add_row("Speed Score", f"{metrics.speed_score:.4f}")
    table.add_row("Timeout Triggered", str(metrics.timeout_triggered))
    console.print(table)


@app.command()
def audit(file: Path = typer.Argument(..., help="Path to code file")) -> None:
    """Audit judge robustness across semantic-invariant perturbations."""
    if not file.exists():
        console.print(f"[bold red][ERROR][/bold red] File '{file}' does not exist.")
        raise typer.Exit(code=1)

    code = file.read_text(encoding="utf-8")
    auditor = JudgeAuditor()
    candidate = CodeCandidate(
        candidate_id=file.stem,
        problem_id="audit-task",
        source_code=code,
    )

    # Standard heuristic baseline judge for CLI audit verification
    def heuristic_judge(c: str) -> float:
        rep = StaticCodeAnalyzer().analyze(c)
        return rep.static_score

    report = auditor.audit_judge(candidate, judge_fn=heuristic_judge)

    table = Table(title=f"Anti-Hacking Judge Audit: {file.name}", header_style="bold yellow")
    table.add_column("Audit Parameter", style="dim")
    table.add_column("Value", justify="right")
    table.add_column("Status", justify="left")

    n_pert = len(report.perturbed_scores)
    thresh = auditor.variance_threshold
    table.add_row("Baseline Score", f"{report.baseline_score:.3f}", "Unperturbed evaluation")
    table.add_row("Perturbation Count", str(n_pert), "Alpha-renamed & docstring-stripped")
    table.add_row("Score Variance", f"{report.score_variance:.5f}", f"Threshold: {thresh}")
    table.add_row(
        "Gaming Detected",
        str(report.gaming_detected),
        "[FAILED] Gaming Flagged" if report.gaming_detected else "[PASSED] Robust Invariance",
    )
    table.add_row(
        "Gaming Resistance Index",
        f"{report.gaming_resistance_index:.3f}",
        "Bounded in [0.0, 1.0]",
    )
    console.print(table)


@app.command()
def bench(
    dataset: Path = typer.Argument(..., help="Path to JSONL dataset"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output traces path"),
) -> None:
    """Run batch rollout evaluation and output NoFunEval metrics."""
    if not dataset.exists():
        console.print(f"[bold red][ERROR][/bold red] Dataset '{dataset}' not found.")
        raise typer.Exit(code=1)

    items = []
    with open(dataset, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    evaluator = BatchRolloutEvaluator()
    summary = evaluator.evaluate_batch(items, output_trace_path=output)

    table = Table(title=f"NoFunEval Summary: {dataset.name}", header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    med_ms = summary["median_latency_seconds"] * 1000
    table.add_row("Total Problems Evaluated", str(summary["total_items"]))
    table.add_row("Passed Completions", str(summary["passed_items"]))
    table.add_row("Functional Pass@1 Rate", f"{summary['pass_rate'] * 100:.1f}%")
    table.add_row("Median Wall-Clock Latency", f"{med_ms:.2f} ms")
    table.add_row("Mean Cyclomatic Complexity", f"{summary['mean_cyclomatic_complexity']:.2f}")
    console.print(table)
    if output:
        console.print(f"Traces exported to: [green]{output}[/green]")
