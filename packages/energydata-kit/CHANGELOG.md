# Changelog

All notable changes to energydata-kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

Two command-line changes for pipelines, approved as P-21 and P-23: gaps
inside `--known-outage` periods no longer fail `--fail-on-issues`, and
`--fail-on NAME` chooses which issues fail the exit status. The report
format is unchanged (schema 2) and no public Python name is added or
changed.

**Upgrading from 0.4.0.** Check one case: a `report` command with both
`--known-outage` and `--fail-on-issues` whose only gaps lie inside the
outage periods now exits 0 instead of 1. To keep failing on every gap,
use `--fail-on ANY --fail-on gaps` instead of `--fail-on-issues`.

### Added
- `report --fail-on NAME`, repeatable, chooses which issues give exit
  status 1: a flag name (`NON_FINITE`, `STALE_VALUE`, … or `ANY` for any
  flagged row, case-insensitive), `gaps` for any missing interval, or
  `unexplained-gaps` for missing intervals outside the `--known-outage`
  periods. Without it, or with `--fail-on-issues`, the exit status is as
  before. Unknown names, and `--fail-on` together with `--fail-on-issues`,
  are refused (exit status 2).

### Changed
- `report --fail-on-issues` no longer fails on missing intervals that lie
  inside `--known-outage` periods: such gaps are reported as explained
  (`n_missing_explained`) and are not issues. Flagged rows and missing
  intervals outside the periods still give exit status 1. A command that
  combines both options and whose only gaps are explained now exits 0
  instead of 1. The report is unchanged.

## [0.4.0] - 2026-10-21

Two refinements approved as P-17 and P-19: `report --unit COLUMN=UNIT`
now also chooses the columns to assess, and timestamp strings with
`±HHMM` or `±HH` offsets parse about five times faster, like `±HH:MM`.
The report format is unchanged (schema 2), no public Python name is added
or changed, and parsed timestamps are identical.

**Upgrading from 0.3.0.** Nothing to change. A `report` command that gave
`--unit COLUMN=UNIT` without `--value-col` used to stop with "pass
--value-col" (exit status 2); it now assesses the named columns.

### Changed
- `report --unit COLUMN=UNIT` without `--value-col` assesses the named
  columns, in the order given, as `--schema` already does; until now the
  command stopped with "pass --value-col". An explicit `--value-col` still
  decides which columns are assessed. A column named by `--unit` that is
  not in the file is refused (exit status 2).
- `normalize_timestamps` (and the command line) parse timestamp strings
  with `±HHMM` or `±HH` offsets, such as `2024-03-31T03:00:00+0200`, about
  five times faster (350,000 strings: about 2.3 s → 0.4 s), as `±HH:MM`
  strings already were. Results and error messages are unchanged.

## [0.3.0] - 2026-10-21

Two command-line additions and faster timestamp parsing (approved as P-14
to P-16): `report --gaps-csv` writes the full gap list, `report --unit
COLUMN=UNIT` gives several columns their units without a Table Schema, and
offset timestamps such as `2024-03-31T03:00:00+02:00` parse about six
times faster. The report format is unchanged (schema 2), no public Python
name is added or changed, and with the 0.2.0 options results are identical.

**Upgrading from 0.2.0.** Nothing to change. One error message is reworded:
a plain `--unit` with several value columns now reads "--unit UNIT
describes a single column; for several, repeat --unit COLUMN=UNIT, or use
--schema" (exit status 2, as before).

### Changed
- `normalize_timestamps` (and the command line) parse ISO 8601 strings
  whose UTC offset changes across DST about six times faster (350,000
  strings: about 2.3 s → 0.4 s) when they have the common form
  `YYYY-MM-DD[T ]HH:MM[:SS[.fff]]` followed by `Z` or `±HH:MM`. Results
  and error messages are unchanged; any other form uses the general parser
  as before.

### Added
- `report --gaps-csv FILE` writes every gap, also those beyond
  `--max-listed`, as `column,start,end,missing_count`: one row per gap,
  per column, on the grid that column's report uses, in the input's
  delimiter and with `\n` line endings. Refused (exit status 2, nothing
  written) when a column has no step. The JSON report is unchanged.
- `report --unit COLUMN=UNIT`, repeatable, gives several value columns
  metadata without a Table Schema; `--resolution`, `--aggregation` and
  `--interval-label` apply to each named column, and columns not named get
  none. The single-column `--unit kWh` form is unchanged. Refused (exit
  status 2): a column that is not assessed, a column named twice, a plain
  unit with several columns, and `--unit` together with `--schema`.

## [0.2.0] - 2026-10-20

Report schema 2 and four opt-in refinements of the checks: gaps that stop
comparisons (`max_gap`), a jump limit per unit of time (`jump_max_rate`),
counter rollovers told apart from resets (`counter_rollover`), and
comparisons that match gaps by overlap. Every new option is off by default:
with the 0.1.0 options, masks and flags are unchanged, and reports differ
only by the schema version and the new fields (`null` parameters,
`COUNTER_ROLLOVER: 0`).

**Upgrading from 0.1.0.**
- Code that requires `"schema_version": "1"` must accept `"2"`. The shipped
  `report_schema.json` validates both, and `compare_reports` reads both.
- In comparisons, a gap whose bounds changed is now listed under
  `gaps.changed`, no longer as one resolved and one new gap, so `resolved`
  and `new` can be shorter than before for the same reports.
- The text and Markdown comparison summaries add `changed: N` to the gap
  line; JSON remains the format for automation.
- Nothing was removed or renamed; the new options are keyword-only.

### Changed
- **Report schema 2.** Reports, frame reports and comparisons now carry
  `"schema_version": "2"`. Schema 2 only adds fields: the parameters
  `max_gap`, `jump_max_rate` and `counter_rollover` (`null` when the
  option is off; see Added), the flag count `COUNTER_ROLLOVER`, and `changed` in a
  comparison's gap section. `report_schema.json` validates schemas 1 and 2.
- `compare_reports` compares schema-1 (0.1.0) and schema-2 reports, also
  with each other, and writes schema 2. A flag count only one side reports
  is no longer compared as 0 against the other.
- `compare_reports` matches gaps by overlap. A gap whose interval overlaps
  one on the other side with different bounds (it shrank, grew or moved) is
  listed in the new `gaps.changed` as a `{"before", "after"}` pair, once per
  overlapping pair when a gap was split or merged; `resolved` and `new` now
  hold only gaps that overlap nothing on the other side. `compare --format
  text` and `markdown` count changed gaps. `worse` is unchanged.

### Added
- `max_gap` for the stale, counter and jump checks (`--max-gap` on the
  command line): rows further apart than this are not compared, so a stale
  run ends at the gap and a counter drop or jump across it is not flagged.
  Accepted by `stale_mask`, `counter_decrease_mask`, `jump_mask`,
  `flag_series`, `assess_quality`, `assess_frame` and `flag_frame` (also
  per column), and the Pandera checks; recorded in reports as an ISO 8601
  duration. Off by default, so results without it are unchanged. Like
  `jump_max_rate`, it measures time between rows, so it needs a sorted
  index and refuses timestamps out of order.
- `jump_max_rate=(delta, period)`, e.g. `(50.0, "1h")` (`--jump-max-rate 50
  1h`): flag `JUMP` where a value changes faster than `delta` per `period`
  since the previous finite value, so the limit scales with the time between
  rows. Combines with `jump_max_delta` and `max_gap`. New `jump_rate_mask`
  and Pandera `jump_rate_check`; accepted by `flag_series`,
  `assess_quality`, `assess_frame` and `flag_frame` (also per column) and
  `series_schema`; recorded in reports as `[delta, ISO 8601 duration]`.
- `counter_rollover`, the register modulus of a cumulative counter
  (`--counter-rollover M`): a decrease consistent with wrapping past it,
  with an implied increase `cur + m - prev` from `-counter_tolerance` to
  below `m / 2`, is flagged with the new `QualityFlag.COUNTER_ROLLOVER`
  (1024) instead of `COUNTER_DECREASE`. New `counter_rollover_mask`;
  accepted by `flag_series`, `assess_quality`, `assess_frame` and
  `flag_frame` (also per column), Pandera `counter_check(rollover=...)` and
  `series_schema`; recorded in reports. The modulus is never guessed.
- `examples/GUIDE.md` shows the new options and changed gaps, executed by
  the test suite like the rest of the guide.

## [0.1.0] - 2026-10-19

First release: quality checks for metered energy time series, on top of
pandas and Pint. Input data is never modified; checks return masks, flags and
reports. Licensed Apache-2.0; the licence ships in the wheel and the sdist.

### Timestamps and grids
- `normalize_timestamps`: UTC normalization with explicit DST policies
  (`ambiguous`, `nonexistent`); naive or unparseable values are reported, not
  guessed (unparseable ones by position). A date without a time of day is
  naive and needs `assume_tz`.
- `summarize_timestamps` and `infer_resolution`.
- Fixed-step grids: `expected_grid`, `find_missing_intervals`,
  `missing_timestamps`, `find_duplicate_timestamps`, `duplicate_mask` and
  `off_grid_mask`, each with `origin=` to anchor the grid.
- Local-calendar steps via `tz=` (for example `"D"`, `"W-MON"` or `"MS"` in
  `"Europe/Stockholm"`), DST-aware.
- Interval semantics: `relabel_intervals` and `interval_bounds` for start/end
  labels; `local_day_completeness` per local calendar day, on the same grid
  as the report (`origin=` included).

### Values and flags
- Masks for missing, non-finite, non-numeric and out-of-bounds values, plus
  the opt-in `stale_mask`, `counter_decrease_mask` and `jump_mask`, tuned with
  `stale_atol`, `stale_exclude`, `counter_tolerance` and `jump_max_delta`
  (a run is excluded when all its values lie within `stale_atol` of an
  excluded value).
- `QualityFlag` bitmask (`MISSING_VALUE` = 1 up to `JUMP` = 512) and the
  non-destructive `flag_series`; `flag_frame` and `flag_column` for several
  columns at once.

### Metadata
- `MeasurementMetadata`: unit (validated with Pint, including `var`; units
  with characters Pint would silently drop are rejected), resolution,
  aggregation, interval label and time zone.
- `check_metadata_consistency` returning `MetadataIssue`s with the stable codes
  `SUM_OF_POWER`, `AVERAGED_ENERGY`, `MISSING_RESOLUTION` and
  `LABEL_ON_INSTANTANEOUS`.
- `to_table_schema` / `from_table_schema`: Frictionless Table Schema export and
  import, under a namespaced `"energydata_kit"` field property. A malformed
  schema raises `ValueError` naming the problem; a `name` inside the
  namespace, which would relabel the field, is rejected.

### Reports
- `assess_quality` → `QualityReport`: deterministic JSON (report schema 1)
  with a SHA-256 data fingerprint, the parameters used, metadata issues and
  per-local-day completeness. Without `freq`, the step is the metadata
  resolution; one with no fixed length (`"MS"`, `"W-MON"`) counts in the
  metadata's time zone. `"D"` is a 24-hour step; for local days, which are
  23 or 25 hours long across DST, pass `tz` (`--tz`).
- `assess_frame` → `FrameQualityReport`: one report for several columns that
  share a timestamp index, with per-column options; each column's section
  equals `assess_quality` on that column. A `timestamps` section states the
  facts that depend only on the shared index (rows, range, step,
  completeness, gaps, duplicates, known-outage figures) once, or is `null`
  when columns take different steps from their metadata.
- Known outages: `known_outages=[(start, end), ...]` lists periods in which
  data is known to be missing. Reports count the missing intervals inside
  them (`n_missing_explained`) and give `completeness_excluding_outages`;
  gaps, totals, completeness and flags are unchanged.
- `compare_reports` → `ReportComparison`: what changed between two reports
  (objects or saved JSON), with deltas, resolved and new gaps, and a `worse`
  verdict. Input that is not a report, such as a saved comparison, is
  rejected with the first bad field named.
- `report_schema.json`: a JSON Schema (draft 2020-12) for report schema 1,
  covering single-series reports, frame reports and comparisons; it ships in
  the package. Schema 1 is fixed from this release on.

### Command line
`energydata-kit` (also `python -m energydata_kit`); exit status 0 OK, 1 issues
found on request, 2 usage, input or file error (listed in `--help`).
- `report`: JSON report for one or more CSV columns, every check option,
  `--known-outage START END`, `--flags-csv`, `--fail-on-issues`, and
  `--format text` or `markdown` for a readable summary (Markdown to paste
  into an issue or pull request; column names escaped and kept on one
  line; when completeness is missing, the summary says why). Metadata from `--unit` (one column, with `--resolution`,
  `--aggregation`, `--interval-label` and `--timezone`) or `--schema` (a
  Table Schema, any number of columns). `--delimiter` and `--decimal` read `;`-, tab- or
  `|`-separated files with decimal commas; the flags CSV follows the input's
  format.
- Parquet input: a file ending in `.parquet`, `.parq` or `.pq` is read with
  the optional extra `[parquet]` (`pyarrow>=14.0.1`) and gives the same
  report as the CSV of the same data. Timestamps may be a column or the
  named index pandas writes with `to_parquet`; unreadable files and
  directories are refused with exit status 2.
- `compare`: what changed between two saved reports, with `--fail-if-worse`
  and `--format text` or `markdown`.

### Integrations and documentation
- Optional extra `[pandera]`: `energydata_kit.pandera_checks` with check
  factories and `series_schema(...)`, built on the same masks as
  `flag_series`; Pandera 0.24 or later, tested on the lowest and the latest.
- `make_synthetic_series` for deterministic test data.
- `examples/GUIDE.md`: worked examples from raw local meter timestamps to
  reports and the command line, executed by the test suite.

### Conventions
- Required inputs are positional and every optional argument is keyword-only;
  the public signatures are pinned by `tests/test_public_api.py`.
- Invalid input raises `ValueError` or `TypeError` with the reason (for
  example a `NaT` timestamp, a flag value no flag uses or a non-finite
  bound or tolerance), never a silent guess. Options are checked when they
  are given, also for empty data and when a Pandera check is built:
  numeric options take real numbers (numpy ones included) but not booleans
  or text, `cumulative` takes `True` or `False`, run lengths and
  `max_listed` take integers, and `tz` must name a known time zone.
- Python 3.11 to 3.14, tested on Linux, Windows and macOS.
- Reports, flags CSVs and fingerprints are byte-identical on every
  supported Python, pandas and numpy version and on every platform (files
  end lines in `\n`), pinned by golden tests.
- `assess_quality` on a year of one-minute data takes under a quarter of a
  second on the benchmark machine (`docs/architecture/PERFORMANCE.md`).
