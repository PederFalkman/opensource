# Roadmap

Only `energydata-kit` is authorized. Everything below is a proposal; each item
needs agreement before work starts, and each must pass the scope test in
`docs/governance/IP_BOUNDARY.md`.

## OSS-01: foundation (this change)

- [x] Monorepo layout, governance and architecture docs
- [x] energydata-kit scaffold: timestamps, gaps/duplicates/off-grid, value
      masks, bitmask flags, unit metadata, deterministic reports, synthetic data
- [x] CI: Ruff, mypy (strict), pytest on Python 3.11–3.13 plus lowest deps,
      wheel build + clean-install test
- [x] IP-boundary checker, gitleaks, pip-audit, dependency review, Dependabot,
      CODEOWNERS

## Open decisions (owners required)

- [ ] **Repository visibility.** The repo is already public; decide whether to
      make it private until release gates G1–G3 pass (see `RELEASE_GATES.md`).
- [ ] **Ownership and license (G1/G2).** Apache-2.0 is the preferred candidate.
- [ ] **Branch protection on `main`:** require CI + code-owner review.
- [ ] **Pin GitHub Actions to commit SHAs** (currently major-version tags).

## OSS-02: interval semantics (in progress)

- [x] Use `MeasurementMetadata.interval_label` to convert between start- and
      end-labelled timestamps explicitly (no silent shifts).
- [x] Consistency checks between `aggregation` and unit dimensionality (e.g. a
      `sum` of power, or a `mean` of energy, is suspicious → advisory issue).
- [x] Local-calendar-day completeness (expected 92/96/100 intervals per local
      day at 15 min) as a report section.

## OSS-03: additional generic checks (in progress)

- [x] Stale / flat-line detection (constant values over N intervals).
- [x] Monotonic cumulative-counter checks (meter register resets/rollovers).
- [x] Reference Pecos/pvanalytics for behavior; implement independently.

## OSS-04: interoperability (in progress)

- [x] Optional Pandera integration (expose checks as Pandera checks).
- [x] Export metadata as frictionless Table Schema.
- [ ] Optional pint-pandas support. **Deferred:** supporting `var` would mean
      changing pint-pandas' process-wide unit registry, which silently affects
      any other pint-pandas user in the same process. Plain
      `series.astype(f"pint[{meta.unit}]")` already works for Pint's built-in
      units. Revisit if users need it.

## Explicitly not planned

Forecasting, grid/power-flow calculations, dynamic ratings, connection
planning, economic optimization, RODOT-related algorithms, market data
download. See `IP_BOUNDARY.md`.

## New packages

No new packages until explicitly authorized. Any proposal needs a scope
statement, an IP-boundary review and an entry in the existing-tools audit.
