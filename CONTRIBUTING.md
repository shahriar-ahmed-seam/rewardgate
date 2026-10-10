# Contributing to RewardGate

Thank you for your interest in contributing to RewardGate. We maintain rigorous standards to ensure publication-grade software engineering quality.

---

## 1. Code of Conduct and Zero-Emoji Policy

- **Zero-Emoji Rule**: Emojis are strictly banned in documentation, commit messages, code comments, and CLI outputs. Write in clear, authoritative, technical prose.
- **Tone**: Maintain professional, publication-grade language consistent with RFC standards and systems libraries.

---

## 2. Engineering Workflow

We follow standard GitHub multi-worker engineering discipline:
1. Open an issue describing the bug, feature, or benchmark extension.
2. Branch off `main` using descriptive branch names (`feat/...`, `fix/...`, `docs/...`).
3. Ensure 100% test pass rate (`pytest -v`) and zero linter warnings (`ruff check`).
4. Submit a formal Pull Request with summary, technical changes, and test proof.
5. Squash or merge cleanly upon review.

---

## 3. Testing and Verification Standards

All PRs must include comprehensive unit and integration tests:
- Tests reside in `tests/test_*.py`.
- Run tests: `pytest -v`.
- Run linter: `ruff check src tests examples`.

---

## 4. Documentation Standards

- Always render architecture diagrams and system workflows using GitHub-flavored Mermaid diagrams (`mermaid`).
- Use standard LaTeX math formatting (`$$...$$`) for metric equations.
- Keep specifications in `docs/SPECIFICATION.md` updated with schema modifications.
