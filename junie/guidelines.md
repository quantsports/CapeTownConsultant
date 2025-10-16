# Junie Project Guidelines
### Purpose
This file defines the persistent guardrails and conventions Junie must follow when analyzing, editing, and running this project, with an emphasis on non-breaking changes and backward compatibility. It complements existing docs by consolidating rules Junie should apply across prompts, reducing the need to restate standards in every request.[6]

### Non‑breaking contract
- Preserve all public APIs, CLI commands, and Streamlit UI routes/components; extend without removal or signature changes unless explicitly authorized and migration steps are included.
- Prefer additive changes: new flags, parameters with safe defaults, and feature toggles over behavioral changes to existing interfaces.
- Maintain data and configuration compatibility; when evolving schemas or formats, implement adapters and versioned loaders.

### Tech stack and tooling
- Python ≥ 3.10, Streamlit frontend, pytest for tests, mypy for typing, ruff for lint, black for formatting.
- Configuration comes from .env and config/; credentials must never be hardcoded and should be read via environment variables or config loaders.

### Project structure
- src/workers: background tasks, templates, context store, orchestrator.
- src/agent: autonomous decision flows and planning logic.
- src/interface: Streamlit app and CLI entry points.
- demo_orchestration.py: demo launcher; ORCHESTRATION_README.md: usage and module docs.

### Build and run
- Setup: copy .env.example to .env and fill required keys; install with pip install -r requirements.txt.
- Run app: streamlit run demo_orchestration.py; ensure local secrets are sourced from .env or IDE environment config.
- Quality gates before commits: black, ruff, mypy, pytest with coverage.

### Testing policy
- Run pytest -q --maxfail=1 --disable-warnings; use pytest-cov and prefer testcontainers for integration when external services are needed.
- Keep ≥80% coverage on core modules; add regression tests for bug fixes and ensure all existing tests pass before merging.

### Development standards
- Keep modules cohesive with clear boundaries; avoid global state; prefer dependency injection for swappable components.
- Use intention-revealing names; document public functions and CLI commands; keep Streamlit code responsive and minimal in the main thread.
- Validate inputs and fail fast with actionable errors in CLI and UI paths.

### Streamlit UI rules
- Do not remove or rename existing widgets or routes; add new ones with default-off or additive behavior to avoid breaking users’ flows.
- Keep UI computations lightweight; offload long tasks to workers; show progress and status updates for long operations.

### Orchestration and workers
- Orchestrator must remain the single coordination layer for multi-step tasks; workers are stateless or encapsulate their own state and expose stable interfaces.
- When extending workers, add new functions or parameters with defaults; do not change existing call semantics without a deprecation path.

### Agent behavior
- The agent should produce plans, propose edits, and run tests incrementally; prefer small PR-sized changes over sweeping refactors unless explicitly requested.
- Reference this guidelines.md for decisions; if ambiguity remains, prefer the safest, reversible option and add notes in commit messages.

### Configuration and secrets
- Read secrets from environment or config files only; never write secrets to code, logs, or VCS.
- Support environment overrides and local developer defaults while keeping production-safe defaults.

### Backward compatibility checklist
- Public API unchanged or extended additively; no breaking parameter order/type changes.
- CLI commands preserved; new flags are optional and default-safe; help text updated.
- Streamlit components and state keys preserved; introduce new ones without renaming existing keys.

### Safety and autonomy guardrails
- Before applying large edits, generate an implementation plan and confirm tests to run; prefer staged changes with verifiable checkpoints.
- After edits, run tests and basic type/lint checks; revert or gate changes if failures exceed threshold.

### Commit and review
- Commit messages should summarize intent, scope, and compatibility notes; link to issues if applicable.
- For refactors, include rationale and expected no-op behavior, plus any deprecation notices.

### Examples of allowed changes
- Add a new worker function with defaulted parameters and test coverage; wire through orchestrator without changing existing call sites.
- Introduce a new Streamlit sidebar section guarded by a feature flag defaulting to off; document usage in ORCHESTRATION_README.md.

### Anti‑patterns to avoid
- Renaming public functions or CLI commands without a shim; changing return types that break callers.
- Embedding secrets or environment-specific paths in code; committing .env files.