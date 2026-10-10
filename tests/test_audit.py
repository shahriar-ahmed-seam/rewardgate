"""Unit tests for judge auditing, semantic invariant perturbations, and NoFunEval metrics."""

from rewardgate.audit import JudgeAuditor
from rewardgate.specs import CodeCandidate, JudgeVerdict


def test_perturbation_generators():
    auditor = JudgeAuditor()
    source = '''
"""Module docstring explaining algorithm."""

def compute(x: int) -> int:
    """Computes factorial iteratively."""
    # Local loop variable
    res = 1
    for i in range(1, x + 1):
        res *= i
    return res
'''
    perturbations = auditor.generate_perturbations(source)

    assert len(perturbations) >= 2
    # Check that at least one perturbation stripped the docstring
    assert any("Computes factorial iteratively" not in p for p in perturbations)


def test_consistent_judge_passes_audit():
    auditor = JudgeAuditor(variance_threshold=0.05)
    candidate = CodeCandidate(
        candidate_id="c-001",
        problem_id="p-001",
        source_code="def f(x): return x + 1",
    )

    # Consistent judge assigns stable scores across invariant rewrites
    def consistent_judge(code: str) -> float:
        return 0.85

    report = auditor.audit_judge(candidate, judge_fn=consistent_judge)

    assert report.gaming_detected is False
    assert report.score_variance == 0.0
    assert report.gaming_resistance_index == 1.0


def test_biased_judge_triggers_gaming_detection():
    auditor = JudgeAuditor(variance_threshold=0.04)
    candidate = CodeCandidate(
        candidate_id="c-002",
        problem_id="p-002",
        source_code='''
def f(x):
    """Verbose docstring that biases naive judges."""
    return x * 2
''',
    )

    # Biased judge gives high score to docstrings, but penalizes stripped code heavily
    def biased_judge(code: str) -> float:
        if "Verbose docstring" in code:
            return 0.95
        return 0.20

    report = auditor.audit_judge(candidate, judge_fn=biased_judge)

    assert report.gaming_detected is True
    assert report.score_variance > 0.04
    assert report.gaming_resistance_index < 0.5

    # Verify verdict calibration
    initial_verdict = JudgeVerdict(raw_score=0.95, normalized_score=0.95)
    calibrated = auditor.verify_verdict(initial_verdict, report)
    assert calibrated.gaming_detected is True
    assert calibrated.normalized_score < initial_verdict.raw_score
