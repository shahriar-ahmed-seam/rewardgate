# Security Policy for RewardGate

## 1. Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

---

## 2. Sandbox Execution Security Boundary

RewardGate executes untrusted model completions in subprocesses. When running large-scale automated rollouts on untrusted or internet-facing inputs:

- Subprocess executions must be isolated via containerization (Docker, Podman) or sandbox namespaces (cgroups, bubblewrap, gVisor).
- Never run untrusted code rollouts as the root user.
- Enforce strict memory limits (`execution_memory_mb`) and wall-clock execution watchdog timeouts (`execution_timeout_seconds`).

---

## 3. Reporting a Vulnerability

If you discover a security vulnerability or sandbox bypass in RewardGate, please send a responsible disclosure report to `security@rewardgate.dev`. Do not file public GitHub issues for security vulnerabilities until an advisory is coordinated.
