"""Scratchpad and reasoning token accounting for post-training code LLMs.

Prevents penalizing load-bearing chain-of-thought comments while maintaining
strict structural bloat tracking on executable AST nodes.
"""

from __future__ import annotations

import ast
import io
import tokenize
from typing import NamedTuple


class ScratchpadAnalysis(NamedTuple):
    """Analysis results differentiating reasoning scratchpads from code structure."""

    total_tokens: int
    scratchpad_tokens: int
    executable_tokens: int
    comment_lines: int
    executable_lines: int
    is_scratchpad_load_bearing: bool
    clean_code: str
    bloat_factor: float


class ScratchpadAnalyzer:
    """Isolates reasoning comments from production AST to prevent test pass degradation."""

    def __init__(self, exempt_scratchpad: bool = True, max_tokens: int = 4096) -> None:
        self.exempt_scratchpad = exempt_scratchpad
        self.max_tokens = max_tokens

    def analyze(self, source_code: str) -> ScratchpadAnalysis:
        """Parses source code into scratchpad tokens, executable tokens, and clean code."""
        if not source_code.strip():
            return ScratchpadAnalysis(
                total_tokens=0,
                scratchpad_tokens=0,
                executable_tokens=0,
                comment_lines=0,
                executable_lines=0,
                is_scratchpad_load_bearing=False,
                clean_code="",
                bloat_factor=1.0,
            )

        comment_tokens = 0
        executable_tokens = 0
        total_tokens = 0
        comment_lines = 0
        reasoning_keywords = {"think", "step", "reason", "plan", "because", "invariant", "proof"}
        has_reasoning_markers = False

        clean_lines = []
        source_io = io.StringIO(source_code)

        ignorable_tokens = (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)
        try:
            tokens = list(tokenize.generate_tokens(source_io.readline))
            for tok_type, tok_string, _, _, _ in tokens:
                total_tokens += 1
                if tok_type == tokenize.COMMENT:
                    comment_tokens += len(tok_string.split())
                    lower_comment = tok_string.lower()
                    if any(kw in lower_comment for kw in reasoning_keywords):
                        has_reasoning_markers = True
                elif tok_type not in ignorable_tokens:
                    executable_tokens += 1
        except tokenize.TokenError:
            # Fallback estimation for malformed tokens
            total_tokens = len(source_code.split())
            executable_tokens = total_tokens

        raw_lines = source_code.splitlines()
        executable_lines = 0
        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                comment_lines += 1
            else:
                executable_lines += 1
                clean_lines.append(line)

        # Also strip pure docstrings from clean code if AST parses
        clean_code = "\n".join(clean_lines)
        try:
            tree = ast.parse(clean_code)
            scoped_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
            for node in ast.walk(tree):
                if isinstance(node, scoped_types):
                    if (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    ):
                        doc_text = node.body[0].value.value.lower()
                        if any(kw in doc_text for kw in reasoning_keywords):
                            has_reasoning_markers = True
        except SyntaxError:
            pass

        is_load_bearing = (comment_tokens > 15) or has_reasoning_markers

        # Bloat factor: if exempt, scratchpad tokens are not counted against bloat
        effective_tokens = executable_tokens if self.exempt_scratchpad else total_tokens
        baseline_expected = max(1, executable_lines * 4)
        bloat_factor = max(1.0, effective_tokens / baseline_expected)

        return ScratchpadAnalysis(
            total_tokens=total_tokens,
            scratchpad_tokens=comment_tokens,
            executable_tokens=executable_tokens,
            comment_lines=comment_lines,
            executable_lines=executable_lines,
            is_scratchpad_load_bearing=is_load_bearing,
            clean_code=clean_code,
            bloat_factor=bloat_factor,
        )
