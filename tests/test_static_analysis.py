"""Unit tests for deterministic static analysis and AST complexity."""

from rewardgate.static_analysis import StaticCodeAnalyzer


def test_simple_function_static_score():
    analyzer = StaticCodeAnalyzer()
    code = """
def square(x: int) -> int:
    return x * x
"""
    report = analyzer.analyze(code)

    assert report.syntax_valid is True
    assert report.cyclomatic_complexity == 1
    assert report.cognitive_complexity == 0
    assert report.halstead_volume > 0.0
    assert report.static_score == 1.0


def test_nested_branching_complexity():
    analyzer = StaticCodeAnalyzer()
    code = """
def process(items):
    total = 0
    for item in items:
        if item > 0:
            if item % 2 == 0:
                total += item
            else:
                total -= item
        elif item < -10:
            total += 1
    return total
"""
    report = analyzer.analyze(code)

    assert report.syntax_valid is True
    # for (+1), if (+1), if (+1), elif (+1) => CC >= 5
    assert report.cyclomatic_complexity >= 5
    # Nested depth increases cognitive complexity
    assert report.cognitive_complexity >= 5
    assert report.static_score < 1.0


def test_syntax_error_static_score():
    analyzer = StaticCodeAnalyzer()
    code = "def bad_syntax(:"
    report = analyzer.analyze(code)

    assert report.syntax_valid is False
    assert report.static_score == 0.0
