"""Sandboxed direct execution profiler and runtime latency benchmarking.

Measures direct wall-clock execution time and peak memory in an isolated sandbox,
mitigating LLM judge hallucination of code speed (Rule 2).
"""

from __future__ import annotations

import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from rewardgate.specs import ExecutionMetrics, TestResult


class SandboxExecutor:
    """Executes code candidates in isolated subprocesses with high-resolution profiling."""

    def __init__(
        self,
        timeout_seconds: float = 5.0,
        memory_mb: int = 512,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.memory_mb = memory_mb

    def execute(
        self,
        source_code: str,
        test_code: str,
        baseline_wall_clock: Optional[float] = None,
    ) -> Tuple[TestResult, ExecutionMetrics]:
        """Runs candidate source code against test assertions in an isolated process.

        Returns:
            Tuple of (TestResult, ExecutionMetrics).
        """
        # Assemble execution script
        wrapper_script = (
            "import sys, time, tracemalloc\n"
            "tracemalloc.start()\n"
            "t0 = time.perf_counter_ns()\n"
            "try:\n"
            f"{self._indent_code(source_code, 4)}\n"
            f"{self._indent_code(test_code, 4)}\n"
            "    t1 = time.perf_counter_ns()\n"
            "    current, peak = tracemalloc.get_traced_memory()\n"
            "    tracemalloc.stop()\n"
            '    print(f"__REWARDGATE_STATS__:{t1 - t0}:{peak}")\n'
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    t1 = time.perf_counter_ns()\n"
            "    current, peak = tracemalloc.get_traced_memory()\n"
            "    tracemalloc.stop()\n"
            '    print(f"__REWARDGATE_STATS__:{t1 - t0}:{peak}", file=sys.stderr)\n'
            '    print(f"__REWARDGATE_ERROR__:{type(e).__name__}:{e}", file=sys.stderr)\n'
            "    sys.exit(1)\n"
        )

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(wrapper_script)
            temp_path = Path(f.name)

        try:
            start_wall = time.perf_counter()
            timed_out = False
            proc = subprocess.Popen(
                [sys.executable, str(temp_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = proc.communicate(timeout=self.timeout_seconds)
                elapsed_wall = time.perf_counter() - start_wall
                return_code = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                elapsed_wall = self.timeout_seconds
                timed_out = True
                return_code = -1
        finally:
            if temp_path.exists():
                temp_path.unlink()

        # Parse telemetry markers from output
        duration_ns, peak_bytes, error_type = self._parse_telemetry(stdout, stderr)
        wall_clock = duration_ns / 1e9 if duration_ns > 0 else elapsed_wall

        if timed_out:
            test_res = TestResult(
                passed=False,
                total_tests=1,
                passed_tests=0,
                failed_tests=1,
                error_type="TimeoutError",
                stdout=stdout,
                stderr=stderr + f"\nProcess terminated after {self.timeout_seconds}s timeout.",
            )
            exec_metrics = ExecutionMetrics(
                wall_clock_seconds=self.timeout_seconds,
                cpu_time_seconds=self.timeout_seconds,
                peak_memory_bytes=peak_bytes,
                baseline_wall_clock_seconds=baseline_wall_clock,
                speed_score=0.0,
                timeout_triggered=True,
                oom_triggered=False,
            )
            return test_res, exec_metrics

        passed = return_code == 0
        test_res = TestResult(
            passed=passed,
            total_tests=1 if passed else 1,
            passed_tests=1 if passed else 0,
            failed_tests=0 if passed else 1,
            error_type=error_type if not passed else None,
            stdout=stdout,
            stderr=stderr,
        )

        speed_score = self.compute_speed_score(
            wall_clock=wall_clock,
            baseline_wall_clock=baseline_wall_clock,
        )

        exec_metrics = ExecutionMetrics(
            wall_clock_seconds=wall_clock,
            cpu_time_seconds=wall_clock,
            peak_memory_bytes=peak_bytes,
            baseline_wall_clock_seconds=baseline_wall_clock,
            speed_score=speed_score,
            timeout_triggered=False,
            oom_triggered=False,
        )
        return test_res, exec_metrics

    def compute_speed_score(
        self,
        wall_clock: float,
        baseline_wall_clock: Optional[float] = None,
    ) -> float:
        """Computes normalized speed score bounded in [0.0, 1.0]."""
        if wall_clock <= 0.0:
            return 1.0

        if baseline_wall_clock is not None and baseline_wall_clock > 0.0:
            # Candidate faster than or equal to baseline -> 1.0
            if wall_clock <= baseline_wall_clock:
                return 1.0
            # Slower: smooth exponential decay
            ratio = (wall_clock - baseline_wall_clock) / baseline_wall_clock
            score = math.exp(-0.5 * ratio)
            return max(0.0, min(1.0, score))

        # Relative to timeout bound
        return max(0.0, min(1.0, 1.0 - (wall_clock / self.timeout_seconds)))

    @staticmethod
    def _indent_code(code: str, spaces: int) -> str:
        pad = " " * spaces
        return "\n".join(pad + line if line.strip() else "" for line in code.splitlines())

    @staticmethod
    def _parse_telemetry(stdout: str, stderr: str) -> Tuple[int, int, Optional[str]]:
        duration_ns = 0
        peak_bytes = 0
        error_type = None

        combined = stdout + "\n" + stderr
        for line in combined.splitlines():
            if line.startswith("__REWARDGATE_STATS__:"):
                parts = line.split(":")
                if len(parts) >= 3:
                    try:
                        duration_ns = int(parts[1])
                        peak_bytes = int(parts[2])
                    except ValueError:
                        pass
            elif line.startswith("__REWARDGATE_ERROR__:"):
                parts = line.split(":")
                if len(parts) >= 2:
                    error_type = parts[1]

        return duration_ns, peak_bytes, error_type
