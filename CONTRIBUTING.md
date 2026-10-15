# Contributing

Thanks for your interest. The project is pre-release and not yet licensed
for reuse (see `docs/governance/RELEASE_GATES.md`), so external contributions
cannot be accepted until a license and contribution terms are in place.

## Before you start

1. Read [`docs/governance/IP_BOUNDARY.md`](docs/governance/IP_BOUNDARY.md).
   Contributions must be independently written, contain no proprietary
   code or data, and fall within the documented scope.
2. Check [`docs/architecture/DUPLICATION_REGISTER.md`](docs/architecture/DUPLICATION_REGISTER.md):
   prefer an existing, maintained library over new code.
3. For anything beyond a small fix, open an issue describing the change first.

## Development

Each package is developed independently:

```bash
cd packages/energydata-kit
python -m pip install --upgrade "pip>=25.1"
python -m pip install -e . --group dev
python -m ruff check . && python -m ruff format --check .
python -m mypy
python -m pytest
```

Repository-level checks:

```bash
python tools/check_ip_boundary.py
python tools/check_workflow_pins.py
python tools/check_docs.py
python tools/check_release_readiness.py   # informational until the release gates pass
python -m pytest tools/tests
```

## Rules

- GitHub Actions are referenced by full commit SHA plus a version comment,
  e.g. `actions/checkout@<40-hex sha> # v7.0.1`. Never use a tag or branch.
- Python 3.11+, typed (`mypy --strict` on `src/`), formatted with Ruff.
- Tests must be deterministic: no network, no wall-clock dependence, seeded
  randomness only. Use `energydata_kit.make_synthetic_series` for data.
  Property-based tests (Hypothesis) use `derandomize=True` and no example
  database, so every run sees the same cases.
- Code blocks in `packages/energydata-kit/examples/GUIDE.md` are executed by
  `tests/test_guide.py`. Keep them runnable, and show results as `assert`
  lines rather than prose claims.
- Never add real, customer or site data to the repository.
- **New dependencies** must be added to the package `pyproject.toml` *and* to
  the allowlist in `tools/ip_boundary.toml`, with a one-line justification in
  the PR. Prefer no new dependency.
- Keep PRs small and focused. Update docs and the duplication register in the
  same PR when adding a capability.
- Public API changes, including `QualityFlag` values and the report schema,
  need a changelog entry.

## Pull request checklist

Complete the IP-boundary checklist in the PR template.
