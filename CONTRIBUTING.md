# Contributing

This is a solo portfolio project, not run as an open-source project seeking
external contributors - but if you're exploring the code or want to suggest
a fix, here's how it's set up.

## Setup

See [docs/setup.md](docs/setup.md) for the full walkthrough (dependencies,
Azure resource provisioning, local environment, seed data).

Quick version:

```bash
uv sync
cp .env.example .env   # fill in values once resources are provisioned
uv run pytest
func start
```

## Before submitting a change

```bash
uv run pytest
uv run ruff check .
uv run black --check .
```

All three run in CI (`.github/workflows/ci.yml`) on every push/PR to `main`.

## Conventions

- Comments explain *why*, not *what* - only added where the code alone
  wouldn't make a non-obvious constraint, workaround, or empirical finding
  clear. See [docs/azure.md](docs/azure.md) for the larger architectural
  "why"s (SQL auto-pause retry behavior, Search free-tier throttling, etc.)
  that don't belong scattered in code comments.
- `src/tools/*.py` are thin Functions blueprint wrappers; real logic lives
  in `src/services/*.py` so it can be unit tested without a running
  Functions host.
- Regenerate `requirements.txt` after changing dependencies in
  `pyproject.toml`: `uv export --no-hashes --no-dev -o requirements.txt`
  (the Azure Functions deploy path reads `requirements.txt`, not
  `pyproject.toml`).
