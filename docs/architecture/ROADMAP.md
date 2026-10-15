# Roadmap

Only `energydata-kit` is authorized. Every item needs agreement before work
starts, and each must pass the scope test in `docs/governance/IP_BOUNDARY.md`.
Merged items stay listed here as a record of what was agreed.

## Open decisions (owners required)

- [ ] **Repository visibility.** The repo is already public; decide whether to
      make it private until release gates G1–G3 pass (see `RELEASE_GATES.md`).
- [ ] **Ownership and license (G1/G2).** Apache-2.0 is the preferred candidate.
- [ ] **Branch protection on `main`:** require CI + code-owner review.
- [x] **Pin GitHub Actions to commit SHAs.** Done in OSS-06.

## Deferred

- **pint-pandas support** (from OSS-04). Supporting `var` would mean changing
  pint-pandas' process-wide unit registry, which silently affects any other
  pint-pandas user in the same process. Plain
  `series.astype(f"pint[{meta.unit}]")` already works for Pint's built-in
  units. Revisit if users need it.

## Proposed

Nothing is proposed at the moment. New items are agreed first, then added here.

## Done

### OSS-01: foundation — merged in [#1](https://github.com/PederFalkman/opensource/pull/1)

- [x] Monorepo layout, governance and architecture docs.
- [x] energydata-kit scaffold: timestamps, gaps/duplicates/off-grid, value
      masks, bitmask flags, unit metadata, deterministic reports, synthetic data.
- [x] CI: Ruff, mypy (strict), pytest on Python 3.11–3.13 plus lowest deps,
      wheel build + clean-install test.
- [x] IP-boundary checker, gitleaks, pip-audit, dependency review, Dependabot,
      CODEOWNERS.

### OSS-02: interval semantics — merged in [#2](https://github.com/PederFalkman/opensource/pull/2)

- [x] `relabel_intervals` / `interval_bounds`: explicit start/end conversion
      (no silent shifts).
- [x] `check_metadata_consistency`: unit vs. aggregation advice
      (`SUM_OF_POWER`, `AVERAGED_ENERGY`, `MISSING_RESOLUTION`,
      `LABEL_ON_INSTANTANEOUS`).
- [x] `local_day_completeness`: expected 92/96/100 intervals per local day at
      15 min, as a report section.

### OSS-03: additional generic checks — merged in [#7](https://github.com/PederFalkman/opensource/pull/7)

- [x] `stale_mask`: stale / flat-line detection (opt-in `STALE_VALUE` flag).
- [x] `counter_decrease_mask`: cumulative-counter resets and rollovers
      (opt-in `COUNTER_DECREASE` flag).
- [x] Pecos/pvanalytics compared at the documentation level; implemented
      independently.

### OSS-04: interoperability — merged in [#8](https://github.com/PederFalkman/opensource/pull/8)

- [x] Optional `[pandera]` extra: `energydata_kit.pandera_checks`.
- [x] `to_table_schema` / `from_table_schema`: Frictionless Table Schema.
- [ ] pint-pandas support: deferred (see above).

### OSS-05: grid limitations — merged in [#10](https://github.com/PederFalkman/opensource/pull/10)

Landed via [#10](https://github.com/PederFalkman/opensource/pull/10) after [#9](https://github.com/PederFalkman/opensource/pull/9) merged into its stacked base instead of `main`.

- [x] Explicit grid `origin`, so a leading off-grid timestamp no longer shifts
      the grid.
- [x] Local-calendar steps (`tz=`) for daily, weekly and monthly data in local
      time, DST-aware. Explicit only; never inferred from metadata.

### OSS-06: supply-chain hardening — merged in [#11](https://github.com/PederFalkman/opensource/pull/11)

- [x] Every GitHub Action pinned to a full commit SHA with a version comment;
      Dependabot (`github-actions`) keeps pins and comments current.
- [x] `tools/check_workflow_pins.py` fails CI on tags, branches, short SHAs or
      undigested Docker images.
- [x] `persist-credentials: false` on every checkout; job permissions stay
      read-only except dependency review (PR comments) and release attestation.
- [x] Duplicated checkout / setup-python / dependency-review steps from an
      earlier merge removed.

### OSS-07: command-line tool — merged in [#12](https://github.com/PederFalkman/opensource/pull/12)

- [x] `energydata-kit report data.csv ...` printing the JSON quality report,
      with timestamp, grid, check and metadata options.
- [x] Optional flagged CSV (`--flags-csv`, `--insert-missing`).
- [x] Exit status for pipelines: `--fail-on-issues` → 1; input errors → 2
      without a traceback.

### OSS-08: release preparation — merged in [#13](https://github.com/PederFalkman/opensource/pull/13)

Everything short of publishing. License and publication stay blocked on gates
G1–G7 in `docs/governance/RELEASE_GATES.md`.

- [x] `tools/check_release_readiness.py`: mechanical release conditions,
      report or `--strict`.
- [x] `.github/workflows/release-build.yml`: build + `twine check` on demand;
      on a release tag, strict readiness check and build provenance
      attestation. No upload to any index.
- [x] `docs/governance/RELEASE_CHECKLIST.md`: release PR template.

### OSS-09: docs housekeeping — merged in [#14](https://github.com/PederFalkman/opensource/pull/14)

- [x] Roadmap reorganised: open decisions, deferred, proposed, done (in order,
      with the PR that merged each item).
- [x] Architecture overview and existing-tools audit updated for OSS-02–OSS-08.
- [x] `tools/check_docs.py`: public API names and flags documented in the
      package README, `## [Unreleased]` in each changelog, no broken relative
      links. Runs in CI.

### OSS-10: property-based tests — merged in [#15](https://github.com/PederFalkman/opensource/pull/15)

- [x] Hypothesis tests (dev-only, deterministic: `derandomize=True`, no example
      database) for non-destructive flagging, flag bits vs. masks, gap
      accounting, report determinism, fingerprint invariance, label round
      trips, stale/counter masks vs. brute-force references, local-day bounds
      and Table Schema round trips.
- [x] `hypothesis` added to the dev group and the dependency allowlist
      (MPL-2.0; test-only, never shipped or copied).

### OSS-11: jump check — this change

- [x] `jump_mask` and opt-in flag `JUMP` (512): change from the previous
      finite value larger than a caller-supplied limit. No built-in limits.
- [x] Wired into `flag_series`, `assess_quality`, the CLI
      (`--jump-max-delta`) and the Pandera checks (`jump_check`).
- [x] Written independently; no code taken from Pecos (which has a similar
      delta check) or any other tool.

## Explicitly not planned

Forecasting, grid/power-flow calculations, dynamic ratings, connection
planning, economic optimization, RODOT-related algorithms, market data
download. See `IP_BOUNDARY.md`.

## New packages

No new packages until explicitly authorized. Any proposal needs a scope
statement, an IP-boundary review and an entry in the existing-tools audit.
