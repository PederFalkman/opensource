# Roadmap

Only `energydata-kit` is authorized. Every item needs agreement before work
starts, and each must pass the scope test in `docs/governance/IP_BOUNDARY.md`.
Merged items stay listed here as a record of what was agreed.

## Open decisions (owners required)

Questions and evidence for each: `docs/governance/RELEASE_DECISIONS.md`.
Engineering for 0.1.0 is complete; the release waits only on these.

- [ ] **D1 Repository visibility.** The repo is public and, since #66,
      Apache-2.0 licensed; decide whether it stays public while G1 and G3
      are open.
- [ ] **D2 Ownership (G1).** Counsel confirms the publishing entity owns the
      code and can license it (and confirms the G4 licence table).
- [x] **D3 Licence (G2).** Apache-2.0, granted 2026-10-18 (#66).
- [ ] **D4 IP boundary review (G3).** A signed review on the release commit.
- [ ] **D5 Branch protection on `main`** (not a gate): require CI and
      code-owner review.
- [ ] **D6 Publication (G7).** PyPI or GitHub-only, the name, the account
      owner; approval removes the upload guard, the readiness check's only
      remaining failure.
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

### P-2 to P-6: candidates after 0.1.0 (OSS-53)

*Prepared by the assistant in OSS-53 for the owner to approve or reject one
by one. Same rules as P-1: nothing here is authorized, and none of it starts
before the 0.1.0 release gates pass.* Each item is generic data-quality
tooling as defined in `IP_BOUNDARY.md` ("What *is* in scope"); none touches
the out-of-scope list (no forecasting, grid calculations, ratings,
connection planning, optimization or decision support).

| ID | Candidate | Why | Effort | Risk and cost |
|---|---|---|---|---|
| P-2 | *Approved by the owner on 2026-10-17 ahead of the release gates; done in OSS-56, as fields in report schema 1 because 0.1.0 is unreleased.* **Expected-outage windows.** Callers pass known periods (maintenance, a meter swap); gaps inside them are reported separately from unexplained gaps, and completeness can exclude them. | The most common false alarm in gap reports is a gap everyone already knew about. | M | New report fields, so report schema 2 or an optional section; `compare_reports` must handle both. No new dependency. |
| P-3 | *Approved by the owner on 2026-10-17 ahead of the release gates; done in OSS-54.* **JSON Schema for the report format.** Publish schema "1" as a JSON Schema file in the package; a test validates every golden report against it. | Lets non-Python consumers (pipelines, dashboards) validate reports without reading our code. | S | Small; the schema file becomes a public contract to maintain. Test-only dependency (`jsonschema`, MIT) or a hand-written check. |
| P-4 | *Approved by the owner on 2026-10-17 ahead of the release gates; done in OSS-55.* **Markdown output** (`report --format markdown`, `compare --format markdown`). | Pasting a readable summary into an issue or PR is a frequent use of `--format text`. | S | Low; formatting only, no new dependency. Must not become a second report format that drifts from JSON. |
| P-5 | *Approved by the owner on 2026-10-18 ahead of the release gates; done in OSS-58.* **Parquet input for the command line** (optional `[parquet]` extra). | Large meter exports increasingly come as Parquet; the library already accepts any pandas Series. | S–M | New optional dependency (pyarrow, Apache-2.0): allowlist, licence table and CI matrix entry. Read-only; no writing of Parquet. |
| P-6 | *Approved by the owner on 2026-10-17 as an additive section (columns unchanged); done in OSS-57.* **Shared timestamp section in frame reports.** `assess_frame` repeats gaps, duplicates and off-grid per column (a known limitation); report them once at frame level. | Smaller, clearer multi-column reports. | M | Breaking report change (schema 2) and a `compare_reports` migration path; worth doing only together with another schema change such as P-2. |

Considered and not proposed: Polars or other DataFrame inputs (a second
data model to maintain for little gain; pandas conversion is one call),
resampling or gap filling (changes data, against the non-destructive rule),
and anything that downloads data.

**Suggested order if approved:** P-3 and P-4 first (small, no schema change),
then P-2 with P-6 as one schema-2 change, then P-5 if users ask for it.

## Done

### Pre-release hardening at a glance (OSS-40 to OSS-65)

For the release reviewers: every part of the package was probed after the
features were in, each with regression tests that fail on the code before
the fix. Details are in the entries below and in the pull requests.

| Area | Items | What was probed | Real bugs fixed |
|---|---|---|---|
| Core API, grids, timestamps | OSS-40, 41, 44 | Fuzzing on pandas 2.1 and 3; about 130 edge cases | Calendar grids and `origin`, DST errors, NaN in JSON, numpy options, `NaT` |
| Determinism | OSS-42 | Reports on old and new Python, pandas, numpy | None; golden tests now pin the bytes |
| Command line | OSS-43, 52 | 3,000 random CSVs; Windows and macOS | Tracebacks with exit 1; CRLF output on Windows |
| Comparisons | OSS-47 | 5,500 real and mutated report pairs | Saved comparisons accepted as reports |
| Table Schema | OSS-49 | 500 round trips, 3,000 mutated schemas | Silent column relabelling; raw `KeyError`s |
| Newer features | OSS-59 | Known outages against a brute-force reference; Markdown; JSON Schema | Generator outages lost; wrong counts above 10**6 intervals |
| Parquet | OSS-62 | Dtypes, timestamp forms, corrupt files | Timestamp index unreadable; directory crash |
| Pandera | OSS-64 | 400 series against `flag_series`; Pandera 0.24 | Index checks broken on 0.24; unsorted input; invalid JSON options |
| Options | OSS-65 | Every option with wrong types, booleans, text | Unknown `tz` traceback; reports failing their JSON Schema |

Performance was re-checked after the input checks (OSS-50): no regression.

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

### OSS-31: roadmap order — merged in [#37](https://github.com/PederFalkman/opensource/pull/37)

- [x] OSS-29 and OSS-30 in order and linked to their PRs (#36 merged before
      the ordering fix reached its branch).

### OSS-32: readable CLI summary — merged in [#38](https://github.com/PederFalkman/opensource/pull/38)

- [x] `report --format text`: rows, completeness, flag counts, the first
      three gaps and metadata issues per column. JSON stays the default and
      the format for automation; `-o` and `--fail-on-issues` behave the same.

### OSS-33: readable comparison summary — merged in [#39](https://github.com/PederFalkman/opensource/pull/39)

- [x] `compare --format text`: the verdict (same data or changed; worse or
      not), then count, flag, gap, metadata-issue and parameter changes per
      column. JSON stays the default; `--fail-if-worse` behaves the same.

### OSS-34: guide covers the newer CLI options — merged in [#40](https://github.com/PederFalkman/opensource/pull/40)

- [x] `examples/GUIDE.md` section 11 shows `--format text` for reports and
      comparisons and reading a `;`/decimal-comma export with `--delimiter`
      and `--decimal`; the test suite runs these blocks and checks their
      output, so the guide cannot drift from the CLI.

### OSS-35: Table Schema metadata in the CLI — merged in [#41](https://github.com/PederFalkman/opensource/pull/41)

- [x] `report --schema`: metadata per column from a Table Schema written by
      `to_table_schema`; its columns are the default `--value-col` and its
      resolution the step without `--freq`. Lifts the one-column limit of
      `--unit`. Conflicting options and unusable schemas exit 2.

### OSS-36: release decision facts refreshed — merged in [#42](https://github.com/PederFalkman/opensource/pull/42)

- [x] `RELEASE_DECISIONS.md` D2: commit and authorship counts as of `eafdb8c`
      (90 commits; same categories as in OSS-22) with the command to recount.
      D6: PyPI and TestPyPI names re-checked, still free.

### OSS-37: 0.1.0 release notes — merged in [#43](https://github.com/PederFalkman/opensource/pull/43)

- [x] `CHANGELOG.md` 0.1.0 rewritten as first-release notes, grouped by area
      (timestamps, flags, metadata, reports, command line, integrations,
      conventions) instead of development history; the `[Unreleased]`
      entries (OSS-27 to OSS-35) folded in, as the release PR would have.
      Later changes still go under `[Unreleased]`.

### OSS-38: one-command local checks — merged in [#44](https://github.com/PederFalkman/opensource/pull/44)

- [x] `tools/check_all.py` (standard library only) runs every check in
      `CONTRIBUTING.md`: lint, format, mypy and tests per package, the
      repository checks, the tools tests and the release dry run, with the
      readiness report as information. It keeps going after a failure and
      prints one summary with the output of failed checks. `--quick` and
      `--build` options. A test keeps it in sync with `CONTRIBUTING.md`.

### OSS-39: roadmap up to date — merged in [#45](https://github.com/PederFalkman/opensource/pull/45)

- [x] OSS-38 linked to #44. Engineering for 0.1.0 is complete; the release
      waits on decisions D1–D6 in `docs/governance/RELEASE_DECISIONS.md`.

### OSS-40: pre-release bug hunt — merged in [#46](https://github.com/PederFalkman/opensource/pull/46)

- [x] Reviewed grids, flags, timestamps, reports and the CLI and fuzzed the
      public API (unsorted, duplicate, off-grid, NaN/inf/text values, DST
      days, `origin`, `tz`, all checks) on pandas 2.1 and 3.
- [x] Fixed: calendar grids ignored points before a later `origin`;
      `ZeroDivisionError` when no grid point falls in the span; raw DST
      errors from calendar grids; two CLI messages. Each has a regression
      test that fails on the previous code.

### OSS-41: pre-release bug hunt, part 2 — merged in [#47](https://github.com/PederFalkman/opensource/pull/47)

- [x] Fuzzed the Pandera checks against `flag_series` / `assess_quality`
      (1,500 random series, pandas 2.1 and 3) and probed metadata, Table
      Schema, frame reports and comparisons.
- [x] Fixed: units with stray characters accepted (Pint drops them);
      `Timedelta` resolutions breaking JSON reports; a leading gap missed by
      the Pandera gap check; duplicate `quality_flag` fields in a Table
      Schema; unchecked `per_column` metadata names. Regression tests fail on
      the previous code.

### OSS-42: cross-version determinism — merged in [#48](https://github.com/PederFalkman/opensource/pull/48)

- [x] Generated reports (single series with every check, local days across
      DST, frame, comparison), a flags CSV and fingerprints on Python 3.13 /
      pandas 3.0.6 / numpy 2.5 and Python 3.11 / pandas 2.1.4 / numpy 1.26:
      byte-identical, so no fix was needed.
- [x] `tests/test_golden.py` pins them in `tests/golden/` (version masked),
      so CI on every supported version and the lowest dependencies catches
      drift. Regeneration documented in `CONTRIBUTING.md`.

### OSS-43: command-line bug hunt — merged in [#49](https://github.com/PederFalkman/opensource/pull/49)

- [x] Fuzzed `energydata-kit report` in-process with 3,000 random CSVs (`,`
      `;` tab, decimal commas, bad and DST timestamps, odd values, missing
      or duplicate columns) and option combinations; every run must exit 0,
      1 or 2, with a message on 2 and valid JSON on success.
- [x] Fixed: file-system errors on input or output paths escaped as
      tracebacks with exit status 1 (read as "issues found"); they now exit
      2 with a message. Regression test fails on the previous code.

### OSS-44: Python API bug hunt — merged in [#50](https://github.com/PederFalkman/opensource/pull/50)

- [x] Probed about 130 edge-case inputs across the exported functions (odd
      steps, numpy scalars, `NaT`, empty and wrongly typed inputs, flag
      values out of range).
- [x] Fixed: `NaN` in report JSON for steps longer than a local day; numpy
      scalar options breaking `to_json()`; `NaT` indexes accepted silently;
      `normalize_timestamps` on empty input or a single string;
      `decode_flags` on negative or unknown bits; non-string metadata
      `name`/`timezone`. Regression tests fail on the previous code.

### OSS-45: documentation polish — merged in [#51](https://github.com/PederFalkman/opensource/pull/51)

- [x] Re-read the READMEs, guide, architecture overview and docstrings
      against the behaviour after OSS-40 to OSS-44: exit status 2 now
      covers file errors; days shorter than one step are a documented
      limitation; docstrings mention `NaT`, empty and numpy inputs; the
      overview lists `check_all.py` and the golden tests.

### OSS-46: exit statuses in `--help` — merged in [#52](https://github.com/PederFalkman/opensource/pull/52)

- [x] `energydata-kit --help`, `report --help` and `compare --help` list
      the exit statuses (follow-up from OSS-45), pinned by a test.

### OSS-47: comparison bug hunt — merged in [#53](https://github.com/PederFalkman/opensource/pull/53)

- [x] Fuzzed `compare_reports` with 100 real single-series and frame
      reports (1,500 real pairs, 4,000 with keys deleted or values
      replaced). Real reports compared cleanly.
- [x] Fixed: a saved comparison (also schema "1") was accepted as a
      report, and hand-edited reports crashed; with `--fail-if-worse`
      both read as "worse". Non-report input now raises `ValueError`
      naming the first bad field, and the command exits 2. Regression
      tests fail on the previous code.

### OSS-48: release-readiness refresh — merged in [#54](https://github.com/PederFalkman/opensource/pull/54)

- [x] Folded the `[Unreleased]` changelog entries from OSS-40 to OSS-47
      into the unreleased 0.1.0 notes as the behaviour users will see
      (bug-by-bug detail stays here and in the git history).
- [x] Refreshed the facts in `RELEASE_DECISIONS.md`: commit counts, the
      PyPI name check (still free), the G6 review. The readiness check now
      fails only on LICENSE, the licence declaration and the upload guard,
      which wait on D2, D3 and D6.

### OSS-49: Table Schema bug hunt — merged in [#55](https://github.com/PederFalkman/opensource/pull/55)

- [x] Round-tripped 500 random metadata sets through `to_table_schema` /
      `from_table_schema` (all equal) and fed 3,000 mutated schemas to
      `from_table_schema` and `energydata-kit report --schema`. The command
      line always exited 0, 1 or 2.
- [x] Fixed: a `name` inside the `energydata_kit` property silently
      relabelled the column's metadata; malformed schemas raised
      `KeyError`/`AttributeError`. Both now raise `ValueError` naming the
      problem. Regression tests fail on the previous code.

### OSS-50: performance re-check — merged in [#56](https://github.com/PederFalkman/opensource/pull/56)

- [x] Re-ran `benchmarks/run.py` on Python 3.13 / pandas 3.0.6 and
      Python 3.11 / pandas 2.1.4 after the input checks of OSS-40 to
      OSS-49: no regression, peak memory unchanged. `PERFORMANCE.md`
      updated; `compare_reports` with its new input check takes ~0.4 ms.

### OSS-51: Python 3.14 — merged in [#57](https://github.com/PederFalkman/opensource/pull/57)

- [x] Ran the full suite (warnings as errors, golden reports included),
      ruff and mypy on Python 3.14.6 with pandas 3.0.6, numpy 2.5.4 and
      Pint 0.26.1: all pass with no code change.
- [x] Added 3.14 to the CI test matrix and the package classifiers.

### OSS-52: Windows and macOS — merged in [#58](https://github.com/PederFalkman/opensource/pull/58)

- [x] Reviewed every file write for Windows: `-o` files (`Path.write_text`)
      and `--flags-csv` (pandas' `os.linesep`) got `\r\n` line endings,
      so reports were not byte-identical across platforms. Both now write
      `\n` everywhere; a regression test fails on the previous code.
- [x] CI runs the tests, golden reports included, on Windows and macOS.

### OSS-53: post-0.1.0 proposals — merged in [#59](https://github.com/PederFalkman/opensource/pull/59)

- [x] Added candidates P-2 to P-6 (expected-outage windows, a JSON Schema
      for reports, Markdown output, Parquet input, a shared timestamp
      section in frame reports) to "Proposed — gated", each with effort,
      risk and dependency cost, for the owner to approve or reject. None
      is authorized; no code changed.

### OSS-54: JSON Schema for reports (P-3) — merged in [#60](https://github.com/PederFalkman/opensource/pull/60)

- [x] `energydata_kit/report_schema.json` (draft 2020-12) describes report
      schema 1: single-series reports, frame reports and comparisons, with
      no unknown fields allowed. Shipped in the wheel (checked in CI).
- [x] Tests validate the golden reports and ten generated ones (no step,
      empty, metadata issues, every check, calendar grid, step longer than a
      day, frames, comparisons) and reject seven kinds of broken report.
- [x] `jsonschema` (MIT) added as a dev dependency only: allowlist and
      licence table updated.

### OSS-55: Markdown output (P-4) — merged in [#61](https://github.com/PederFalkman/opensource/pull/61)

- [x] `--format markdown` for `report` and `compare`: headings per column
      and bullet lists, column names escaped.
- [x] Text and Markdown are rendered from the same facts; the text output
      was compared byte for byte with the previous code (unchanged), and a
      test checks every text fact appears in the Markdown.

### OSS-56: known outages (P-2) — merged in [#62](https://github.com/PederFalkman/opensource/pull/62)

- [x] `known_outages` for `assess_quality` and `assess_frame` and
      `--known-outage START END` for the command line: timezone-aware
      periods, both ends included, validated.
- [x] Reports add `n_missing_explained`, `completeness_excluding_outages`
      and `parameters.known_outages`; gaps, totals, completeness, flags and
      fingerprints are unchanged (golden diffs add only the new fields).
      Added to schema 1 and its JSON Schema while 0.1.0 is unreleased.
- [x] `compare_reports`, its input check and the text and Markdown
      summaries handle the new figures.

### OSS-57: shared timestamp section in frame reports (P-6) — merged in [#63](https://github.com/PederFalkman/opensource/pull/63)

- [x] Owner's choice among three designs: an additive frame-level
      `timestamps` section. Column reports are unchanged and still equal
      `assess_quality` per column (the 0.1.0 promise), so reports do not
      get smaller; they get one place to read the timestamp facts.
- [x] The section is built only when every column reports identical
      timestamp facts, so it is correct by construction; `null` when
      columns take different steps from their metadata.
- [x] JSON Schema, golden frame report (only the new section added) and
      tests updated.

### OSS-58: Parquet input (P-5) — merged in [#64](https://github.com/PederFalkman/opensource/pull/64)

- [x] `energydata-kit report` reads `.parquet`/`.parq`/`.pq` files with
      the new optional extra `[parquet]` (pyarrow, Apache-2.0,
      `>=14.0.1` for CVE-2023-47248); same report as the CSV of the same
      data, byte for byte. Read only; nothing writes Parquet.
- [x] Allowlist, licence table and CI updated. The lowest-dependencies job
      pins pyarrow 14.0.2: current pyarrow needs NumPy 2, and the CLI
      turns an unusable pyarrow into a clear exit 2.

### OSS-59: bug hunt in the newer features — merged in [#65](https://github.com/PederFalkman/opensource/pull/65)

- [x] Probed known outages, the frame `timestamps` section, Markdown
      output and the report JSON Schema; the outage figures matched a
      brute-force reference on 1,500 random series.
- [x] Fixed: a `known_outages` generator reached only the first column of
      `assess_frame`; unclear errors for malformed outages; summary counts
      off above about 10**6 intervals; control characters in column names
      breaking summary lines and Markdown headings.

### OSS-60: release-readiness refresh — merged in [#67](https://github.com/PederFalkman/opensource/pull/67)

- [x] `RELEASE_DECISIONS.md` facts refreshed after P-2 to P-6 and the
      Apache-2.0 licence (#66): what changed since OSS-48, G2 passed,
      commit counts, PyPI names re-checked, required checks for branch
      protection, a note for the IP reviewer on known outages.
- [x] pip-audit now also installs the `[parquet]` extra, so pyarrow is
      audited; the licence checklist has a pyarrow row.
- [x] Moving the `[Unreleased]` changelog entries into the 0.1.0 section
      was left for a changelog-only change: OSS-61.

### OSS-61: changelog fold — merged in [#68](https://github.com/PederFalkman/opensource/pull/68)

- [x] The `[Unreleased]` entries (P-2 to P-6, the licence, Python 3.14,
      Windows and macOS, pre-release fixes) folded into the 0.1.0 notes by
      theme; fixes to unreleased code described as the shipped behaviour.
- [x] The readiness check fails only on the upload guard (G7, decision
      D6); `RELEASE_DECISIONS.md` says so.

### OSS-62: Parquet bug hunt — merged in [#69](https://github.com/PederFalkman/opensource/pull/69)

- [x] Probed the Parquet reader against the CSV of the same data: text,
      timezone-aware (ns, us, non-UTC) and naive timestamps, float32,
      nullable, decimal, categorical, boolean and nested values, `NaT`,
      empty, corrupt and truncated files. All gave the CSV's report or a
      clear exit 2, except the fixed cases below.
- [x] Fixed: a frame written by pandas with its timestamps as the named
      index reported "timestamp column not found"; an empty `.parquet`
      directory crashed with an `IndexError`; pyarrow's errors named a
      `'<Buffer>'` instead of the file; an unnamed timestamp index now
      says what to change.

### OSS-63: decision brief — no repository change

- [x] A one-page brief of the open decisions D1, D2, D4 and D6 for counsel
      and management, shared outside the repository; it summarises
      `RELEASE_DECISIONS.md`, which stays the record.

### OSS-64: Pandera bug hunt — merged in [#70](https://github.com/PederFalkman/opensource/pull/70)

- [x] Compared every Pandera check with `flag_series` on 400 random
      series (no disagreement on time-ordered data) and probed odd inputs
      and options.
- [x] Fixed: with the lowest supported Pandera (0.24) every timestamp
      check in `pa.Index` raised `TypeError`, and the timezone check called
      aware timestamps naive; the lowest-dependencies CI job now pins
      Pandera 0.24. The stale, counter and jump checks compared rows of an
      unsorted index in file order; they now refuse it, as `flag_series`
      does. Invalid bounds and `stale_exclude` are rejected when a check is
      built, not at every validation.
- [x] Fixed in all checks: `stale_exclude` given as a numpy array of two or
      more values crashed; a non-numeric `stale_exclude` went unnoticed on
      empty data; NaN or infinite bounds, `stale_atol`, `stale_exclude` or
      `counter_tolerance` were accepted and made the report invalid JSON.

### OSS-65: options audit — merged in [#71](https://github.com/PederFalkman/opensource/pull/71)

- [x] Probed every option of `assess_quality` (and so `assess_frame`,
      `flag_series`, the CLI and the Pandera schema) with wrong types,
      booleans, text, numpy scalars and arrays, and empty data, and checked
      each report against the JSON Schema.
- [x] Fixed: an unknown `tz` raised a `KeyError` from zoneinfo, so
      `--tz` ended in a traceback with exit status 1 ("issues found");
      booleans as numbers and a non-boolean `cumulative` were recorded
      as-is, making the report fail its JSON Schema; text in numeric
      options failed inside numpy; `bounds` with three values said "too
      many values to unpack". Each now raises `ValueError` or `TypeError`
      naming the option; numpy numbers stay accepted.

### OSS-66: roadmap tidy — merged in [#72](https://github.com/PederFalkman/opensource/pull/72)

- [x] Open decisions listed as D1 to D6, with D3 (licence) done; a
      one-table summary of the pre-release hardening for the release
      reviewers. No code changes.

### OSS-67: fresh-eyes review — merged in [#73](https://github.com/PederFalkman/opensource/pull/73)

- [x] A high-effort review read every module end to end; all nine
      findings were reproduced before fixing.
- [x] Fixed: date-only timestamps read as UTC (the "-02" of
      "2024-01-02" taken as an offset); `local_days` ignoring `origin=`;
      `compare_reports` crashing on `"truncated": null`; `stale_exclude`
      generators used up or recorded as `[]`; `stale_exclude` with
      `stale_atol` flagging every other row of a near-zero run; CLI
      metadata options silently ignored without `--unit`; a report written
      before a `--flags-csv` error.
- [x] Open for the owner: whether a calendar resolution in metadata (for
      example `"D"` with `timezone="Europe/Stockholm"`) should use the
      metadata time zone without `tz=`. Decided yes; done in OSS-68.

### OSS-68: calendar resolutions in metadata — this change

- [x] A calendar resolution taken from metadata (`"D"`, `"W-MON"`, `"MS"`)
      is a local-calendar step in `metadata.timezone` when no `tz=` is
      given: complete daily data across a DST change read 75 % before, and
      `"MS"` was refused. `"D"` in UTC, fixed resolutions and an explicit
      `freq=` are unchanged. The report, frame reports, the Pandera schema
      and both `--flags-csv` paths use the same rule.

## Explicitly not planned

Forecasting, grid/power-flow calculations, dynamic ratings, connection
planning, economic optimization, RODOT-related algorithms, market data
download. See `IP_BOUNDARY.md`.

## New packages

No new packages until explicitly authorized. Any proposal needs a scope
statement, an IP-boundary review and an entry in the existing-tools audit.
