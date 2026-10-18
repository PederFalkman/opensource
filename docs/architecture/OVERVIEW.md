# Architecture overview

## Repository layout

```
opensource/
├── README.md, CONTRIBUTING.md, SECURITY.md
├── ruff.toml                    # lint config for tools/ only
├── docs/
│   ├── architecture/            # this file, audit, duplication register, roadmap,
│   │                            # API review, performance
│   └── governance/              # IP boundary, release gates and checklist,
│                                # third-party licences
├── packages/
│   └── energydata-kit/          # the only package authorized so far
│       ├── pyproject.toml       # own metadata, deps, lint/type/test config
│       ├── README.md
│       ├── src/energydata_kit/
│       ├── tests/               # golden/: pinned reports, compared byte for byte
│       ├── examples/            # runnable script + GUIDE.md (executed by the tests)
│       └── benchmarks/          # run.py: timings on long series
├── tools/
│   ├── check_all.py             # runs every check below plus lint, types and tests
│   ├── check_ip_boundary.py     # CI tripwire (stdlib only)
│   ├── check_workflow_pins.py   # actions pinned to commit SHAs
│   ├── check_release_readiness.py # mechanical release conditions
│   ├── check_docs.py            # docs match the code (public API, flags, links, docstrings)
│   ├── check_third_party.py     # licence table matches the declared dependencies
│   ├── release_dry_run.py       # rehearses the release in a temporary copy
│   ├── ip_boundary.toml         # import denylist + dependency allowlists
│   └── tests/
└── .github/
    ├── workflows/ci.yml         # IP boundary, lint, types, tests, packaging, release dry run
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
                      frame_report.py → FrameQualityReport and flag_frame (per column)
                      compare.py → ReportComparison (what changed between two reports)

  semantics.py → interval labels, metadata consistency, local-day completeness (feeds report.py)
  table_schema.py → Frictionless Table Schema export/import of MeasurementMetadata
  pandera_checks.py → optional [pandera] extra: the same masks as Pandera checks (not imported by default)
  synthetic.py → seeded test series with explicitly placed defects
  cli.py → `energydata-kit report` / `compare` over assess_quality, assess_frame, flag_series, flag_frame, compare_reports
```

Key decisions:

| Decision | Rationale |
|---|---|
| Normalize to UTC before any check | DST days (23 h / 25 h locally) become regular in UTC, so they are never reported as gaps or duplicates. Policies for ambiguous and nonexistent local times are explicit (`raise` by default). |
| Flags are a `uint16` bitmask in a separate column | Non-destructive, composable (one row can have several issues), compact, language-neutral. Bit values are a public contract. |
| No silent guessing | Naive timestamps need `assume_tz`. Grid checks need a stated step (`freq` or `metadata.resolution`); the inferred step is reported but not used. |
| Reports have no wall-clock time | Same input + parameters + version → byte-identical JSON. The fingerprint covers UTC ns timestamps, canonicalized float64 values and the series name, so it does not depend on pandas' datetime resolution or display time zone. |
| pandas, numpy, Pint as the only required runtime dependencies (Pandera and pyarrow are optional extras, for Pandera checks and Parquet input) | Mature, permissively licensed (BSD), already ubiquitous in energy data work. No schema engine, unit system or I/O layer is reimplemented. |
| Pint registry extended with `var` | Pint has no reactive-power unit; `var` is defined as dimensionally equal to `VA`. |
| Calendar grids only with an explicit `tz` | Daily and longer steps in local time are laid out by pandas in wall-clock time (23/25-hour DST days). They are never inferred from metadata, so a fixed `"1D"` step stays 24 h in UTC unless the caller says otherwise. |
| Opt-in checks for stale values, counters and jumps | A sensible run length or jump limit depends on the signal, and whether a series is cumulative is the caller's knowledge; all three stay off by default and the package ships no limits. |
| CLI is a thin layer | `energydata-kit report` and `compare` only parse arguments, CSV and JSON, then call the library (`assess_quality`, `assess_frame`, `flag_series`, `flag_frame`, `compare_reports`); exit status 1 for issues (`--fail-on-issues`, `--fail-if-worse`), 2 for usage, input and file errors. |

## Supported versions

- Python 3.11, 3.12, 3.13, 3.14 (CI matrix).
- Linux for every check; the tests also run on Windows and macOS (CI).
- Lowest supported runtime dependencies are tested in CI: numpy 1.26,
  pandas 2.1, Pint 0.24. Latest tested locally: pandas 3.0, Pint 0.26.
