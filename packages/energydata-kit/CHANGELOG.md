# Changelog

All notable changes to energydata-kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Changed

- `report` refuses `-o`, `--flags-csv` or `--gaps-csv` naming one of its
  input files or the same path as another of them, and `compare` refuses
  `-o` naming either report: the command exits with status 2 before
  anything is written (P-43). Before, `report in.csv -o in.csv` replaced
  the data file with the report and exited 0, `--flags-csv in.csv` replaced
  it with the flagged table, `-o x --gaps-csv x` kept only the gap list, and
  `compare a.json b.json -o a.json` replaced the earlier report. Paths are
  compared after resolving them, so `./in.csv` and `in.csv` are the same
  file. Writing over an earlier run's output file is still allowed. This
  changes only commands that destroyed a file.

## [0.13.0] - 2026-10-24

One opt-in exit-status option for `compare` and one clearer error message,
approved as P-41 and P-42: `--fail-on-changed-metadata` fails when two
reports describe the data differently, and a column name that differs from
the file's only by surrounding spaces is pointed out. The report and
comparison formats are unchanged (schema 2) and no public Python name is
added or changed.

**Upgrading from 0.12.0.** Nothing needs to change: the new option is
opt-in, and commands that worked with 0.12.0 give the same output and exit
status. Only the text of the "column not found" error can now end with a
hint; a script that matches that message exactly should match its start.

### Added

- `compare --fail-on-changed-metadata` exits with status 1 when the two
  reports describe the data differently, for example another unit,
  aggregation or resolution, in any column (P-41). Before, the same data
  reported with `--unit kW` and then `--unit kWh` gave "metadata changed:
  unit" and exited 0 even with `--fail-if-worse
  --fail-on-changed-parameters`. Opt-in, like
  `--fail-on-changed-parameters`. The comparison format is unchanged.

### Changed

- When `--timestamp-col`, `--time-col` or `--value-col` names a column
  that is not in the file but one column matches it once surrounding
  spaces are removed (for example ` kwh` from a header `timestamp, kwh`),
  the error now says so: "(column ' kwh' differs only by surrounding
  spaces)" (P-42). The command still exits with status 2 and nothing is
  renamed; pass the exact name, spaces included, to use that column.

## [0.12.0] - 2026-10-23

Two opt-in exit-status options for `compare`, approved as P-39 and P-40:
`--fail-on-removed-columns` fails when a column disappears between two
reports, and `--fail-on-changed-parameters` fails when the reports were
made differently. The report and comparison formats are unchanged (schema
2) and no public Python name is added or changed.

**Upgrading from 0.11.0.** Nothing needs to change: both options are
opt-in, and commands that worked with 0.11.0 give the same output and
exit status. A pipeline that checked `columns_removed` or the changed
parameters in the comparison JSON itself can use these options instead.

### Added

- `compare --fail-on-removed-columns` exits with status 1 when a column of
  the earlier report is missing from the later one (P-39). Before, a
  removed column was listed ("columns removed: b") and the command exited
  0, even with `--fail-if-worse`, so a meter that dropped out of an export
  passed unnoticed. Opt-in: `--fail-if-worse` keeps its meaning, and added
  columns never fail. The comparison format is unchanged.
- `compare --fail-on-changed-parameters` exits with status 1 when the two
  reports were made with different parameters, for example another step,
  bounds or known outages, in any column (P-40). Before, the same data
  reported with `--freq 1h` and then `2h` read as a completeness
  improvement, "parameters changed: freq", and exited 0 with
  `--fail-if-worse`. Opt-in: comparing across a deliberate change still
  works by default. The comparison format is unchanged.

## [0.11.0] - 2026-10-23

Two more command-line options, approved as P-37 and P-38: `--fail-on
metadata` fails when the report lists metadata issues, and
`--all-value-cols` assesses every column of a wide file. The report and
comparison formats are unchanged (schema 2) and no public Python name is
added or changed.

**Upgrading from 0.10.0.** Nothing needs to change: both options are
opt-in, and commands that worked with 0.10.0 give the same output and
exit status. If a script listed every column with `--value-col`, it can
use `--all-value-cols` instead.

### Added

- `report --fail-on metadata` exits with status 1 when the report lists
  metadata issues, such as `SUM_OF_POWER` for `--unit kW --aggregation
  sum` (P-37), in the report or in any column of a multi-column report.
  Before, they were printed and the command exited 0, even with
  `--fail-on-issues`. Opt-in: `--fail-on-issues` and the other names keep
  their exit status. The checks and the report format are unchanged.
- `report --all-value-cols` assesses every column except the timestamp
  column (and `--time-col`), giving the same report as one `--value-col`
  per column, in file order (P-38). Before, a file with several value
  columns needed each named, and a column added to an export later was
  silently not assessed. Refused together with `--value-col`. A text
  column is reported as `NON_NUMERIC` rather than skipped. The report
  format is unchanged.

## [0.10.0] - 2026-10-23

Two exit-status options for pipelines, approved as P-35 and P-36:
`--fail-on empty` fails on a file without data rows, and
`--min-completeness` fails below a completeness the caller chooses. The
report and comparison formats are unchanged (schema 2) and no public
Python name is added or changed.

**Upgrading from 0.9.0.** Nothing needs to change: both options are
opt-in, and commands that worked with 0.9.0 give the same output and exit
status. If a pipeline checked for empty files or parsed `completeness`
from the JSON report to fail below a limit, it can use these options
instead.

### Added

- `report --fail-on empty` exits with status 1 when the input has no data
  rows, e.g. an export that came back with only its header (P-35). Before,
  such a file always exited 0, even with `--fail-on-issues`, so a pipeline
  passed it as if the data were perfect. Opt-in: `--fail-on-issues` and
  the other names keep their exit status for an empty file. The report
  format is unchanged.
- `report --min-completeness FRACTION` exits with status 1 when
  completeness is below the fraction the caller chooses (0 to 1; there is
  no default), in the report or in any column of a multi-column report
  (P-36). With `--known-outage`, completeness without the outages is
  compared, as `compare --fail-if-worse` does. It fills the space between
  `--fail-on gaps` (any missing interval) and not failing at all, and
  combines with `--fail-on` and `--fail-on-issues`. When completeness is
  not checked (no step, no rows, or no expected interval left) the command
  is refused with status 2 instead of passing. The report format is
  unchanged.

## [0.9.0] - 2026-10-23

Two more command-line options for reading real exports, approved as P-34
and P-33: `--time-col` joins separate date and time columns, and
`--thousands` reads values with a thousands separator. The report and
comparison formats are unchanged (schema 2) and no public Python name is
added or changed.

**Upgrading from 0.8.0.** Nothing needs to change: both options are
opt-in, and commands that worked with 0.8.0 give the same output. If you
worked around these formats before (joining date and time by hand, or
removing separators), you can drop the workaround; the report is the
same.

### Added

- `report --time-col COL` joins a time-of-day column with `--timestamp-col`
  when a file splits date and time, e.g. `date;time;kwh` (P-34). Only the
  plain ISO forms are accepted (`2026-01-01` and `13:45` or `13:45:00`);
  `24:00`, a missing part or any other form is refused with the first rows
  that fail, rather than guessed. The usual `--assume-tz` rules apply. The
  flags CSV has one joined timestamp column, named after
  `--timestamp-col`. Before, passing the date column alone read every row
  of a day as the same timestamp, without an error. The report format is
  unchanged.
- `report --thousands SEP` reads values with a thousands separator, e.g.
  `--delimiter ';' --decimal , --thousands .` for `1.234,5` (P-33); the
  choices are `.`, `,`, `'` and `space`. Before, such values were not read
  as numbers, so every row was flagged `NON_NUMERIC` while the command
  exited 0. The separator must differ from `--decimal` and the delimiter
  (refused otherwise), and it applies to CSV input only. The flags CSV
  writes the values without it. The report format is unchanged.

## [0.8.0] - 2026-10-23

Two command-line additions for reading real exports, approved as P-29 and
P-30: `--encoding` for CSV files that are not UTF-8, and known-outage
times without a UTC offset read in `--assume-tz`. The report and
comparison formats are unchanged (schema 2) and no public Python name is
added or changed.

**Upgrading from 0.7.0.** Nothing needs to change: both additions are
opt-in, and commands that worked with 0.7.0 give the same output. Only
two error cases differ: a CSV that is not UTF-8 is still refused, with a
hint to pass `--encoding`, and a `--known-outage` time without an offset
is now accepted when `--assume-tz` is given instead of being refused.

### Added

- `report --encoding NAME` reads CSV input in another text encoding, e.g.
  `--encoding latin-1` or `cp1252` for many European exports (P-29). The
  default stays UTF-8, and the encoding is never guessed; when a file is
  not UTF-8 the error now suggests the option. `--flags-csv` and
  `--gaps-csv` are written in the same encoding, as they already follow
  the input's delimiter and decimal mark. An unknown encoding is refused,
  and so is `--encoding` with Parquet input or standard input. The report
  format is unchanged.
- With `--assume-tz`, `report --known-outage` reads times without a UTC
  offset in that zone, as the data's own timestamps are (P-30), e.g.
  `--assume-tz Europe/Oslo --known-outage "2026-01-01 02:00" "2026-01-01 04:00"`.
  The report records the periods in UTC, exactly as if they had been given
  with an offset. A time skipped at the start of DST follows
  `--nonexistent`; a time repeated at the end of DST is refused, with a
  hint to give it with an offset. Without `--assume-tz`, a time without an
  offset is refused as before, and the Python API (`known_outages=`) still
  requires timezone-aware timestamps.

## [0.7.0] - 2026-10-22

Two command-line additions approved as P-26 and P-27: with several input
files the flags CSV names each row's file, and `--freq inferred` uses the
most common step between timestamps on request. Also a fix for pandas
3.1. The report and comparison formats are unchanged (schema 2) and no
public Python name is added or changed.

**Upgrading from 0.6.0.** Check two cases, both in command-line output
only:

- If you pass several input files together with `--flags-csv`, the flags
  CSV now ends with a `source` column. A reader that expects the 0.6.0
  columns by position, or a value column named `source`, needs a change.
  One-file runs are unchanged.
- Without a step, the text and Markdown summaries' "completeness: not
  checked" line now also names the most common step between timestamps.
  The JSON report is unchanged.

### Added

- With several input files, `report --flags-csv` ends with a `source`
  column naming the file each row came from, as given on the command line
  (P-26). Rows added by `--insert-missing` have an empty source. With one
  file the flags CSV is unchanged, and the JSON report is unchanged in
  both cases. A value or timestamp column already named `source` is
  refused when several files are combined with `--flags-csv`.
- `report --freq inferred` uses the most common step between timestamps
  (the report's `inferred_resolution`) as the expected step, so gaps and
  completeness are checked on a first look at an unknown file (P-27). The
  report records it under `freq` exactly as if it had been passed; the
  text and Markdown summaries add a line saying the step was inferred.
  It is opt-in: without `--freq` nothing is guessed, but the summary now
  names the most common step. Refused with `--tz` (a fixed step only) and
  for fewer than two distinct timestamps.

### Fixed

- No `Pandas4Warning` with pandas 3.1. Timestamp handling read the
  nanosecond values of a timezone-aware index through `.values`, which
  pandas 3.1 deprecates; it now drops the timezone with
  `tz_convert(None)` first, which gives the same UTC values without a
  copy. Results are unchanged. Under 0.6.0 the warning is a
  `DeprecationWarning` that Python hides by default, so it shows only where
  warnings are enabled, for example in a test suite that turns them into
  errors.

## [0.6.0] - 2026-10-22

Two changes approved as P-24 and P-25: `compare` now treats gaps inside
known outages the way `report` does, and `report` reads several input
files (such as monthly exports) as one table. The report and comparison
formats are unchanged (schema 2) and no public Python name is added or
changed.

**Upgrading from 0.5.0.** Check one case: comparing two reports that
record known outages, `compare_reports(...).worse` (and the exit status of
`compare --fail-if-worse`) no longer counts missing intervals inside the
outages, so it can be `false` (0) where it was `true` (1). Comparisons of
reports without outages are unchanged.

### Added
- `report` reads several input files as one table, e.g. monthly exports:
  `energydata-kit report jan.csv feb.csv mar.csv`. The files are read with
  the same options and stacked in the order given; a timestamp in two files
  is a duplicate, as within one file, and `--flags-csv` writes one combined
  file. Refused (exit status 2): files with different columns, CSV mixed
  with Parquet, and `-` (standard input) with other files. The report
  format is unchanged.

### Changed
- `compare_reports` (and `compare --fail-if-worse`) no longer call a
  comparison worse because of missing intervals inside known outages: a
  series is worse when flagged rows rise, when missing intervals outside
  the outages (`n_missing_intervals - n_missing_explained`) rise, or when
  completeness falls, compared as `completeness_excluding_outages` when
  both reports record outages. This matches `report --fail-on-issues`
  since 0.5.0. Reports without known outages compare exactly as before;
  for reports with them, `worse` can now be `false` (and the exit status
  0) where it was `true` (1). The comparison format is unchanged.

## [0.5.0] - 2026-10-21

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
