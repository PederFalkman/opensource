# Roadmap

Only `energydata-kit` is authorized. Every item needs agreement before work
starts, and each must pass the scope test in `docs/governance/IP_BOUNDARY.md`.
Merged items stay listed here as a record of what was agreed.

## Open decisions (owners required)

Questions and evidence for each: `docs/governance/RELEASE_DECISIONS.md`,
section "0.7.0". 0.1.0 (2026-10-19), 0.2.0 (2026-10-20), 0.3.0 to 0.5.0
(all 2026-10-21) and 0.6.0 (2026-10-22) were released as GitHub releases
only; their records are kept there. Engineering for 0.7.0 is complete
(OSS-161 and OSS-162, P-26 and P-27), and the owner recorded the answers
below on 2026-10-22; 0.7.0 was released the same day (OSS-164, #136). No
0.8.0 work is approved yet; the remaining candidates (P-28, and P-12,
P-13, P-18, P-20 and P-22 carried over) are under "Proposed" below
(OSS-160) and not approved.

- [x] **G1 for 0.7.0.** Counsel confirmed that the code added since 0.6.0
      (`ba19231`) is covered (recorded 2026-10-22).
- [x] **G3 for 0.7.0.** The technical lead signed off the IP-boundary review
      of the diff from 0.6.0 (recorded 2026-10-22).
- [x] **G4 for 0.7.0.** No dependency changed; the 0.6.0 position stands
      (recorded 2026-10-22).
- [x] **D6 for 0.7.0 (G7).** GitHub release only, like 0.6.0 (recorded
      2026-10-22).

Recorded for 0.6.0:

- [x] **G1 for 0.6.0.** Counsel confirmed that the code added since 0.5.0
      (`34cf9c7`) is covered (recorded 2026-10-22).
- [x] **G3 for 0.6.0.** The technical lead signed off the IP-boundary review
      of the diff from 0.5.0 (recorded 2026-10-22).
- [x] **G4 for 0.6.0.** No dependency changed; the 0.5.0 position stands
      (recorded 2026-10-22).
- [x] **D6 for 0.6.0 (G7).** GitHub release only, like 0.5.0 (recorded
      2026-10-22).

Recorded for 0.5.0:

- [x] **G1 for 0.5.0.** Counsel confirmed that the code added since 0.4.0
      (`6cc79fd`) is covered (recorded 2026-10-21).
- [x] **G3 for 0.5.0.** The technical lead signed off the IP-boundary review
      of the diff from 0.4.0 (recorded 2026-10-21).
- [x] **G4 for 0.5.0.** No dependency changed; the 0.4.0 position stands
      (recorded 2026-10-21).
- [x] **D6 for 0.5.0 (G7).** GitHub release only, like 0.4.0 (recorded
      2026-10-21).

Recorded for 0.4.0:

- [x] **G1 for 0.4.0.** Counsel confirmed that the code added since 0.3.0
      (`afa6974`) is covered (recorded 2026-10-21).
- [x] **G3 for 0.4.0.** The technical lead signed off the IP-boundary review
      of the diff from 0.3.0 (recorded 2026-10-21).
- [x] **G4 for 0.4.0.** No dependency changed; the 0.3.0 position stands
      (recorded 2026-10-21).
- [x] **D6 for 0.4.0 (G7).** GitHub release only, like 0.3.0 (recorded
      2026-10-21).

Recorded for 0.3.0:

- [x] **G1 for 0.3.0.** Counsel confirmed that the code added since 0.2.0
      (`344c862`) is covered (recorded 2026-10-21).
- [x] **G3 for 0.3.0.** The technical lead signed off the IP-boundary review
      of the diff from 0.2.0 (recorded 2026-10-21).
- [x] **G4 for 0.3.0.** No dependency changed; the 0.2.0 position stands
      (recorded 2026-10-21).
- [x] **D6 for 0.3.0 (G7).** GitHub release only, like 0.2.0 (recorded
      2026-10-21).

Recorded for 0.2.0:

- [x] **G1 for 0.2.0.** Counsel confirmed in writing that the code added
      since 0.1.0 is covered (recorded 2026-10-20).
- [x] **G3 for 0.2.0.** The technical lead signed off the IP-boundary review
      of the diff from 0.1.0 (`827a2df`) (recorded 2026-10-20).
- [x] **G4 for 0.2.0.** No dependency changed; the 0.1.0 position stands
      (recorded 2026-10-20).
- [x] **D6 for 0.2.0 (G7).** GitHub release only, like 0.1.0 (recorded
      2026-10-20).
- [ ] **D5 Branch protection on `main`** (not a gate): require CI and
      code-owner review.
- [x] **D3 Licence (G2).** Apache-2.0, granted 2026-10-18 (#66).
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

### P-26 to P-28: candidates for 0.7.0 (OSS-160)

*Prepared by the assistant in OSS-160 for the owner to approve or reject one
by one. Nothing here is authorized; none of it starts without approval.*
Each item is generic data-quality or command-line tooling as defined in
`IP_BOUNDARY.md` ("What *is* in scope"), ships no domain thresholds and
touches nothing on the out-of-scope list. P-22, P-13, P-18, P-12 and P-20
from earlier rounds were not approved and stay open; they are ranked again
below. Each new motivating behaviour was checked on 2026-10-22 on `main`
at `17314b6` (0.7.0.dev0).

| ID | Candidate | Why | Effort | Risk and cost |
|---|---|---|---|---|
| P-26 | *Approved by the owner on 2026-10-22; done in OSS-161.* **Which file each flagged row came from.** When `report` reads several files (P-25), `--flags-csv` gains a `source` column with the input file name of each row. With one file the CSV is unchanged. | P-25 was motivated by users joining monthly files by hand and losing which file a row came from, but it loses that too: checked with `report jan.csv feb.csv --flags-csv f.csv`, the file has only `timestamp,kwh,quality_flag`. A flagged row then has to be searched for in every month's file. | S | No report-format change: the JSON report is unchanged; only the flags CSV of a several-file run gets a column, documented in the changelog. `--gaps-csv` stays as it is, because a gap can span two files. Names are written as given on the command line. |
| P-27 | *Approved by the owner on 2026-10-22; done in OSS-162.* **Use the inferred step on request** (`--freq inferred`). The report already records `inferred_resolution` (the most common step between timestamps); this option makes it the expected step, so gaps and completeness are checked. The text and Markdown summaries also name the inferred step when no step is given. | Checked: without `--freq`, the summary says "completeness: not checked (no step: pass --freq …)" and does not show the step the JSON already infers (`inferred_resolution: P0DT1H0M0S` for hourly data); `--freq inferred` is refused. A first look at an unknown file takes two runs. | S | No format change: the inferred step is recorded under `freq` as an explicit one would be. It stays opt-in: the report's rule that "the step is never guessed silently" holds, and the summary says the step was inferred. Inference picks the most common step, so a file that is mostly gaps or mixed resolutions can give a misleading step; documented. Fixed steps only; `--tz` with `inferred` is refused. |
| P-28 | **Duplicates that disagree.** Count duplicate timestamps whose values differ separately from exact repeats, e.g. `n_conflicting_duplicates` next to `n_duplicate_timestamps`. | Checked: two overlapping files that repeat 02:00 with the same value and two that repeat it with 3 and 9 give identical reports (1 duplicate timestamp, `DUPLICATE_TIMESTAMP` 2). A re-issued, corrected month and a harmless overlap look the same. More likely now that P-25 reads several files. | M | A new report field, so report schema 3 and a `compare_reports` reader for 1, 2 and 3; worth doing only together with P-12 and P-20. Must define "differ" for missing values (NaN against NaN is not a conflict) and keep the `DUPLICATE_TIMESTAMP` flag as it is. |
| P-22 | *Carried over, not approved.* **Known outages from a file** (`--known-outages-csv`). As described for 0.5.0 below. | A long maintenance log makes a long command. | S | No format change. |
| P-13 | *Carried over, not approved.* `origin="epoch"`. | A leading off-grid timestamp shifts the grid. | S | Fits schema 2. |
| P-18 | *Carried over, not approved.* Compare full gap lists from `--gaps-csv`. | Only listed gaps are compared. | S–M | No report change. |
| P-12, P-20 | *Carried over, not approved.* DST policy for calendar grids; single-row spikes. | Known limitations. | S–M, M | Report schema 3; together with P-28 if it is approved. |

Considered and not proposed:
- **Compressed input** (`report data.csv.gz`): already works; checked on
  2026-10-22, pandas reads it by its extension. A line in the README is
  enough and can ride with any change.
- **Sorting files by time:** `report feb.csv jan.csv` already gives the same
  result as `report jan.csv feb.csv`, because timestamps are checked in
  time order.
- **Inferring the step by default:** it would change reports that have no
  step today and break "never guessed silently"; P-27 keeps it opt-in.

**Suggested order if approved:** P-26 first (it completes P-25, and is
small), then P-27, then P-22. P-13 and P-18 as before; P-28 only with P-12
and P-20, as one schema-3 change. Each needs its own approval.

### P-24 and P-25: candidates for 0.6.0 (OSS-154)

*Prepared by the assistant in OSS-154 for the owner to approve or reject one
by one. Nothing here is authorized; none of it starts without approval.*
Each item is generic data-quality or command-line tooling as defined in
`IP_BOUNDARY.md` ("What *is* in scope"), ships no domain thresholds and
touches nothing on the out-of-scope list. P-22, P-13, P-18, P-12 and P-20
from earlier rounds were not approved and stay open; they are ranked again
below.

| ID | Candidate | Why | Effort | Risk and cost |
|---|---|---|---|---|
| P-24 | *Approved by the owner on 2026-10-22, as the default behaviour; done in OSS-155.* **`compare` treats explained gaps like `report` does.** A comparison is "worse" only when unexplained missing intervals rise (outside `--known-outage` periods) or, when both reports record outages, when `completeness_excluding_outages` falls; flagged rows count as before. | Checked on 2026-10-21: one hour missing inside a declared outage makes `report --fail-on-issues` exit 0 (since P-21) but `compare --fail-if-worse` exit 1, calling the data worse. The two commands disagree about the same gap. | S | The comparison's `worse` field keeps its name and type but changes meaning for reports with outages, and `--fail-if-worse` can then exit 0 where it exited 1; documented in the changelog. Reports without outages compare exactly as before. If that is not wanted, the rule can sit behind a `compare --ignore-explained` option instead. |
| P-25 | *Approved by the owner on 2026-10-22; done in OSS-156.* **Several input files in one report** (`report jan.csv feb.csv mar.csv`). The files are read with the same options and stacked in the order given; duplicates across files are detected as within one file. | Meter exports usually come per month; today `report` takes one file (a second is refused as "unrecognized arguments"), so users join files by hand first, which loses which file a row came from. | S–M | No format change: the report covers the combined data, as if it were one file. All files must have the same columns (refused otherwise, exit 2). `--flags-csv` writes one combined file. Reading Parquet and CSV together is out of scope. |
| P-22 | *Carried over, not approved.* **Known outages from a file** (`--known-outages-csv`). As described for 0.5.0 below. | A long maintenance log makes a long command. | S | No format change. |
| P-13 | *Carried over, not approved.* `origin="epoch"`. | A leading off-grid timestamp shifts the grid. | S | Fits schema 2. |
| P-18 | *Carried over, not approved.* Compare full gap lists from `--gaps-csv`. | Only listed gaps are compared. | S–M | No report change. |
| P-12, P-20 | *Carried over, not approved.* DST policy for calendar grids; single-row spikes. | Known limitations. | S–M, M | Report schema 3; only together. |

Considered and not proposed:
- **A `--fail-on`-style choice for `compare`:** `--fail-if-worse` with P-24
  covers the common case; a per-issue choice can follow if asked for.
- **Globs or directories as input** (`report data/*.csv`): the shell already
  expands globs into P-25's list of files.

**Suggested order if approved:** P-24 first (it makes `compare` agree with
`report`, and is small), then P-25, then P-22. P-13 and P-18 as before;
P-12 with P-20 only as a schema-3 change. Each needs its own approval.

### P-21 to P-23: candidates for 0.5.0 (OSS-148)

*Prepared by the assistant in OSS-148 for the owner to approve or reject one
by one. Nothing here is authorized; none of it starts without approval.*
Each item is generic data-quality or command-line tooling as defined in
`IP_BOUNDARY.md` ("What *is* in scope"), ships no domain thresholds and
touches nothing on the out-of-scope list. P-12, P-13, P-18 and P-20 from
earlier rounds were not approved and stay open; they are ranked again below.
All three new items concern the command line's use in pipelines, and none
changes the report format.

| ID | Candidate | Why | Effort | Risk and cost |
|---|---|---|---|---|
| P-21 | *Approved by the owner on 2026-10-21, as the default behaviour; done in OSS-149.* **Explained gaps do not fail `--fail-on-issues`.** A missing interval inside a `--known-outage` period no longer counts as an issue for the exit status; unexplained gaps and flagged rows still do. | Checked on 2026-10-21: a report whose only gap lies wholly inside `--known-outage` has `n_missing_explained` equal to `n_missing_intervals` and `completeness_excluding_outages` 1.0, yet `--fail-on-issues` exits 1. A pipeline that declares planned maintenance still fails on it. | S | No format change, but the exit status changes for callers that combine both options (1 → 0 when every gap is explained); documented in the changelog. If that is not wanted, the same behaviour can sit behind an opt-in flag instead. |
| P-22 | **Known outages from a file** (`report --known-outages-csv FILE` with `start,end` columns). | Today each period is a repeated `--known-outage START END`; a maintenance log with dozens of periods makes a long, fragile command. A file can also be a `--gaps-csv` from an earlier run, to accept the gaps found once as known. | S | No format change: the report records the periods as it does now. Must define how a `column` column (as `--gaps-csv` writes) applies a period to one column only in multi-column reports, and refuse malformed rows (exit 2). |
| P-23 | *Approved by the owner on 2026-10-21; done in OSS-150.* **Choose what fails the exit status** (`report --fail-on FLAG`, repeatable, e.g. `--fail-on NON_FINITE --fail-on gaps`). | `--fail-on-issues` is all or nothing: any flag or any missing interval. A pipeline that tolerates stale values but not gaps cannot express that and ends up ignoring the exit status. | S | No format change; `--fail-on-issues` keeps its meaning. The accepted names are the `QualityFlag` names plus `gaps` (and `unexplained-gaps` if P-21 is approved); unknown names are refused. Designing it together with P-21 keeps the two consistent. |
| P-13 | *Carried over, not approved.* **Grid anchored at the step boundary** (`origin="epoch"`). As described for 0.3.0 below. | Known limitation: a leading off-grid timestamp shifts the grid. | S | Fits schema 2. |
| P-18 | *Carried over, not approved.* **Compare full gap lists** from `--gaps-csv` files. As described for 0.4.0 below. | Known limitation: only listed gaps are compared. | S–M | No report change. |
| P-12, P-20 | *Carried over, not approved.* **DST policy for calendar grids** and **single-row spikes.** As described below. | Known limitations. | S–M, M | Both need report schema 3; only worth doing together. |

Considered and not proposed:
- **Reading Excel or other formats:** a new dependency for a one-line
  pandas conversion the caller can do.
- **Per-flag exit codes** (different numbers per issue): harder to use in
  shells than P-23's yes/no with a chosen set.

**Suggested order if approved:** P-21 first (it fixes surprising
behaviour), then P-23 designed with it, then P-22. P-13 and P-18 as
before; P-12 with P-20 only as a schema-3 change. Each needs its own
approval.

### P-17 to P-20: candidates for 0.4.0 (OSS-142)

*Prepared by the assistant in OSS-142 for the owner to approve or reject one
by one. Nothing here is authorized; none of it starts without approval.*
Each item is generic data-quality or command-line tooling as defined in
`IP_BOUNDARY.md` ("What *is* in scope"), ships no domain thresholds and
touches nothing on the out-of-scope list. P-12 and P-13 from 0.3.0 were not
approved and stay open; they are ranked again below with the new items.

**The constraint that shapes them:** report schema 2 has closed
`parameters` and `flag_counts` objects (`additionalProperties: false` in
`report_schema.json`), so any new recorded option or flag needs **report
schema 3**, with `compare_reports` reading 1, 2 and 3. P-12 and P-20 need
it; P-13, P-17, P-18 and P-19 do not. If both P-12 and P-20 are approved,
they should ship as one schema-3 change.

| ID | Candidate | Why | Effort | Risk and cost |
|---|---|---|---|---|
| P-17 | *Approved by the owner on 2026-10-21; done in OSS-143.* **`--unit COLUMN=UNIT` names the value columns.** When `--value-col` is not given, the columns named by `--unit COLUMN=UNIT` become the assessed columns, as `--schema` columns already do. | Found while writing the 0.3.0 guide example (OSS-139): naming each column twice (`--value-col kwh --unit kwh=kWh`) is easy to get wrong, and the single-column form needs no `--value-col` when the file has one value column. Today the command stops with "pass --value-col". | S | No format change. Must keep an explicit `--value-col` authoritative (then `--unit` may name a subset), and keep the order of `--unit` options as the column order so reports stay deterministic. |
| P-18 | **Compare full gap lists.** `compare before.json after.json --gaps before.csv after.csv` reads the `--gaps-csv` files and compares every gap, not only the first `max_listed`. | Known limitation: "Only listed gaps are compared"; long outage histories set `lists_truncated`, and the comparison then misses gaps. P-14 made the full list available but nothing reads it. | S–M | No report change. The comparison output keeps its fields; `lists_truncated` becomes `false` when full lists are read, which consumers must be told. Must refuse CSVs that do not match their report (columns, gap counts). |
| P-19 | *Approved by the owner on 2026-10-21; done in OSS-144.* **Fast parsing of the other offset forms.** Extend the OSS-136 fast path to `+0200` and `+02` offsets. | Known limitation and `PERFORMANCE.md`: measured on 2026-10-21, 350,000 strings take 1.6–1.7 s in these forms against 0.5 s for `+02:00`. | S | No format change. Same rule as P-16: results and errors must match the general parser on the lowest and current pandas, checked by a property test, or the proposal is dropped. |
| P-20 | **Single-row spikes.** An opt-in `spike_max_delta` flags a row that differs from both neighbours by more than the limit, in opposite directions, with a new `SPIKE` flag (bit 2048), so one outlier is flagged once. | Known limitation: the jump check flags the row where a change lands, so a single outlier flags itself and the row after it; callers cannot tell a spike from a step. | M | New flag bit and recorded option, so schema 3 (pair with P-12). The caller picks the limit in the data's unit; no limit shipped. Must define behaviour at gaps (`max_gap`), missing values and the first and last rows. |
| P-12 | *Carried over from 0.3.0, not approved.* **DST policy for calendar grids.** As described for 0.3.0 below. | Known limitation: a daily grid at 02:30 in Europe/Stockholm raises. | S–M | Schema 3 (pair with P-20). |
| P-13 | *Carried over from 0.3.0, not approved.* **Grid anchored at the step boundary** (`origin="epoch"`). As described for 0.3.0 below. | Known limitation: a leading off-grid timestamp shifts the grid. | S | Fits schema 2; `origin` may then hold a keyword instead of a timestamp, documented as such. |

Considered and not proposed:
- **`"D"` in metadata as a local day when a timezone is set:** it would
  silently change the result of existing metadata; `--tz` already covers it.
- **Per-step groups in the frame `timestamps` section:** a schema change for
  the rare case of columns with different steps.
- **Flags from Pandera:** Pandera's model is pass or fail; `flag_series`
  already gives the flags.
- **Automatic or statistical limits, gap filling, resampling, pint-pandas:**
  out of scope or deferred, as before.

**Suggested order if approved:** P-17 and P-19 first (small, no format
change), then P-13, then P-18. P-12 and P-20 only if a schema-3 change is
wanted, and then together. Each needs its own approval.

### P-12 to P-16: candidates for 0.3.0 (OSS-135)

*Prepared by the assistant in OSS-135 for the owner to approve or reject one
by one. Nothing here is authorized; none of it starts without approval.*
Each item is generic data-quality or command-line tooling as defined in
`IP_BOUNDARY.md` ("What *is* in scope"), ships no domain thresholds and
touches nothing on the out-of-scope list. Each comes from the package
README's "Known limitations".

**The constraint that shapes them:** report schema 2 is fixed since 0.2.0
and its `parameters` object allows no extra fields. Only P-12 adds a
recorded option, so only P-12 would need **report schema 3**; P-13 to P-16
change no format. If P-12 is approved, any other option a report must
record should join the same schema-3 change.

| ID | Candidate | Why | Effort | Risk and cost |
|---|---|---|---|---|
| P-12 | **DST policy for calendar grids.** An opt-in `nonexistent`/`ambiguous` choice for calendar grids (`tz=`) whose wall-clock time falls in a skipped or repeated DST hour, with the same choices `normalize_timestamps` already offers, instead of raising. | Known limitation: a daily grid at 02:30 in Europe/Stockholm raises because pandas cannot place it, so such series cannot be assessed at all. | S–M | Recorded in reports, so report schema 3 and a `compare_reports` reader for 1, 2 and 3. Must define which grid point a skipped hour maps to; defaults stay "raise". |
| P-13 | **Grid anchored at the step boundary.** `origin="epoch"` (or similar) places the grid on whole steps since the Unix epoch, so a leading off-grid timestamp no longer shifts the whole grid. | Known limitation: without `origin`, the grid starts at the first timestamp, and one early stray row moves every grid point. | S | Fits schema 2 (`origin` is a string), but a consumer that expects an ISO timestamp there sees a keyword; documented as such. Fixed steps only; calendar steps already align to the calendar. |
| P-14 | *Approved by the owner on 2026-10-20; done in OSS-137.* **Full gap list as a file** (`report --gaps-csv`). Writes every gap, not only the first `max_listed`, next to the JSON report. | Known limitation: comparisons see only listed gaps; long outage histories hit `max_listed` and `lists_truncated`. | S | No format change: the JSON is untouched and the CSV follows the input's delimiter, like `--flags-csv`. |
| P-15 | *Approved by the owner on 2026-10-20; done in OSS-138.* **Units for several columns on the command line** (`--unit COLUMN=UNIT`, repeatable), without writing a Table Schema. | Known limitation: `--unit` works with one `--value-col` only; several columns need `--schema`. | S | No format change. Must keep the single-column `--unit kWh` form and refuse a unit for a column that is not assessed. |
| P-16 | *Approved by the owner on 2026-10-20; done in OSS-136.* **Faster parsing of timestamps whose UTC offset changes across DST.** Use pandas' ISO 8601 fast path where the input allows it, keeping the current result. | Known limitation and `PERFORMANCE.md`: about 2 s per 350,000 rows, all of it in pandas' general parser. | S | No format change. Results must stay byte-identical (the golden tests pin them) on the lowest and current pandas; if the fast path differs anywhere, the proposal is dropped. |

Considered and not proposed:
- **Comparing the frame-level `timestamps` section:** it repeats facts
  already compared per column; little gain for a comparison-format change.
- **Fractional expected counts on 30-minute DST days:** affects very few
  zones (e.g. Lord Howe Island); the current floor is documented.
- **pint-pandas support:** still deferred (process-wide unit registry).
- **Automatic or statistical limits, gap filling, resampling:** out of
  scope, as for P-7 to P-11.

**Suggested order if approved:** P-16, P-14 and P-15 first (approved
2026-10-20) (no format
change, each small). P-13 next. P-12 only if wanted, as the single schema-3
change. Each needs its own approval.

### P-7 to P-11: candidates after 0.1.0 (OSS-100)

*Prepared by the assistant in OSS-100 for the owner to approve or reject one
by one. Nothing here is authorized; none of it starts without approval.*
Each item is generic data-quality or release tooling as defined in
`IP_BOUNDARY.md` ("What *is* in scope"), ships no domain thresholds (every
limit stays caller-supplied) and touches nothing on the out-of-scope list.
Most come from the package README's "Known limitations".

**The constraint that shapes all of them:** report schema 1 is fixed since
0.1.0, and its `parameters` object allows no extra fields. Any new check
option that a report records (P-7, P-8, P-9) therefore needs **report
schema 2**, which `compare_reports` and `report_schema.json` must support
alongside schema 1. If more than one is approved, they should ship together
as one schema-2 change, not one schema bump each. Options used only by
`flag_series` and the Pandera checks, and not recorded in reports, need no
schema change.

| ID | Candidate | Why | Effort | Risk and cost |
|---|---|---|---|---|
| P-7 | *Approved by the owner on 2026-10-20, as part of report schema 2 (design in `SCHEMA_2.md`, OSS-103); implemented in OSS-106.* **Rate-based jump limit.** An opt-in `jump_max_rate` (change per unit of time, e.g. kW per hour) next to the absolute `jump_max_delta`, dividing each change by the time since the previous finite value. | Known limitation: the jump check uses an absolute limit per row, so a gap followed by a normal ramp looks like a jump, and the same limit can't fit two resolutions. | S | Schema 2 if recorded in reports. The caller picks the rate; units stay the caller's (no Pint conversion of limits). Must define behaviour across duplicates and off-grid rows. |
| P-8 | *Approved by the owner on 2026-10-20, as part of report schema 2 (design in `SCHEMA_2.md`, OSS-103); implemented in OSS-105.* **Runs and comparisons that stop at gaps.** An opt-in `max_gap` for the stale, counter and jump checks: consecutive rows further apart than this are not compared, and a stale run does not continue across the gap. | Known limitation: these checks compare consecutive rows and ignore time gaps, so a flat line before and after an outage counts as one run and a jump across a long gap is flagged. | S–M | Schema 2 if recorded. Default off, so 0.1.0 results stay identical. Interacts with P-7; worth designing together. |
| P-9 | *Approved by the owner on 2026-10-20, as part of report schema 2 (design in `SCHEMA_2.md`, OSS-103); implemented in OSS-107.* **Counter rollover (wrap-around) separated from resets.** An opt-in `counter_rollover` (the register's modulus, e.g. 10**6 kWh, supplied by the caller): a drop consistent with wrapping past the modulus gets a new `COUNTER_ROLLOVER` flag (bit 1024) instead of `COUNTER_DECREASE`. | Known limitation: a register reset and a rollover both appear as `COUNTER_DECREASE`; a caller who knows the register size can tell them apart. | S | Adds a flag bit (public contract: never renumbered) and a flag count, so schema 2. No modulus is shipped or guessed. |
| P-10 | *Approved by the owner on 2026-10-20, as part of report schema 2 (design in `SCHEMA_2.md`, OSS-103); implemented in OSS-108.* **Overlap-aware gap comparison.** `compare_reports` matches gaps by overlap, so a gap that shrank or grew shows as *changed* (with before/after bounds) instead of one resolved and one new gap. | Known limitation in the README; the before/after view of a fix is the main use of `compare`. | M | Changes the comparison output (a new `changed` list): comparisons are schema-versioned with reports, so this rides on schema 2 too. Only listed gaps can be compared, as today (`max_listed`). |
| P-11 | *Approved by the owner on 2026-10-19; done in OSS-101, as a **draft** release the owner publishes.* **Attach the built files to the GitHub release.** The *Release build* workflow, on an `energydata-kit-v*` tag, also creates (or updates) the GitHub release and uploads the wheel, sdist and their SHA-256 sums. Still never uploads to an index. | D6 chose GitHub releases only; today the owner attaches the files by hand after the workflow builds them, which is error-prone and leaves the attested files and the attached files separate. | S | Needs `contents: write` for that job only, a pinned action or `gh`, and a test in the dry run. Gated by the strict readiness check (D6 line for that version) already in the workflow. No package change. |

Considered and not proposed:
- **Automatic or statistical limits** (outlier scores, learned thresholds):
  they edge towards forecasting or anomaly models and would ship implied
  domain limits.
- **Gap filling or resampling:** changes data, against the non-destructive
  rule.
- **Publishing to PyPI:** a D6 decision, not engineering.
- **A second package:** not authorized.

**Suggested order if approved:** P-11 first (no schema change, removes a
manual release step). Then P-8 with P-7, and P-9 if wanted, as one
schema-2 change together with P-10, because they all change what reports
and comparisons contain. Each needs its own approval.

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
      metadata time zone without `tz=`. Decided in OSS-68, narrowed after a
      second review to steps with no fixed length (see below).

### OSS-68: calendar resolutions in metadata — merged in [#74](https://github.com/PederFalkman/opensource/pull/74)

- [x] A metadata resolution with no fixed length (`"MS"`, `"W-MON"`) is a
      local-calendar step in `metadata.timezone` when no `tz=` is given;
      before, it was refused. The report, frame reports, the Pandera schema
      and both `--flags-csv` paths use the same rule.
- [x] `"D"` stays the 24-hour step, as before, by the owner's decision after
      a second review: as a local-calendar step it crashed in zones where
      DST skips midnight (São Paulo, Santiago, Cairo) and moved daily data
      stamped at UTC midnight off the grid. Local days need `tz=` (`--tz`),
      now documented.

### OSS-69: release facts refreshed — merged in [#75](https://github.com/PederFalkman/opensource/pull/75)

- [x] `RELEASE_DECISIONS.md`: commit counts, the hardening since OSS-60 and
      the Pandera 0.24 pin; the shared decision brief republished to match.

### OSS-70: release dry run — branch only, not for merge before D1, D2, D4, D6

- [x] Branch `claude/oss-70-release-dry-run` holds the release edits
      (upload guard removed, changelog dated, readiness test inverted);
      `check_release_readiness --strict` and `release_dry_run --build` pass.
      A draft release-PR description was prepared from the checklist. It
      is rebased and opened only after the human gates are signed off.

### OSS-71: second fresh-eyes review — fixes in #74 and OSS-72

- [x] A second whole-package review on the OSS-68 code: its three
      regressions (DST-skipped midnights, UTC-stamped daily data, UTC
      aliases) were fixed in #74 by keeping `"D"` a 24-hour step; two CLI
      edge cases went to OSS-72; code-quality notes left as possible
      follow-ups.

### OSS-72: `--flags-csv` grid across `--schema` columns — merged in [#76](https://github.com/PederFalkman/opensource/pull/76)

- [x] Equal fixed steps spelled differently (`"60min"`, `"1h"`) are one
      grid, not "different resolutions".
- [x] A column without a resolution, next to columns with one, is refused
      with exit 2 before anything is written, instead of being flagged on
      another column's grid while its report has none.

### OSS-73: one rule for the grid taken from metadata — merged in [#77](https://github.com/PederFalkman/opensource/pull/77)

- [x] From the second review's code-quality notes, with no behaviour
      change: the helper that picks the grid from metadata lives in
      `metadata.py`, and fixed vs calendar is decided by `to_step()`, the
      rule that validates resolutions, instead of a second check with a
      pandas 2/3 special case. A test pins the classification on both.

### OSS-74: build the grid once in `assess_quality` — merged in [#78](https://github.com/PederFalkman/opensource/pull/78)

- [x] The last note from the second review: gaps, completeness and
      known outages share one expected grid and one presence test
      instead of building them two or three times. Reports are
      byte-identical; `assess_quality` is 10–40 % faster on long series.
      The measurements are in `PERFORMANCE.md`.

### OSS-75: docs accuracy audit — merged in [#79](https://github.com/PederFalkman/opensource/pull/79)

- [x] For release gate G6, README, the guide, OVERVIEW, CONTRIBUTING,
      API_REVIEW, the docstrings and `--help` were checked against the code
      after OSS-59 to OSS-74. Every suspected inaccuracy was confirmed by
      running it before it was fixed.
- [x] Fixed: the package README said no licence had been granted, and
      the README and OVERVIEW said calendar steps were never taken from
      metadata (true before OSS-68). CONTRIBUTING told contributors to
      write changelog entries under `[Unreleased]`, against the practice
      since OSS-61. The `report` and `compare` help said JSON and CSV
      only. Four docstrings were out of date (`local_days`, empty
      completeness, `resolution_timedelta`, the resolution field), and
      the text summary blamed a missing `--freq` for every empty
      completeness.
- [x] The guide gains two executed examples: a monthly metadata
      resolution laid out in its time zone, and Parquet input.

### OSS-76: release branch refreshed — branch only; merged by mistake in #82, reverted in OSS-81

- [x] `claude/oss-76-release-refresh`: the OSS-70 release edits with
      `main` merged in (through #79; through #81 since OSS-80). The
      strict readiness check, the wheel and sdist build with `twine
      check`, every repository check and the lowest-dependency tests
      pass. The draft release-PR description has the new digests. Since
      OSS-81 the release PR is a fresh branch from the final `main` (see
      below), with the date set.

### OSS-77: decision brief refreshed — merged in [#80](https://github.com/PederFalkman/opensource/pull/80)

- [x] `RELEASE_DECISIONS.md`: what changed since OSS-68, G6 audited in
      OSS-75, the rehearsed release branch, commit counts at #79; the
      shared decision brief republished to match.

### OSS-78: review of the code since OSS-71 — merged in [#81](https://github.com/PederFalkman/opensource/pull/81)

- [x] A focused review of the code merged after the second review (#76
      to #79): the `--flags-csv` grid check, the grid helper in
      `metadata.py`, the grid built once and the new summary messages.
      300 random reports were byte-identical before and after #78 on
      pandas 2.1 and 3.
- [x] Fixed: equal calendar steps spelled differently (`"MS"` and
      `"1MS"`, `"W"` and `"W-SUN"`) were refused as "different
      resolutions" by `--flags-csv`, as `"60min"` and `"1h"` were before
      OSS-72. Two docstrings corrected (`"D"` is a fixed step; no
      `local_days` for an empty series).

### OSS-79: pause until the release decisions

- [x] No new work by the owner's choice: the package is reviewed, the
      docs audited and the release rehearsed; the release waits on D1,
      D2, D4 and D6.

### OSS-80: release branch brought up to date — merged in [#83](https://github.com/PederFalkman/opensource/pull/83)

- [x] `main` (through #81) merged into `claude/oss-76-release-refresh`;
      the strict readiness check, the build with `twine check`, every
      repository check and 403 tests on the lowest supported versions
      pass. The draft release-PR description has the new digests.

### OSS-81: unintended release merge reverted — merged in [#84](https://github.com/PederFalkman/opensource/pull/84)

- [x] #82 merged the release rehearsal branch into `main` before the
      release decisions; by the owner's decision it is reverted here.
      The upload guard, the readiness test and the placeholder
      changelog date are back as they were after #81; nothing was
      tagged or published.
- [x] Because a merge was reverted, the release PR reverts this revert
      (or re-applies the three release edits) instead of merging
      `claude/oss-76-release-refresh` again, which git would treat as
      already merged.

### OSS-82: pause until the release decisions

- [x] No new work by the owner's choice, after #84 restored the guard.

### OSS-83: upload guard tied to the decision record — merged in [#85](https://github.com/PederFalkman/opensource/pull/85)

- [x] `check_release_readiness.py --guard`, run in CI and by
      `check_all.py` on every change: removing `Private :: Do Not Upload`
      fails unless `RELEASE_DECISIONS.md` has the owner's line
      `**D6 approved:** YYYY-MM-DD ...`. #82 passed CI because it removed
      the guard and inverted its test together; that no longer works.
- [x] The strict readiness check (and so the tag build) also requires
      the D6 line; the release dry run adds a placeholder one to its copy,
      as it does for the licence. The checklist, gates and D6 say the
      release PR carries the approval line with the guard removal.

### OSS-84: pause until the release decisions

- [x] No new work by the owner's choice while #85 was in review.

### OSS-85: decision brief refreshed — merged in [#86](https://github.com/PederFalkman/opensource/pull/86)

- [x] `RELEASE_DECISIONS.md`: what changed since OSS-77 (the #81 fix,
      the #82 merge and its revert in #84, the D6-tied guard of #85),
      the readiness check now failing on the guard and the D6 line,
      the release PR as a revert of the revert, and commit counts at
      #85. The shared decision brief republished to match.

### OSS-86 to OSS-89: pause until the release decisions

- [x] No new work by the owner's choice.

### OSS-90: release energydata-kit 0.1.0 — merged in [#87](https://github.com/PederFalkman/opensource/pull/87)

- [x] Decisions recorded by the owner on 2026-10-19: D1 make the
      repository private for now; D2 ownership confirmed in writing by
      counsel; D4 IP review signed off by the technical lead; D6 GitHub
      release only, no package index (`**D6 approved:**` line).
- [x] Reverts the OSS-81 revert, bringing back the rehearsed release
      edits: upload guard removed, changelog dated 2026-10-19, the
      readiness test expecting a release-ready package. Status lines in
      the READMEs, SECURITY and CONTRIBUTING updated.
- [ ] After merge, by the owner: tag `energydata-kit-v0.1.0` on the merge
      commit; the *Release build* workflow builds and attests the files,
      which are attached to a GitHub release. Nothing is uploaded.

### OSS-91 to OSS-96: pause until #87 merged

- [x] No new work while the release PR was open.

### OSS-97: open 0.2.0 development — merged in [#88](https://github.com/PederFalkman/opensource/pull/88)

- [x] `__version__` is `0.2.0.dev0`; `[Unreleased]` takes the changes
      after 0.1.0; CONTRIBUTING says so. The 0.1.0 section stays as
      released.
- [x] The `Private :: Do Not Upload` guard is back: D6 approved 0.1.0 as a
      GitHub release only, so no index upload is approved for 0.2.0. The
      readiness test again expects a package that is not release-ready.
- [x] The next release needs a new D6 approval; since OSS-98 the guard
      check enforces it, as the 0.1.0 line names its version.

### OSS-98: D6 approval tied to the version — merged in [#89](https://github.com/PederFalkman/opensource/pull/89)

- [x] The guard check (and the strict readiness check) accept only a
      `**D6 approved:** YYYY-MM-DD` line that names the package and the
      version being released, as whole words: the 0.1.0 approval no longer
      unlocks the guard for 0.2.0, and a `.devN` version cannot drop it.
      The 0.1.0 record already names its version, so the release commit
      `827a2df` still passes; `b9444a6` (#82) still fails.
- [x] The release dry run writes its placeholder line with the version;
      D6, the checklist and the gates show the format.

### OSS-99: pause while #88 and #89 were open

- [x] No new work by the owner's choice.

### OSS-100: post-0.1.0 proposals — merged in [#90](https://github.com/PederFalkman/opensource/pull/90)

- [x] P-7 to P-11 drafted above for the owner to approve or reject one by
      one; nothing implemented. P-11 approved by the owner on 2026-10-19;
      P-7 to P-10 not decided. The schema-2 constraint is spelled out,
      since four of the five change what reports record.

### OSS-101: release files attached to a draft GitHub release (P-11) — merged in [#93](https://github.com/PederFalkman/opensource/pull/93)

- [x] A new `github-release` job in the *Release build* workflow, on an
      `energydata-kit-v*` tag and after the build (strict readiness check,
      including the D6 line for that version) and the attestation: it
      creates a **draft** GitHub release with the wheel, sdist and
      `SHA256SUMS`, or replaces the files of an existing draft. It refuses
      to touch a release that is already published, and never uploads to
      a package index. Only this job has `contents: write`; it uses the
      runner's `gh`, so no new action to pin.
- [x] `tools/tests/test_release_workflow.py` runs the step's script with a
      fake `gh` for all three paths, and checks the permissions and that
      nothing names an index upload.
- [x] Release checklist, gates and overview updated. A workflow runs from
      the tagged commit, so this applies from the next release on; 0.1.0
      (`827a2df`) predates it, and its files are attached by hand.

### OSS-102: pause

- [x] No new work by the owner's choice while #93 was open.

### OSS-103: report schema 2 design — merged in [#94](https://github.com/PederFalkman/opensource/pull/94)

- [x] P-7 to P-10 approved by the owner on 2026-10-20. `SCHEMA_2.md`
      fixes what they change in the format before any code: new
      parameters (`max_gap`, `jump_max_rate`, `counter_rollover`), the
      `COUNTER_ROLLOVER` flag (bit 1024), `changed` gaps in comparisons,
      `compare_reports` reading schemas 1 and 2, and a five-step plan for
      0.2.0. Three open questions for the owner. Docs only.

### OSS-104: report schema 2, step 1 (scaffolding) — merged in [#95](https://github.com/PederFalkman/opensource/pull/95)

- [x] The owner's answers to the design's three questions recorded in
      `SCHEMA_2.md`: `(delta, period)` rates, the `m / 2` rollover rule,
      schema 2 only.
- [x] Reports, frame reports and comparisons write `"schema_version": "2"`
      with the new fields, all off: parameters `max_gap`, `jump_max_rate`,
      `counter_rollover` (`null`), flag count `COUNTER_ROLLOVER` (0, new
      `QualityFlag` bit 1024, reserved), comparison `gaps.changed` (empty).
      No check behaves differently yet.
- [x] `report_schema.json` validates schemas 1 and 2; the schema-1
      definitions are unchanged byte for byte. `compare_reports` reads
      both and no longer counts a flag one side lacks as 0. The 0.1.0
      golden reports are kept in `tests/golden/schema1/` and compared
      with their schema-2 counterparts (no changes listed).

### OSS-105: report schema 2, step 2 (P-8 `max_gap`) — merged in [#96](https://github.com/PederFalkman/opensource/pull/96)

- [x] `max_gap` on `stale_mask`, `counter_decrease_mask` and `jump_mask`:
      rows further apart are not compared (a counter or jump value is
      measured against the last finite value before it). Plumbed through
      `flag_series`, `assess_quality`, `assess_frame`, `flag_frame` (also
      per column), `--max-gap` and the Pandera checks.
- [x] Reports record `parameters.max_gap` as an ISO 8601 duration; `null`
      when off, so the golden reports are unchanged.
- [x] Refused with the reason: a bare number (no unit), a non-positive or
      unreadable duration, input without a `DatetimeIndex`, and `max_gap`
      without a check it tunes.

### OSS-106: report schema 2, step 3 (P-7 `jump_max_rate`) — merged in [#97](https://github.com/PederFalkman/opensource/pull/97)

- [x] `jump_rate_mask(values, (delta, period))`: flags a change larger than
      `delta × elapsed / period`, with `elapsed` the exact time since the
      last finite value. Rows with the same timestamp are not compared;
      `max_gap` applies as for the other checks.
- [x] `jump_max_rate` on `flag_series`, `assess_quality`, `assess_frame`,
      `flag_frame` (also per column), `--jump-max-rate DELTA PERIOD`, and
      Pandera (`jump_rate_check`, `series_schema`). Either jump limit sets
      `JUMP`; `max_gap` may now tune a rate alone.
- [x] Reports record `parameters.jump_max_rate` as `[delta, duration]`;
      `null` when off, so the golden reports are unchanged.

### OSS-107: report schema 2, step 4 (P-9 `counter_rollover`) — merged in [#99](https://github.com/PederFalkman/opensource/pull/99) (reviewed in [#98](https://github.com/PederFalkman/opensource/pull/98), which merged into the OSS-106 branch instead of `main`)

- [x] `counter_rollover_mask(values, modulus)`: of the rows
      `counter_decrease_mask` flags (same `tolerance` and `max_gap`), those
      whose implied increase `cur + m − prev` is at least `-tolerance` and
      below `m / 2`, the owner's rule in `SCHEMA_2.md`.
- [x] `counter_rollover` on `flag_series` (sets `COUNTER_ROLLOVER`, bit
      1024, instead of `COUNTER_DECREASE`), `assess_quality`,
      `assess_frame`, `flag_frame` (also per column), `--counter-rollover`,
      and Pandera (`counter_check(rollover=...)` passes rollovers;
      `series_schema`). Requires `cumulative=True`; never guessed.
- [x] Reports record `parameters.counter_rollover` and count
      `COUNTER_ROLLOVER`; off by default, so the golden reports are
      unchanged.

### OSS-108: report schema 2, step 5 (P-10 overlap matching) — merged in [#101](https://github.com/PederFalkman/opensource/pull/101) (reviewed in [#100](https://github.com/PederFalkman/opensource/pull/100), which merged into the OSS-107 branch instead of `main`)

- [x] `compare_reports` matches listed gaps by overlap (intervals of
      missing timestamps, both ends included): exact matches stay
      unlisted, overlapping gaps with different bounds go to
      `gaps.changed` as before/after pairs (each pair for a split or a
      merge), and `resolved` / `new` keep only gaps overlapping nothing.
      A sweep over the sorted lists, so long lists stay linear.
- [x] `compare --format text` and `markdown` count changed gaps. `worse`
      is still decided by counts.
- [x] The comparison golden file is regenerated: its two shrunk/grown
      gaps move from resolved + new to `changed`; nothing else differs.
      Report schema 2 is now complete (`SCHEMA_2.md`, steps 1 to 5).

### OSS-109: prepare the 0.2.0 release — merged in [#102](https://github.com/PederFalkman/opensource/pull/102)

- [x] `RELEASE_DECISIONS.md` gains a 0.2.0 section: what the release
      contains, what did not change since 0.1.0 (no dependency, extra or
      data file), and the open questions per gate (G1, G3, G4, D6). It
      decides nothing; the 0.1.0 record is kept below it.
- [x] Changelog `[Unreleased]` reads as release notes: a summary and what
      changes for 0.1.0 users (schema version, `gaps.changed`, the
      summary line). Version stays `0.2.0.dev0`; the upload guard stays.
- [x] `examples/GUIDE.md` shows `jump_max_rate`, `max_gap`,
      `counter_rollover` and changed gaps, executed by the test suite.
- [x] "Open decisions" above now lists the 0.2.0 questions.

### OSS-110: pre-release review of the 0.2.0 code — merged in [#103](https://github.com/PederFalkman/opensource/pull/103)

- [x] Compared `jump_mask`, `jump_rate_mask`, `counter_decrease_mask`,
      `counter_rollover_mask` and `stale_mask` (with and without
      `max_gap`) with plain-Python references on 15,000 random series
      (NaN, ±inf, duplicates, gaps; s/us/ns units; three time zones), and
      overlap matching with brute force on 3,000 random gap sets, on the
      current and the lowest supported dependencies: no mismatch. Two of
      these comparisons are kept as property tests.
- [x] Fixed: on timestamps out of order, `jump_rate_mask` silently flagged
      nothing and `max_gap` treated earlier rows as near. The time-based
      options now refuse unsorted input (`ValueError`), as `flag_series`
      and the Pandera checks already did; without them the masks still
      compare in row order, as in 0.1.0.
- [x] Checked and fine: Pandera 0.24 and current in a `DataFrameSchema`;
      command-line refusal of negative, infinite and NaN values (exit 2);
      numpy values recorded as plain numbers; with every check on, a year
      of one-minute data takes about 0.6 s (0.3 s with the 0.1.0 checks);
      nothing is slower with the new options off.
- [x] Left as is: a `max_gap` beyond pandas' range (about 292 years) is
      reported as not a duration rather than out of range.

### OSS-111: 0.2.0 decision brief

- [x] A shareable page for the people who sign off (G1, G3, G4, D6), drawn
      from the 0.2.0 section of `RELEASE_DECISIONS.md`. No repository change.

### OSS-112 to OSS-132: pauses

- [x] No new work by the owner's choice while the 0.2.0 decisions were open.

### OSS-133: release energydata-kit 0.2.0 — merged in [#104](https://github.com/PederFalkman/opensource/pull/104)

- [x] `__version__` is `0.2.0`; the changelog's notes move under
      `## [0.2.0] - 2026-10-20` (date to set on release day) with an empty
      `[Unreleased]` above. The upload guard stays: no D6 line for 0.2.0
      exists, so the readiness test pins exactly the two G7 failures and
      `--guard` passes.
- [x] `RELEASE_DECISIONS.md`: a guide for the G3 reviewer (what to diff and
      what to confirm, each backed by a tool) and the remaining release
      steps.
- [x] Decisions recorded by the owner on 2026-10-20: G1 counsel confirmed,
      G3 signed off, G4 the 0.1.0 position stands, D6 GitHub release only,
      with the `**D6 approved:**` line naming `energydata-kit 0.2.0`.
- [x] Release edits: `Private :: Do Not Upload` removed, the readiness test
      expects nothing to fail (`--strict` exits 0, `--guard` passes), and the
      status lines in both READMEs, `SECURITY.md`, `CONTRIBUTING.md` and
      `RELEASE_GATES.md` name 0.2.0 as a GitHub release.
- [x] After merge (owner): tagged `energydata-kit-v0.2.0` on `344c862`; the
      *Release build* workflow passed (strict readiness, build, `twine
      check`, provenance attestation) and created the draft release, which
      the owner published on 2026-10-20 (marked pre-release). An independent
      rebuild from the tag gave matching checksums to compare.

### OSS-134: open 0.3.0 development — merged in [#105](https://github.com/PederFalkman/opensource/pull/105)

- [x] `__version__` is `0.3.0.dev0`; new changelog entries go under
      `[Unreleased]`, and the released sections are not edited.
- [x] The `Private :: Do Not Upload` guard is back: D6 approved 0.2.0 only,
      as a GitHub release. The readiness test again expects a package that
      is not release-ready, with the licence checks and `--guard` passing.
- [x] Status lines: 0.2.0 is the GitHub release, `main` is 0.3.0
      development.

### OSS-135: 0.3.0 proposals — merged in [#106](https://github.com/PederFalkman/opensource/pull/106)

- [x] P-12 to P-16 written up for the owner to approve one by one, each from
      a README "Known limitation", with effort, risk and whether it needs
      report schema 3 (only P-12). Docs only; nothing is authorized.
- [x] The owner approved P-14, P-15 and P-16 on 2026-10-20, to be built in
      the suggested order (P-16, P-14, P-15), one PR each. P-12 and P-13 are
      not approved.

### OSS-136: faster parsing of DST-offset timestamps (P-16) — merged in [#107](https://github.com/PederFalkman/opensource/pull/107)

- [x] `normalize_timestamps` splits strict `±HH:MM`/`Z` strings into local
      time and offset and parses the local part on pandas' fast naive path:
      350k strings take 0.33–0.40 s instead of about 2.3 s. Other forms and
      every failure fall back to the general parser.
- [x] Unchanged results and errors: a property test compares the two
      paths; 120,000 random inputs matched the previous code (results,
      error types and messages) on pandas 3.0.6 and 2.1.4. One divergence
      found on the way (an offset pushing a time past the ns range on
      pandas 2.1) is fixed and pinned by a test.
- [x] `benchmarks/run.py` times runs without `tracemalloc` (which slowed
      Python-level code and inflated every time) and adds the offset case;
      `PERFORMANCE.md` re-measured and says why all its times dropped.

### OSS-137: `report --gaps-csv` (P-14) — merged in [#108](https://github.com/PederFalkman/opensource/pull/108)

- [x] Writes every gap, beyond `--max-listed`, as
      `column,start,end,missing_count`, per column on that column's report
      grid (`find_missing_intervals` with the report's step, `tz` and
      `origin`), in the input's delimiter with `\n` line endings.
- [x] Refused before anything is written when a column has no step.
- [x] Tests: the CSV equals the uncapped report's gaps on fixed,
      local-calendar (DST) and shifted grids; per-column grids from a
      Table Schema; `;` input; header-only output; the refusal. The guide
      shows it (executed).

### OSS-138: `report --unit COLUMN=UNIT` (P-15) — merged in [#109](https://github.com/PederFalkman/opensource/pull/109)

- [x] `--unit` is repeatable: `COLUMN=UNIT` gives each named column
      metadata, with the shared `--resolution`, `--aggregation` and
      `--interval-label`; unnamed columns get none. A plain `--unit kWh`
      still describes a single column, exactly as before.
- [x] Refused with exit status 2: a column that is not assessed, a column
      named twice, an empty column or unit, a plain unit mixed with
      `COLUMN=UNIT` or given for several columns, and `--unit` with
      `--schema`.
- [x] Tests: per-column metadata and completeness in the frame report;
      one named column gives the same report as the plain form; each
      refusal. The README limitation is removed.

### OSS-139: prepare the 0.3.0 release — merged in [#110](https://github.com/PederFalkman/opensource/pull/110)

- [x] `RELEASE_DECISIONS.md` gains a 0.3.0 section: what the release
      contains, what did not change since 0.2.0 (no dependency, extra or
      data file), the open questions per gate (G1, G3, G4, D6) and a guide
      for the G3 reviewer. It decides nothing; earlier records are kept.
- [x] Changelog `[Unreleased]` reads as release notes: a summary and what
      changes for 0.2.0 users (one reworded error message). Version stays
      `0.3.0.dev0`; the upload guard stays.
- [x] `examples/GUIDE.md` shows `--unit COLUMN=UNIT`, executed by the test
      suite, next to the `--gaps-csv` example.
- [x] "Open decisions" above lists the 0.3.0 questions.

### OSS-140: release energydata-kit 0.3.0 — merged in [#111](https://github.com/PederFalkman/opensource/pull/111)

- [x] Decisions recorded by the owner on 2026-10-21: G1 counsel confirmed, G3
      signed off, G4 the 0.2.0 position stands, D6 GitHub release only,
      with the `**D6 approved:**` line naming `energydata-kit 0.3.0`.
- [x] `__version__` is `0.3.0`; the changelog's notes move under
      `## [0.3.0] - 2026-10-21` with an empty `[Unreleased]` above.
- [x] Release edits: `Private :: Do Not Upload` removed, the readiness test
      expects nothing to fail (`--strict` exits 0, `--guard` passes), and the
      status lines in both READMEs, `SECURITY.md`, `CONTRIBUTING.md` and
      `RELEASE_GATES.md` name 0.3.0 as a GitHub release.
- [x] After merge (owner): tagged `energydata-kit-v0.3.0` on `afa6974`; the
      *Release build* workflow passed (strict readiness, build, `twine
      check`, provenance attestation) and created the draft release, which
      the owner published on 2026-10-21 (marked pre-release).

### OSS-141: open 0.4.0 development — merged in [#112](https://github.com/PederFalkman/opensource/pull/112)

- [x] `__version__` is `0.4.0.dev0`; new changelog entries go under
      `[Unreleased]`, and the released sections are not edited.
- [x] The `Private :: Do Not Upload` guard is back: D6 approved 0.3.0 only,
      as a GitHub release. The readiness test again expects a package that
      is not release-ready, with the licence checks and `--guard` passing.
- [x] Status lines: 0.3.0 is the GitHub release, `main` is 0.4.0
      development.

### OSS-142: 0.4.0 proposals — merged in [#113](https://github.com/PederFalkman/opensource/pull/113)

- [x] P-17 to P-20 written up for the owner to approve one by one, ranked
      with P-12 and P-13 carried over from 0.3.0: effort, risk, and
      whether each needs report schema 3 (P-12 and P-20). The two measured
      claims (the `--unit` refusal, the offset-form parse times) were
      checked on 2026-10-21. Docs only; nothing is authorized.
- [x] The owner approved P-17 and P-19 on 2026-10-21, to be built one PR
      each (P-17 first). P-12, P-13, P-18 and P-20 are not approved.

### OSS-143: `--unit COLUMN=UNIT` names the value columns (P-17) — merged in [#114](https://github.com/PederFalkman/opensource/pull/114)

- [x] Without `--value-col`, the columns named by `--unit COLUMN=UNIT` are
      assessed, in `--unit` order; an explicit `--value-col` still decides,
      and `--unit` may then name a subset. A named column missing from the
      file is refused (exit status 2). A plain `--unit kWh` is unchanged.
- [x] Tests: the same report as naming each column twice; column order;
      a subset with `--value-col`; one named column; the refusals. The
      guide's example drops the repeated `--value-col` (executed).

### OSS-144: fast parsing of `±HHMM` and `±HH` offsets (P-19) — merged in [#115](https://github.com/PederFalkman/opensource/pull/115)

- [x] The OSS-136 split covers `±HHMM` and `±HH` as well as `±HH:MM` and
      `Z`: 350k strings take 0.34–0.47 s instead of 2.1–2.5 s. The last
      six characters decide form and offset and are cached, so `±HH:MM`
      is not slower (a first version without that cache was, by about
      15–20 %, and was reworked).
- [x] Unchanged results and errors: a new property test runs every form
      and malformed endings with the fast path on and off; 120,000 random
      batches matched on pandas 3.0.6 and 2.1.4.
- [x] Benchmark case for `+0100` strings; `PERFORMANCE.md`, the README
      limitation and the changelog updated.

### OSS-145: prepare the 0.4.0 release — merged in [#116](https://github.com/PederFalkman/opensource/pull/116)

- [x] `RELEASE_DECISIONS.md` gains a 0.4.0 section: what the release
      contains (P-17, P-19), what did not change since 0.3.0 (no
      dependency, extra or data file), the open questions per gate (G1,
      G3, G4, D6) and a guide for the G3 reviewer. It decides nothing;
      earlier records are kept.
- [x] Changelog `[Unreleased]` reads as release notes: a summary and what
      changes for 0.3.0 users. Version stays `0.4.0.dev0`; the upload
      guard stays.
- [x] "Open decisions" above lists the 0.4.0 questions.

### OSS-146: release energydata-kit 0.4.0 — merged in [#117](https://github.com/PederFalkman/opensource/pull/117)

- [x] Decisions recorded by the owner on 2026-10-21: G1 counsel confirmed, G3
      signed off, G4 the 0.3.0 position stands, D6 GitHub release only,
      with the `**D6 approved:**` line naming `energydata-kit 0.4.0`.
- [x] `__version__` is `0.4.0`; the changelog's notes move under
      `## [0.4.0] - 2026-10-21` with an empty `[Unreleased]` above.
- [x] Release edits: `Private :: Do Not Upload` removed, the readiness test
      expects nothing to fail (`--strict` exits 0, `--guard` passes), and the
      status lines in both READMEs, `SECURITY.md`, `CONTRIBUTING.md` and
      `RELEASE_GATES.md` name 0.4.0 as a GitHub release.
- [x] After merge (owner): tagged `energydata-kit-v0.4.0` on `6cc79fd`; the
      *Release build* workflow passed and created the draft release, which
      the owner published on 2026-10-21 (marked pre-release).

### OSS-147: open 0.5.0 development — merged in [#118](https://github.com/PederFalkman/opensource/pull/118)

- [x] `__version__` is `0.5.0.dev0`; new changelog entries go under
      `[Unreleased]`, and the released sections are not edited.
- [x] The `Private :: Do Not Upload` guard is back: D6 approved 0.4.0 only,
      as a GitHub release. The readiness test again expects a package that
      is not release-ready, with the licence checks and `--guard` passing.
- [x] Status lines: 0.4.0 is the GitHub release, `main` is 0.5.0
      development.

### OSS-148: 0.5.0 proposals — merged in [#119](https://github.com/PederFalkman/opensource/pull/119)

- [x] P-21 to P-23 written up for the owner to approve one by one, ranked
      with P-12, P-13, P-18 and P-20 carried over: effort, risk, and that
      none of the new items changes the report format. The behaviour behind
      P-21 (an explained gap still failing `--fail-on-issues`) was checked
      on 2026-10-21. Docs only; nothing is authorized.
- [x] The owner approved P-21 and P-23 on 2026-10-21, to be built one PR
      each (P-21 first, as proposed: the default behaviour, not opt-in).
      P-12, P-13, P-18, P-20 and P-22 are not approved.

### OSS-149: explained gaps do not fail `--fail-on-issues` (P-21) — merged in [#120](https://github.com/PederFalkman/opensource/pull/120)

- [x] `--fail-on-issues` counts a missing interval as an issue only when it
      lies outside every `--known-outage` period (per column in
      multi-column reports); flagged rows still always count. The report
      is unchanged.
- [x] Tests: a gap wholly inside an outage exits 0 (one and two columns);
      no outage, or one covering part of the gap, exits 1; a flagged row
      exits 1 even with every gap explained. Help text, README exit
      status, guide and changelog updated.

### OSS-150: `report --fail-on NAME` (P-23) — merged in [#121](https://github.com/PederFalkman/opensource/pull/121)

- [x] `--fail-on`, repeatable, fails the command only on the named issues:
      a `QualityFlag` name or `ANY` (case-insensitive), `gaps`, or
      `unexplained-gaps` (outside the `--known-outage` periods, as P-21).
      `--fail-on-issues` is now the same as `--fail-on ANY --fail-on
      unexplained-gaps`, with unchanged behaviour; the two options are
      refused together, as are unknown names (exit status 2).
- [x] Tests: each kind of name, case-insensitivity, a check that did not
      run, explained and unexplained gaps, a multi-column report and the
      refusals. Guide (executed), README exit status and changelog updated.

### OSS-151: prepare the 0.5.0 release — merged in [#122](https://github.com/PederFalkman/opensource/pull/122)

- [x] `RELEASE_DECISIONS.md` gains a 0.5.0 section: what the release
      contains (P-21, P-23), what did not change since 0.4.0 (no
      dependency, extra or data file), the open questions per gate (G1,
      G3, G4, D6) and a guide for the G3 reviewer. It decides nothing;
      earlier records are kept.
- [x] Changelog `[Unreleased]` reads as release notes: a summary and the
      one exit-status change for 0.4.0 users, with how to keep the old
      behaviour. Version stays `0.5.0.dev0`; the upload guard stays.
- [x] "Open decisions" above lists the 0.5.0 questions.

### OSS-152: release energydata-kit 0.5.0 — merged in [#123](https://github.com/PederFalkman/opensource/pull/123)

- [x] Decisions recorded by the owner on 2026-10-21: G1 counsel confirmed, G3
      signed off, G4 the 0.4.0 position stands, D6 GitHub release only,
      with the `**D6 approved:**` line naming `energydata-kit 0.5.0`.
- [x] `__version__` is `0.5.0`; the changelog's notes move under
      `## [0.5.0] - 2026-10-21` with an empty `[Unreleased]` above.
- [x] Release edits: `Private :: Do Not Upload` removed, the readiness test
      expects nothing to fail (`--strict` exits 0, `--guard` passes), and the
      status lines in both READMEs, `SECURITY.md`, `CONTRIBUTING.md` and
      `RELEASE_GATES.md` name 0.5.0 as a GitHub release.
- [x] After merge (owner): tagged `energydata-kit-v0.5.0` on `34cf9c7`; the
      *Release build* workflow passed and created the draft release, which
      the owner published on 2026-10-21.

### OSS-153: open 0.6.0 development — merged in [#124](https://github.com/PederFalkman/opensource/pull/124)

- [x] `__version__` is `0.6.0.dev0`; new changelog entries go under
      `[Unreleased]`, and the released sections are not edited.
- [x] The `Private :: Do Not Upload` guard is back: D6 approved 0.5.0 only,
      as a GitHub release. The readiness test again expects a package that
      is not release-ready, with the licence checks and `--guard` passing.
- [x] Status lines: 0.5.0 is the GitHub release, `main` is 0.6.0
      development.

### OSS-154: 0.6.0 proposals — merged in [#125](https://github.com/PederFalkman/opensource/pull/125)

- [x] P-24 and P-25 written up for the owner to approve one by one, ranked
      with P-12, P-13, P-18, P-20 and P-22 carried over; neither new item
      changes the report format. Both motivating behaviours (an explained
      gap failing `compare --fail-if-worse`; `report` refusing a second
      file) were checked on 2026-10-21. Docs only; nothing is authorized.
- [x] The owner approved P-24 and P-25 on 2026-10-22, to be built one PR
      each (P-24 first, as proposed: the default behaviour, not opt-in).
      P-12, P-13, P-18, P-20 and P-22 are not approved.

### OSS-155: `compare` treats explained gaps like `report` (P-24) — merged in [#126](https://github.com/PederFalkman/opensource/pull/126)

- [x] A series is worse when flagged rows rise, when missing intervals
      outside known outages rise, or when completeness falls (compared
      outside the outages when both reports record them). Reports without
      outages compare as before; the comparison format is unchanged.
- [x] Tests: an explained gap is not worse (single series and frame); an
      unexplained one is; without outages on both sides the plain rule
      applies; on the command line, `compare --fail-if-worse` exits 0 for
      the case where `report --fail-on-issues` does. The comparison golden
      files are unchanged. Help text, README, docstring and changelog
      updated.

### OSS-156: several input files in one report (P-25) — merged in [#127](https://github.com/PederFalkman/opensource/pull/127)

- [x] `report FILE...` reads each file with the same options and stacks
      them in order; duplicates across files are found as within one file,
      and `--flags-csv` writes one combined file. Files with different
      columns, CSV mixed with Parquet, and `-` with other files are refused
      (exit status 2).
- [x] Tests: two CSV halves give the same report and flags file, byte for
      byte, as the whole file; the same for two Parquet halves; an
      overlapping row is a duplicate; each refusal. README, guide
      (executed) and changelog updated.

### OSS-157: prepare the 0.6.0 release — merged in [#129](https://github.com/PederFalkman/opensource/pull/129)

- [x] `RELEASE_DECISIONS.md` gains a 0.6.0 section: what the release
      contains (P-24, P-25), what did not change since 0.5.0 (no
      dependency, extra or data file), the open questions per gate (G1,
      G3, G4, D6) and a guide for the G3 reviewer. It decides nothing;
      earlier records are kept.
- [x] Changelog `[Unreleased]` reads as release notes: a summary and the
      one comparison change for 0.5.0 users. Version stays `0.6.0.dev0`;
      the upload guard stays.
- [x] "Open decisions" above lists the 0.6.0 questions.

### OSS-158: release energydata-kit 0.6.0 — merged in [#130](https://github.com/PederFalkman/opensource/pull/130)

- [x] Decisions recorded by the owner on 2026-10-22: G1 counsel confirmed, G3
      signed off, G4 the 0.5.0 position stands, D6 GitHub release only,
      with the `**D6 approved:**` line naming `energydata-kit 0.6.0`.
- [x] `__version__` is `0.6.0`; the changelog's notes move under
      `## [0.6.0] - 2026-10-22` with an empty `[Unreleased]` above.
- [x] Release edits: `Private :: Do Not Upload` removed, the readiness test
      expects nothing to fail (`--strict` exits 0, `--guard` passes), and the
      status lines in both READMEs, `SECURITY.md`, `CONTRIBUTING.md` and
      `RELEASE_GATES.md` name 0.6.0 as a GitHub release.
- [x] After merge (owner): tagged `energydata-kit-v0.6.0` on `ba19231`; the
      *Release build* workflow passed (its first run with
      `actions/download-artifact` v8.0.2, #128) and created the draft release,
      which the owner published on 2026-10-22.

### OSS-159: open 0.7.0 development; pandas 3.1 compatibility — merged in [#131](https://github.com/PederFalkman/opensource/pull/131)

- [x] `__version__` is `0.7.0.dev0`; new changelog entries go under
      `[Unreleased]`, and the released sections are not edited.
- [x] The `Private :: Do Not Upload` guard is back: D6 approved 0.6.0 only,
      as a GitHub release. The readiness test again expects a package that
      is not release-ready, with the licence checks and `--guard` passing.
- [x] Status lines: 0.6.0 is the GitHub release, `main` is 0.7.0
      development.
- [x] pandas 3.1.0 (released 2026-10-22) deprecates `DatetimeIndex.values`
      on a timezone-aware index. `utc_ns` used it, so CI on `main` failed
      after #130 (the suite turns warnings into errors) while it passed on
      the PR the hour before. `utc_ns` now calls `tz_convert(None)` before
      reading the values: the same int64 values, still without a copy, on
      pandas 2.1.4 to 3.1.0. No other
      warning appears with pandas 3.1.

### OSS-160: 0.7.0 proposals — merged in [#132](https://github.com/PederFalkman/opensource/pull/132)

- [x] P-26 to P-28 written up for the owner to approve one by one, ranked
      with P-12, P-13, P-18, P-20 and P-22 carried over. P-26 and P-27
      change no report format; P-28 needs schema 3. Each motivating
      behaviour was checked on 2026-10-22 on `17314b6` (a several-file
      flags CSV without the file; the inferred step neither shown nor
      usable; agreeing and conflicting duplicates reported alike). Docs
      only; nothing is authorized.
- [x] The owner approved P-26 and P-27 on 2026-10-22, to be built one PR
      each (P-26 first, as proposed). P-28, P-12, P-13, P-18, P-20 and P-22
      are not approved.

### OSS-161: which file each flagged row came from (P-26) — merged in [#133](https://github.com/PederFalkman/opensource/pull/133)

- [x] With several input files, `--flags-csv` ends with a `source` column:
      each input row's file as given on the command line, empty for rows
      `--insert-missing` adds (they are the only rows with
      `MISSING_INTERVAL`, and input rows keep their order). Single-column
      and multi-column flags files alike.
- [x] With one file the flags CSV is unchanged; the JSON report is
      unchanged in both cases. A column already named `source` is refused
      (exit 2) before anything is written.
- [x] Tests: the source per row with and without `--insert-missing`, files
      out of time order, one file, and the refusal; the guide's several-file
      example (executed) reads the column. README and changelog updated.

### OSS-162: use the inferred step on request (P-27) — merged in [#134](https://github.com/PederFalkman/opensource/pull/134)

- [x] `report --freq inferred` takes the most common step between
      timestamps (`infer_resolution`, the report's `inferred_resolution`)
      and uses it as if passed, as a short `--freq` value (`15min`, `1h`,
      `90min`), for the report, `--flags-csv` and `--gaps-csv`. The JSON
      report is byte-identical to the one with that step given.
- [x] The text and Markdown summaries add "step: 15min, inferred (the most
      common step between timestamps)"; without a step, the "not checked"
      line names the most common step. Nothing is inferred unless asked.
- [x] Refused (exit 2) with `--tz` and for fewer than two distinct
      timestamps. Tests, the guide (executed), README and changelog.

### OSS-163: prepare the 0.7.0 release — merged in [#135](https://github.com/PederFalkman/opensource/pull/135)

- [x] `RELEASE_DECISIONS.md` gains a 0.7.0 section: what the release
      contains (P-26, P-27 and the pandas 3.1 fix), what did not change
      since 0.6.0 (no dependency, extra or data file), the open questions
      per gate (G1, G3, G4, D6) and a guide for the G3 reviewer. It decides
      nothing; earlier records are kept.
- [x] Changelog `[Unreleased]` reads as release notes: a summary and the
      two output changes for 0.6.0 users. Version stays `0.7.0.dev0`; the
      upload guard stays.
- [x] "Open decisions" above lists the 0.7.0 questions.

### OSS-164: release energydata-kit 0.7.0 — merged in [#136](https://github.com/PederFalkman/opensource/pull/136)

- [x] Decisions recorded by the owner on 2026-10-22: G1 counsel confirmed, G3
      signed off, G4 the 0.6.0 position stands, D6 GitHub release only,
      with the `**D6 approved:**` line naming `energydata-kit 0.7.0`.
- [x] `__version__` is `0.7.0`; the changelog's notes move under
      `## [0.7.0] - 2026-10-22` with an empty `[Unreleased]` above.
- [x] Release edits: `Private :: Do Not Upload` removed, the readiness test
      expects nothing to fail (`--strict` exits 0, `--guard` passes), and the
      status lines in both READMEs, `SECURITY.md`, `CONTRIBUTING.md` and
      `RELEASE_GATES.md` name 0.7.0 as a GitHub release.
- [x] After merge (owner): tagged `energydata-kit-v0.7.0` on `230483c`; the
      *Release build* workflow passed and created the draft release, which
      the owner published on 2026-10-22.

### OSS-165: open 0.8.0 development — this change

- [x] `__version__` is `0.8.0.dev0`; new changelog entries go under
      `[Unreleased]`, and the released sections are not edited.
- [x] The `Private :: Do Not Upload` guard is back: D6 approved 0.7.0 only,
      as a GitHub release. The readiness test again expects a package that
      is not release-ready, with the licence checks and `--guard` passing.
- [x] Status lines: 0.7.0 is the GitHub release, `main` is 0.8.0
      development.

## Explicitly not planned

Forecasting, grid/power-flow calculations, dynamic ratings, connection
planning, economic optimization, RODOT-related algorithms, market data
download. See `IP_BOUNDARY.md`.

## New packages

No new packages until explicitly authorized. Any proposal needs a scope
statement, an IP-boundary review and an entry in the existing-tools audit.
