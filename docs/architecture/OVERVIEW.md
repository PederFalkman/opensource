# Architecture overview

## Repository layout

```
opensource/
├── README.md, CONTRIBUTING.md, SECURITY.md
├── ruff.toml                    # lint config for tools/ only
├── docs/
│   ├── architecture/            # this file, audit, duplication register, roadmap
│   └── governance/              # IP boundary, release gates, release checklist
├── packages/
│   └── energydata-kit/          # the only package authorized so far
│       ├── pyproject.toml       # own metadata, deps, lint/type/test config
│       ├── README.md
│       ├── src/energydata_kit/
│       ├── tests/
│       └── examples/
├── tools/
│   ├── check_ip_boundary.py     # CI tripwire (stdlib only)
│   ├── check_workflow_pins.py   # actions pinned to commit SHAs
│   ├── check_release_readiness.py # mechanical release conditions
│   ├── check_docs.py            # docs match the code (public API, flags, links)
│   ├── ip_boundary.toml         # import denylist + dependency allowlists
│   └── tests/
└── .github/
    ├── workflows/ci.yml         # IP boundary, lint, types, tests, packaging
    ├── workflows/security.yml   # gitleaks, pip-audit, dependency review
    ├── workflows/release-build.yml # build + attest on release tags; never publishes
    ├── dependabot.yml
    └── CODEOWNERS
```

## Monorepo principles

- **Independently installable packages.** Each directory under `packages/` is
  a self-contained Python project with its own `pyproject.toml`, version,
  dependencies, tests and README. No package imports another through relative
  paths, and there is no root-level Python project or shared virtual
  environment.
- **No workspace tooling yet.** Plain `pip` + `pyproject.toml` (PEP 621,
  PEP 735 dependency groups) is enough for one package. A workspace manager
  (e.g. uv workspaces) can be added when a second package exists and the
  need is concrete.
- **Per-package CI jobs.** Each package gets its own CI job with
  `working-directory` set to the package. A new package adds a job; it does
  not change existing ones.
- **Shared tooling stays small.** `tools/` uses the standard library only, so
  it runs without installing anything.

## energydata-kit design

```
                 ┌────────────────────┐
 raw timestamps ─► timestamps.py      │ normalize_timestamps → tz-aware UTC (ns)
                 └─────────┬──────────┘
                           │ DatetimeIndex (UTC)
        ┌──────────────────┼────────────────────┐
        ▼                  ▼                    ▼
  intervals.py        flags.py             metadata.py
  gaps, duplicates,   value masks +        MeasurementMetadata,
  off-grid, grid      QualityFlag bitmask  units via Pint
        └──────────────────┬────────────────────┘
                           ▼
                      report.py  → QualityReport (deterministic JSON + SHA-256 fingerprint)

  semantics.py → interval labels, metadata consistency, local-day completeness (feeds report.py)
  table_schema.py → Frictionless Table Schema export/import of MeasurementMetadata
  pandera_checks.py → optional [pandera] extra: the same masks as Pandera checks (not imported by default)
  synthetic.py → seeded test series with explicitly placed defects
  cli.py → `energydata-kit report` command line over assess_quality / flag_series
```

Key decisions:

| Decision | Rationale |
|---|---|
| Normalize to UTC before any check | DST days (23 h / 25 h locally) become regular in UTC, so they are never reported as gaps or duplicates. Policies for ambiguous and nonexistent local times are explicit (`raise` by default). |
| Flags are a `uint16` bitmask in a separate column | Non-destructive, composable (one row can have several issues), compact, language-neutral. Bit values are a public contract. |
| No silent guessing | Naive timestamps need `assume_tz`. Grid checks need a stated step (`freq` or `metadata.resolution`); the inferred step is reported but not used. |
| Reports have no wall-clock time | Same input + parameters + version → byte-identical JSON. The fingerprint covers UTC ns timestamps, canonicalized float64 values and the series name, so it does not depend on pandas' datetime resolution or display time zone. |
| pandas, numpy, Pint as the only required runtime dependencies (Pandera is an optional extra) | Mature, permissively licensed (BSD), already ubiquitous in energy data work. No schema engine, unit system or I/O layer is reimplemented. |
| Pint registry extended with `var` | Pint has no reactive-power unit; `var` is defined as dimensionally equal to `VA`. |
| Calendar grids only with an explicit `tz` | Daily and longer steps in local time are laid out by pandas in wall-clock time (23/25-hour DST days). They are never inferred from metadata, so a fixed `"1D"` step stays 24 h in UTC unless the caller says otherwise. |
| Opt-in checks for stale values and counters | A sensible run length depends on the signal, and whether a series is cumulative is the caller's knowledge; both stay off by default. |
| CLI is a thin layer | `energydata-kit report` only parses arguments and CSV, then calls `assess_quality` / `flag_series`; exit status 1 for issues (with `--fail-on-issues`), 2 for input errors. |

## Supported versions

- Python 3.11, 3.12, 3.13 (CI matrix).
- Lowest supported runtime dependencies are tested in CI: numpy 1.26,
  pandas 2.1, Pint 0.24. Latest tested locally: pandas 3.0, Pint 0.26.
