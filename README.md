# Solid Soup Open Engineering

Open-source Python tools for energy data, scientific computing, engineering
validation and reproducible workflows.

> **Status: energydata-kit 0.11.0 is released as a GitHub release** (built
> wheel and sdist attached to the tag; **not** on PyPI or any other index),
> after 0.1.0 to 0.10.0.
> Licensed **Apache-2.0** — the licence text is [`LICENSE`](LICENSE). The
> release decisions are recorded in
> [`RELEASE_DECISIONS.md`](docs/governance/RELEASE_DECISIONS.md); whether
> external contributions need a CLA or DCO is still open. See [release
> gates](docs/governance/RELEASE_GATES.md).

## Packages

Each package under `packages/` is independently installable, with its own
dependencies, tests and version.

| Package | Status | Description |
|---|---|---|
| [`energydata-kit`](packages/energydata-kit) | pre-alpha; 0.11.0 (GitHub release, not on PyPI) | Quality checks for energy time series: UTC timestamp normalization, gap/duplicate detection (UTC or local-calendar grids), interval semantics, unit metadata, non-destructive quality flags, reproducible reports, optional Pandera checks and an `energydata-kit report` command line |

## Quick start

```bash
cd packages/energydata-kit
python -m pip install --upgrade "pip>=25.1"
python -m pip install -e . --group dev
pytest && ruff check . && mypy
cd ../.. && python tools/check_all.py   # every check from CONTRIBUTING.md, one summary
```

## Documentation

- [Architecture overview](docs/architecture/OVERVIEW.md)
- [Existing tools audit](docs/architecture/EXISTING_TOOLS_AUDIT.md) and
  [duplication register](docs/architecture/DUPLICATION_REGISTER.md)
- [Roadmap](docs/architecture/ROADMAP.md), [public API review](docs/architecture/API_REVIEW.md)
  and [performance](docs/architecture/PERFORMANCE.md)
- [IP boundary](docs/governance/IP_BOUNDARY.md): read this before contributing
- [Release gates](docs/governance/RELEASE_GATES.md),
  [release checklist](docs/governance/RELEASE_CHECKLIST.md),
  [third-party licences](docs/governance/THIRD_PARTY_LICENSES.md) and the
  [open release decisions](docs/governance/RELEASE_DECISIONS.md)
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)
