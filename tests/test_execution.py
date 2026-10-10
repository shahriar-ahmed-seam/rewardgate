"""Unit tests for sandboxed execution and runtime profiling."""

from rewardgate.execution import SandboxExecutor


def test_sandbox_successful_execution():
    executor = SandboxExecutor(timeout_seconds=2.0)
    source_code = """
def add(a, b):
    return a + b
"""
    test_code = """
assert add(2, 3) == 5
assert add(-1, 1) == 0
"""
    test_res, metrics = executor.execute(source_code, test_code)

    assert test_res.passed is True
    assert test_res.failed_tests == 0
    assert metrics.wall_clock_seconds > 0.0
    assert metrics.speed_score > 0.5
    assert metrics.timeout_triggered is False


def test_sandbox_failed_assertion():
    executor = SandboxExecutor(timeout_seconds=2.0)
    source_code = """
def multiply(a, b):
    return a + b  # Buggy implementation
"""
    test_code = """
assert multiply(2, 3) == 6
"""
    test_res, metrics = executor.execute(source_code, test_code)

    assert test_res.passed is False
    assert test_res.failed_tests == 1
    assert test_res.error_type == "AssertionError"
    assert metrics.timeout_triggered is False


def test_sandbox_timeout_termination():
    executor = SandboxExecutor(timeout_seconds=0.5)
    source_code = """
def infinite_loop():
    while True:
        pass
"""
    test_code = """
infinite_loop()
"""
    test_res, metrics = executor.execute(source_code, test_code)

    assert test_res.passed is False
    assert test_res.error_type == "TimeoutError"
    assert metrics.timeout_triggered is True
    assert metrics.speed_score == 0.0


def test_speed_score_with_baseline():
    executor = SandboxExecutor()

    # Faster than baseline gets 1.0
    assert executor.compute_speed_score(wall_clock=0.01, baseline_wall_clock=0.02) == 1.0

    # Slower than baseline decays smoothly
    score_slower = executor.compute_speed_score(wall_clock=0.04, baseline_wall_clock=0.02)
    assert 0.0 < score_slower < 1.0

    # Much slower gets smaller score
    score_much_slower = executor.compute_speed_score(wall_clock=0.20, baseline_wall_clock=0.02)
    assert score_much_slower < score_slower
