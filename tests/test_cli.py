"""Unit tests for RewardGate Typer CLI commands."""

import json
from pathlib import Path

from typer.testing import CliRunner

from rewardgate.cli.main import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "RewardGate" in result.stdout
    assert "RFC-001" in result.stdout


def test_cli_static(tmp_path: Path):
    code_file = tmp_path / "solution.py"
    code_file.write_text("def f(x):\n    return x + 1\n", encoding="utf-8")

    result = runner.invoke(app, ["static", str(code_file)])
    assert result.exit_code == 0
    assert "McCabe Complexity" in result.stdout
    assert "Static Score" in result.stdout


def test_cli_eval(tmp_path: Path):
    cand_file = tmp_path / "cand.py"
    cand_file.write_text("def solve(): return 42\n", encoding="utf-8")
    test_file = tmp_path / "test.py"
    test_file.write_text("assert solve() == 42\n", encoding="utf-8")

    result = runner.invoke(app, ["eval", str(cand_file), "--tests", str(test_file)])
    assert result.exit_code == 0
    assert "GATE OPEN" in result.stdout
    assert "FINAL SCALAR" in result.stdout
    assert "1.5000" in result.stdout


def test_cli_profile(tmp_path: Path):
    cand_file = tmp_path / "cand.py"
    cand_file.write_text("def solve(): return 42\n", encoding="utf-8")
    test_file = tmp_path / "test.py"
    test_file.write_text("assert solve() == 42\n", encoding="utf-8")

    result = runner.invoke(app, ["profile", str(cand_file), "--tests", str(test_file)])
    assert result.exit_code == 0
    assert "Wall-Clock Elapsed" in result.stdout
    assert "Peak Traced Memory" in result.stdout


def test_cli_audit(tmp_path: Path):
    cand_file = tmp_path / "cand.py"
    cand_file.write_text("def solve():\n    '''doc'''\n    return 42\n", encoding="utf-8")

    result = runner.invoke(app, ["audit", str(cand_file)])
    assert result.exit_code == 0
    assert "Score Variance" in result.stdout
    assert "Gaming Resistance Index" in result.stdout


def test_cli_bench(tmp_path: Path):
    dataset_file = tmp_path / "dataset.jsonl"
    record = {
        "problem_id": "p1",
        "source_code": "def solve(): return 1",
        "test_code": "assert solve() == 1",
    }
    dataset_file.write_text(json.dumps(record) + "\n", encoding="utf-8")
    output_traces = tmp_path / "out_traces.jsonl"

    result = runner.invoke(app, ["bench", str(dataset_file), "--output", str(output_traces)])
    assert result.exit_code == 0
    assert "NoFunEval Summary" in result.stdout
    assert "Pass@1 Rate" in result.stdout
    assert output_traces.exists()
