# Solid Soup Open Engineering

Open-source Python tools for energy data, scientific computing, engineering
validation and reproducible workflows.

> **Status: pre-release.** Nothing is published and **no open-source license
> has been granted yet**. Licensing (Apache-2.0 preferred) is pending ownership
> and legal review; see [release gates](docs/governance/RELEASE_GATES.md).

## Packages

Each package under `packages/` is independently installable, with its own
dependencies, tests and version.

| Package | Status | Description |
|---|---|---|
| [`energydata-kit`](packages/energydata-kit) | pre-alpha | Quality checks for energy time series: UTC timestamp normalization, gap/duplicate detection (UTC or local-calendar grids), interval semantics, unit metadata, non-destructive quality flags, reproducible reports, optional Pandera checks and an `energydata-kit report` command line |

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
