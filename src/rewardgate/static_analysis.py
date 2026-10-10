"""Deterministic AST complexity, Halstead metrics, and structural bloat analysis.

Computes ungameable code quality and maintainability metrics directly from the Python AST.
"""

from __future__ import annotations

import ast
import math
from typing import Optional, Set

from rewardgate.scratchpad import ScratchpadAnalyzer
from rewardgate.specs import StaticAnalysisReport


class StaticCodeAnalyzer:
    """Performs deterministic static analysis to produce objective maintainability scores."""

    def __init__(self, scratchpad_analyzer: Optional[ScratchpadAnalyzer] = None) -> None:
        self.scratchpad_analyzer = scratchpad_analyzer or ScratchpadAnalyzer()

    def analyze(self, source_code: str, baseline_loc: Optional[int] = None) -> StaticAnalysisReport:
        """Parses and computes McCabe, cognitive, Halstead, and structural bloat metrics."""
        scratch_info = self.scratchpad_analyzer.analyze(source_code)
        clean_code = scratch_info.clean_code

        try:
            tree = ast.parse(clean_code)
        except SyntaxError:
            return StaticAnalysisReport(
                syntax_valid=False,
                cyclomatic_complexity=1,
                cognitive_complexity=0,
                halstead_volume=0.0,
                halstead_difficulty=0.0,
                loc=scratch_info.executable_lines,
                ast_node_count=0,
                bloat_ratio=1.0,
                scratchpad_comment_tokens=scratch_info.scratchpad_tokens,
                static_score=0.0,
            )

        cc = self._compute_cyclomatic_complexity(tree)
        cog = self._compute_cognitive_complexity(tree)
        volume, difficulty = self._compute_halstead_metrics(tree)
        node_count = sum(1 for _ in ast.walk(tree))

        loc = max(1, scratch_info.executable_lines)
        expected_nodes = baseline_loc * 5 if baseline_loc else max(20, loc * 4)
        bloat_ratio = max(1.0, node_count / max(1, expected_nodes))

        # Composite static score in [0.0, 1.0]
        # Low complexity, clean structure -> 1.0; high nesting and branching -> penalized
        cc_penalty = 0.03 * max(0, cc - 3)
        cog_penalty = 0.02 * max(0, cog - 2)
        bloat_penalty = 0.05 * max(0.0, bloat_ratio - 1.5)
        raw_score = 1.0 - (cc_penalty + cog_penalty + bloat_penalty)
        static_score = max(0.0, min(1.0, raw_score))

        return StaticAnalysisReport(
            syntax_valid=True,
            cyclomatic_complexity=cc,
            cognitive_complexity=cog,
            halstead_volume=volume,
            halstead_difficulty=difficulty,
            loc=loc,
            ast_node_count=node_count,
            bloat_ratio=bloat_ratio,
            scratchpad_comment_tokens=scratch_info.scratchpad_tokens,
            static_score=static_score,
        )

    def _compute_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """McCabe Cyclomatic Complexity = 1 + branches."""
        complexity = 1
        branch_types = (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.With)
        for node in ast.walk(tree):
            if isinstance(node, branch_types):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Each extra value in an 'and' / 'or' represents an additional branch
                complexity += max(0, len(node.values) - 1)
            elif isinstance(node, ast.Assert):
                complexity += 1
            elif isinstance(node, (ast.comprehension, ast.IfExp)):
                complexity += 1
        return complexity

    def _compute_cognitive_complexity(self, tree: ast.AST) -> int:
        """Measures mental effort required to understand code based on nesting depth."""
        cognitive = 0

        def traverse(node: ast.AST, depth: int) -> None:
            nonlocal cognitive
            branch_types = (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)
            is_branching = isinstance(node, branch_types)
            next_depth = depth + 1 if is_branching else depth
            if is_branching:
                cognitive += 1 + depth

            for child in ast.iter_child_nodes(node):
                traverse(child, next_depth)

        traverse(tree, 0)
        return cognitive

    def _compute_halstead_metrics(self, tree: ast.AST) -> tuple[float, float]:
        """Calculates Halstead Volume and Difficulty metrics."""
        operators: Set[str] = set()
        operands: Set[str] = set()
        total_operators = 0
        total_operands = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)):
                operators.add(type(node).__name__)
                total_operators += 1
            elif isinstance(node, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                operators.add(type(node).__name__)
                total_operators += 1
            elif isinstance(node, (ast.And, ast.Or, ast.Not)):
                operators.add(type(node).__name__)
                total_operators += 1
            elif isinstance(node, (ast.Call, ast.Return, ast.Assign)):
                operators.add(type(node).__name__)
                total_operators += 1
            elif isinstance(node, ast.Name):
                operands.add(node.id)
                total_operands += 1
            elif isinstance(node, ast.Constant):
                operands.add(str(node.value))
                total_operands += 1

        n1 = len(operators)
        n2 = len(operands)
        n_total = total_operators + total_operands
        vocab = n1 + n2

        if vocab == 0 or n_total == 0:
            return 0.0, 0.0

        volume = n_total * math.log2(vocab)
        difficulty = (n1 / 2.0) * (total_operands / max(1, n2))
        return volume, difficulty
