# Contributing

Thanks for your interest. energydata-kit 0.5.0 is released on GitHub. It is licensed
Apache-2.0 (`LICENSE`), but external contributions cannot be accepted until
contribution terms are in place (see `docs/governance/RELEASE_GATES.md`).
Whether contributors will sign off commits (Developer Certificate of Origin)
or sign a contributor agreement is an open decision, D2 in
[`RELEASE_DECISIONS.md`](docs/governance/RELEASE_DECISIONS.md). Issues
(bug reports, questions, scope proposals) are welcome now.

## Before you start

1. Read [`docs/governance/IP_BOUNDARY.md`](docs/governance/IP_BOUNDARY.md).
   Contributions must be independently written, contain no proprietary
   code or data, and fall within the documented scope.
2. Check [`docs/architecture/DUPLICATION_REGISTER.md`](docs/architecture/DUPLICATION_REGISTER.md):
   prefer an existing, maintained library over new code.
3. For anything beyond a small fix, open an issue describing the change first.
   Proposals outside the current scope are recorded as `P-n` in the
   [roadmap](docs/architecture/ROADMAP.md) and are not implemented until
   authorized.

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

Or run every check below at once, with one summary at the end (from the
repository root, in the environment where the package's dev dependencies are
installed; `--quick` skips the test suites and the dry run, `--build` also
builds the wheel):

```bash
python tools/check_all.py
```

Repository-level checks:

```bash
python tools/check_ip_boundary.py
python tools/check_workflow_pins.py
python tools/check_docs.py
python tools/check_third_party.py
python tools/check_release_readiness.py --guard   # upload guard kept until D6 is recorded
python tools/check_release_readiness.py   # informational until the release gates pass
python tools/release_dry_run.py           # rehearses the release in a temp copy; --build to build too
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
  the PR, *and* get a row with its licence in
  `docs/governance/THIRD_PARTY_LICENSES.md`. Prefer no new dependency.
- Keep PRs small and focused. Update docs and the duplication register in the
  same PR when adding a capability.
- Public API: required inputs are positional and every optional argument is
  keyword-only (see `docs/architecture/API_REVIEW.md`). Signatures are pinned
  in `tests/test_public_api.py`; change that snapshot only on purpose.
- Every public function, class, method and property has a docstring
  (`tools/check_docs.py`), and every exported name is mentioned in the
  package README.
- Reports are deterministic across supported pandas, numpy and Python
  versions. `tests/test_golden.py` compares fixed reports, a flags CSV and
  fingerprints byte for byte with `tests/golden/`; after an intended change
  to report content, regenerate with `EDK_UPDATE_GOLDEN=1 pytest
  tests/test_golden.py`, review the diff and note it in the changelog.
- Performance: `tests/test_performance.py` keeps generous time budgets; a
  change that slows the year-of-minute-data cases noticeably needs a note in
  `docs/architecture/PERFORMANCE.md`.
- User-visible changes, including public API, `QualityFlag` values and the
  report schema, need an entry under `## [Unreleased]` in the package
  `CHANGELOG.md`. The released sections (`## [0.1.0]` to `## [0.4.0]`) are not edited; the
  release PR folds `[Unreleased]` into the new dated section.

## Pull request checklist

Complete the IP-boundary checklist in the PR template.
