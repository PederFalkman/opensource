# Roadmap

Only `energydata-kit` is authorized. Every item needs agreement before work
starts, and each must pass the scope test in `docs/governance/IP_BOUNDARY.md`.
Merged items stay listed here as a record of what was agreed.

## Open decisions (owners required)

Questions and evidence for each: `docs/governance/RELEASE_DECISIONS.md`.

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

## Proposed — gated, not authorized for implementation

Proposals get a `P-` label; an `OSS-` number is assigned only when work is
authorized, so numbers stay unique.

### P-1: Energy Tariff Data Quality (Engrate-inspired)

*Added by the repository owner in `46e01f1` as "OSS-16"; relabelled in
OSS-23 because OSS-16 is the release dry run (#21). Text otherwise unchanged.*

**Status: PROPOSED / DEFERRED.** Consider only after release and ownership/licensing gates G1–G7 for energydata-kit. This is a narrow, independent extension of the existing Python data-quality tooling, not a tariff calculation or commercial market product.

Scope candidate: non-destructive validation of published tariff data and schedules—effective-date coverage, overlapping rate periods, missing time bands, timestamp/DST consistency, unit/aggregation semantics, source identity, revision/version integrity and deterministic quality reports. Use synthetic fixtures and lawfully reusable public examples only; do not ingest tariff catalogues without verifying source rights.

Admission gates:
1. Complete current release, ownership and licensing decisions; do not assume Apache-2.0 is granted.
2. Perform independent IP isolation, prior-art and open-source duplication review (including tariff/price libraries) before changing the existing-tools audit.
3. Demonstrate demand for this independent developer utility; define acceptance cases and maintenance owner.
4. Authorize a small scoped PR, reusing energydata-kit quality primitives, not a new calculation stack. CI, security and release governance must pass.
5. Explicit Control Tower cross-reference: this is a standalone OSS proposal, not an active MICA reliability/calibration or capacity package.

**Out of scope:** tariff bill/cost calculations, solver optimizations, market-data downloads, live DSO catalogues, BRP messaging and operations, settlement, MICA physical modeling/capacity intelligence, customer economic scenarios and proprietary algorithms. Those remain governed separately and are not implicitly authorized by this entry.

**Ordering:** Existing OSS release gates first; P-1 assessment second; no implementation before separate approval. MICA REL-01/REL-02/VER-01 engineering priorities are unaffected.

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

### OSS-11: jump check — merged in [#16](https://github.com/PederFalkman/opensource/pull/16)

- [x] `jump_mask` and opt-in flag `JUMP` (512): change from the previous
      finite value larger than a caller-supplied limit. No built-in limits.
- [x] Wired into `flag_series`, `assess_quality`, the CLI
      (`--jump-max-delta`) and the Pandera checks (`jump_check`).
- [x] Written independently; no code taken from Pecos (which has a similar
      delta check) or any other tool.

### OSS-12: worked examples — merged in [#17](https://github.com/PederFalkman/opensource/pull/17)

- [x] `packages/energydata-kit/examples/GUIDE.md`: worked examples for
      timestamps and DST, gaps, flags, metadata and labels, local days, daily
      local-time data, opt-in checks (incl. jumps), reports, Table Schema,
      Pandera and the command line. Synthetic data only.
- [x] `tests/test_guide.py` runs every code block in order (Python blocks
      in-process, `energydata-kit` commands as subprocesses), so stale docs
      fail CI. Pandera blocks are skipped where the extra is not installed.

### OSS-13: pre-release API review — merged in [#18](https://github.com/PederFalkman/opensource/pull/18)

- [x] Rule: required inputs positional, optional arguments keyword-only;
      applied across the core API and the Pandera factories
      (`docs/architecture/API_REVIEW.md`).
- [x] `tests/test_public_api.py` pins every public signature and the rule.
- [x] Known gaps recorded (stale/counter fine-tuning options only on the
      mask functions), not changed.

### OSS-14: third-party licence evidence (G4) — merged in [#19](https://github.com/PederFalkman/opensource/pull/19)

- [x] `docs/governance/THIRD_PARTY_LICENSES.md`: licence of every direct
      dependency (runtime, Pandera extra, dev, build) and of the runtime
      dependencies' own dependencies, with sources and an assessment for
      legal review. No licence chosen for energydata-kit (G2).
- [x] `tools/check_third_party.py`: CI keeps the table in sync with
      `pyproject.toml` and rejects copyleft licences on shipped
      dependencies; `--report` lists installed runtime dependencies and
      their declared licences for refreshing the table.

### OSS-15: tuning options for the opt-in checks — merged in [#20](https://github.com/PederFalkman/opensource/pull/20)

- [x] `stale_atol`, `stale_exclude` and `counter_tolerance` on
      `flag_series`, `assess_quality`, `series_schema` and the CLI, closing
      the gap recorded in `API_REVIEW.md`. Keyword-only, recorded in the
      report `parameters`, rejected without their check.

### OSS-16: release dry run — merged in [#21](https://github.com/PederFalkman/opensource/pull/21)

- [x] `tools/release_dry_run.py`: applies the release PR edits (final
      version, dated changelog, placeholder LICENSE and licence declaration,
      upload guard removed) to a temporary copy, runs the strict readiness
      check and, with `--build`, builds, `twine check`s and inspects the
      wheel and sdist. Never changes the repository or uploads. New CI job.
- [x] Finding: a root `LICENSE` alone does not ship in the wheel or sdist.
      The readiness check now also requires an identical copy in the package
      directory, and the release checklist says so.

### OSS-17: multi-column reports — merged in [#23](https://github.com/PederFalkman/opensource/pull/23)

- [x] `assess_frame` → `FrameQualityReport`: each column gets exactly the
      `assess_quality` report, plus a combined fingerprint and a per-column
      summary. Shared options for all columns, `per_column` overrides for
      check options and metadata.
- [x] CLI: repeat `--value-col`; `--unit` and `--flags-csv` stay
      single-column and are rejected with several columns.

### OSS-18: performance check — merged in [#24](https://github.com/PederFalkman/opensource/pull/24)

- [x] `benchmarks/run.py` and `docs/architecture/PERFORMANCE.md`: measured
      times and memory on 350k–525k-row series, on the newest and the lowest
      supported dependencies.
- [x] Hot spots fixed with identical results: no full-index nanosecond copy
      (pandas 3 defaults to microseconds), sorted search instead of hashing
      for grid membership, vectorised offset detection for string timestamps.
- [x] `tests/test_performance.py`: coarse 10-second budget for a year of
      minute data (about 0.3 s today), catching accidental quadratic steps.

### OSS-19: report comparison — merged in [#25](https://github.com/PederFalkman/opensource/pull/25)

- [x] `compare_reports` → `ReportComparison`: only what differs between two
      reports (objects or saved JSON, same report schema), per series or per
      column, with deltas; plus a narrowly defined `worse` flag.
- [x] CLI `energydata-kit compare BEFORE AFTER [--fail-if-worse]`.

### OSS-20: pre-release polish — merged in [#26](https://github.com/PederFalkman/opensource/pull/26)

- [x] `tools/check_docs.py` also requires docstrings on every package module
      and public function, class, method and property; missing ones added.
- [x] README and architecture overview checked against the code: CLI
      `compare`, multi-column reports, new tools and docs, limitations.
- [x] Error messages: one consistent hint for timezone-naive input.

### OSS-21: multi-column flags — merged in [#27](https://github.com/PederFalkman/opensource/pull/27)

- [x] `flag_frame` / `flag_column`: one `quality_flag_<column>` per value
      column, each equal to `flag_series` on that column; shared options and
      `per_column` overrides as in `assess_frame`.
- [x] CLI `--flags-csv` with several `--value-col`, closing the limitation
      recorded in OSS-17 and OSS-20.

### OSS-22: release decision pack — merged in [#28](https://github.com/PederFalkman/opensource/pull/28)

- [x] `docs/governance/RELEASE_DECISIONS.md`: each open decision (visibility,
      G1 ownership, G2 licence, G3 IP review, branch protection, G7
      publication) with its owner, the evidence already in the repository,
      the questions to answer and the next step after each answer. Linked
      from the release gates, the checklist and the README. No code changes.

### OSS-23: roadmap tidy — merged in [#29](https://github.com/PederFalkman/opensource/pull/29)

- [x] One "Proposed" section instead of two; proposals labelled `P-n`
      until authorized. The owner's tariff-data proposal is now P-1 (it
      reused OSS-16, which is the release dry run); its text is unchanged
      apart from that label.

### OSS-24: release edits for 0.1.0 — merged in [#30](https://github.com/PederFalkman/opensource/pull/30)

- [x] The release edits that need no decision: version `0.1.0`, a dated
      `## [0.1.0]` changelog section (date reset on release day), README
      status. Opened as a draft to wait for the decisions; the owner merged
      it early, so `main` reads `0.1.0` although nothing is released.
- [x] Left out on purpose: the LICENSE files and `license` declaration
      (G2) and removing the upload guard (G7).
- [x] `tools/release_dry_run.py` keeps an existing dated changelog section,
      so the dry run also passes on the release branch.

### OSS-25: keep 0.1.0 on `main` until release — merged in [#31](https://github.com/PederFalkman/opensource/pull/31)

- [x] Decision: `main` stays at `0.1.0` until the gates pass (no return to
      `.dev0`). Anything added under `[Unreleased]` meanwhile is folded into
      the 0.1.0 section by the release PR.
- [x] `check_release_readiness.py`: new check *nothing left unreleased*
      (with a final version, `[Unreleased]` must be empty), so the strict
      check on the tag catches entries that were not folded in.
- [x] `release_dry_run.py` folds `[Unreleased]` into an existing dated
      section, as the release PR will.
- [x] Release decisions, checklist and roadmap updated for the merge of #30.

### OSS-26: contributor docs — merged in [#32](https://github.com/PederFalkman/opensource/pull/32)

- [x] `CONTRIBUTING.md`: the API, docstring, performance and changelog rules
      from OSS-13, OSS-18, OSS-20 and OSS-24; contribution terms point to
      decision D2 without deciding it; scope proposals become `P-n`.
- [x] PR template gains a short checks list.
- [x] Issue templates: bug report (synthetic data only), scope proposal
      (with the out-of-scope list); blank issues off and security reports
      routed to private vulnerability reporting.

### OSS-27: edge-case hardening — merged in [#33](https://github.com/PederFalkman/opensource/pull/33)

- [x] Probed the public API and CLI with empty, single-row, all-missing,
      non-numeric, naive-timestamp and malformed inputs. Most already gave
      clear results; tests now pin them.
- [x] Fixed: an unparseable timestamp in a mix with aware ones was reported
      as "mix of timezone-aware and naive"; unparseable values are now
      named with their position.
- [x] CLI hints at the delimiter when a file reads as one `;`/tab/`|`
      column; completeness documented as counting timestamps.

### OSS-28: CLI `--delimiter` and `--decimal` — merged in [#34](https://github.com/PederFalkman/opensource/pull/34)

- [x] `report` reads `;`-, tab- and `|`-separated files and decimal commas;
      the report equals that of the same data as a comma-separated file.
- [x] Invalid delimiters (several characters, letters, digits, quotes, or
      the same as `--decimal`) exit 2 with a message.

### OSS-29: security policy refresh — merged in [#35](https://github.com/PederFalkman/opensource/pull/35)

- [x] `SECURITY.md`: what to include in a report (synthetic data only), what
      is and is not a security issue, how reports are handled, history
      cleaning after a leak, how the package limits exposure, and supported
      versions; the policy for released versions is left to the first
      release.

### OSS-30: flags CSV in the input's format — merged in [#36](https://github.com/PederFalkman/opensource/pull/36)

- [x] `--flags-csv` is written with the input's `--delimiter` and
      `--decimal`, so it opens in the same tools as the input; the default
      (comma, decimal point) is unchanged.

### OSS-31: roadmap order — this change

- [x] OSS-29 and OSS-30 in order and linked to their PRs (#36 merged before
      the ordering fix reached its branch).

## Explicitly not planned

Forecasting, grid/power-flow calculations, dynamic ratings, connection
planning, economic optimization, RODOT-related algorithms, market data
download. See `IP_BOUNDARY.md`.

## New packages

No new packages until explicitly authorized. Any proposal needs a scope
statement, an IP-boundary review and an entry in the existing-tools audit.
