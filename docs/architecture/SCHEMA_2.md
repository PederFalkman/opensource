# Report schema 2: design (OSS-103)

**Status:** accepted by the owner on 2026-10-20 (open questions answered
below). Step 1 is implemented in OSS-104, step 2 in OSS-105 and step 3 in OSS-106; steps 4 and 5 are not yet. P-7 to P-10 were approved by the owner on 2026-10-20 (see
`ROADMAP.md`); this note fixes what they change in the report format before
any code is written, so the format changes once, in 0.2.0.

## Why a new schema

Report schema 1 is fixed since 0.1.0: `report_schema.json` sets
`additionalProperties: false` on `parameters`, `flag_counts` and the
comparison's `gaps`. P-7, P-8 and P-9 add options a report must record (a
report states the parameters it was made with, so it can be reproduced), P-9
adds a flag, and P-10 changes the comparison's gap section. None of these fit
schema 1, and the flag-count section requires every flag name, so even P-9
alone would break validation of schema-1 consumers.

## What changes

All changes are additive: no schema-1 field is removed, renamed or given a
new meaning.

| Where | Schema 1 | Schema 2 | From |
|---|---|---|---|
| `schema_version` (reports, frame reports, comparisons) | `"1"` | `"2"` | all |
| `parameters.max_gap` | — | ISO 8601 duration string or `null` | P-8 |
| `parameters.jump_max_rate` | — | `null`, or `[number, duration]`, e.g. `[50.0, "PT1H"]` | P-7 |
| `parameters.counter_rollover` | — | number or `null` | P-9 |
| `flag_counts.COUNTER_ROLLOVER` | — | integer, required | P-9 |
| `QualityFlag.COUNTER_ROLLOVER` | — | bit 1024 (the flags column stays `uint16`) | P-9 |
| comparison `gaps.changed` | — | list of `{"before": gap, "after": gap}`, required | P-10 |
| comparison `gaps.resolved` / `gaps.new` | every gap not matched exactly | only gaps that overlap no gap on the other side | P-10 |

All three new options default to off (`null`), so a schema-2 report made
with the 0.1.0 options has exactly the schema-1 content plus the new
`null` parameters and `COUNTER_ROLLOVER: 0`. The golden tests pin this.

## Semantics

**P-8 `max_gap`.** For the stale, counter and jump checks, two consecutive
rows (in time order, after the existing handling of duplicates) are
compared only if they are at most `max_gap` apart. A stale run ends at a
larger gap; the row after the gap starts a new run. A counter decrease or a
jump across a larger gap is not flagged. Grid, gap and off-grid checks are
unaffected. Accepted as anything `pd.Timedelta` accepts; recorded as ISO 8601.

**P-7 `jump_max_rate`.** `(delta, period)`: flag a row when its change from
the previous finite value exceeds `delta` per `period`, scaled by the time
between the two rows (`|Δvalue| > delta × Δt / period`). Rows with the same
timestamp (duplicates, already flagged) are skipped. It can be combined with
`jump_max_delta`; either flags `JUMP`. With `max_gap`, a change across a
larger gap is not compared. The pair form keeps units honest: the caller
says "50 per hour", and nothing assumes a time unit.

**P-9 `counter_rollover`.** The register modulus `m` (e.g. `1e6`), supplied
by the caller and never guessed. With `cumulative=True`, a decrease from
`prev` to `cur` is a rollover, flagged `COUNTER_ROLLOVER` instead of
`COUNTER_DECREASE`, when the increase implied by wrapping,
`cur + m − prev`, is at least `-counter_tolerance` and less than `m / 2`.
Otherwise it stays `COUNTER_DECREASE` (a reset, or a drop too large to be a
wrap). Example with `m = 1e6`: 999 990 → 10 is a rollover (implied +20);
500 000 → 0 is a decrease.

**P-10 overlap matching.** Two listed gaps match when their intervals
overlap. Exact matches are still unchanged and listed nowhere. A gap that
overlaps exactly one gap on the other side, with different bounds, goes to
`changed`. If one gap overlaps several (a gap split in two, or two merged),
each pair is listed in `changed`. Only listed gaps are compared, as today
(`lists_truncated`). `worse` is not affected: it is still decided by counts.

## Reading old reports

- `compare_reports` accepts schema 1 against schema 1 (as today), 2 against
  2, and 1 against 2 in either order; its output is always schema 2.
- A schema-1 side is read as schema 2 with the new parameters `null`. Its
  missing `COUNTER_ROLLOVER` count is treated as *not reported*, not as 0:
  no delta is shown for it, so a comparison never invents a change.
- `report_schema.json` validates both: `schema_version` `"1"` selects the
  frozen schema-1 definitions (kept byte-for-byte), `"2"` the new ones.
- The package writes only schema 2 from 0.2.0 on. Writing schema 1 on
  request is not planned: it would mean keeping two writers in step for
  little gain. A consumer pinned to schema 1 keeps reading 0.1.0 reports
  and updates when it moves to 0.2.0.

## Command line and Pandera

- `report` gains `--max-gap DURATION`, `--jump-max-rate DELTA PERIOD` and
  `--counter-rollover M`, next to the existing check options, and applies
  them per column like the others.
- `--format text` and `markdown` show `changed` gaps in comparisons.
- `pandera_checks` gains the same options on its stale, counter and jump
  checks; Pandera reports failures and records no schema, so no format
  question arises there.

## Plan

One release, 0.2.0, in this order. Each item is its own PR with tests, and
the format changes only in the first:

1. **Schema 2 scaffolding**: version `"2"`, the new parameter fields and
   flag count (all `null` or 0), `report_schema.json` for 1 and 2,
   `compare_reports` reading both, regenerated golden reports, changelog.
2. **P-8** `max_gap`.
3. **P-7** `jump_max_rate` (uses P-8's gap handling).
4. **P-9** `counter_rollover` and the new flag.
5. **P-10** overlap matching in `compare_reports`.

## Decisions (owner, 2026-10-20)

1. **Rate period**: `jump_max_rate` is `(delta, period)`, recorded as
   `[delta, ISO 8601 duration]`.
2. **Rollover rule**: a rollover when the implied increase `cur + m − prev`
   is at least `-counter_tolerance` and below `m / 2`.
3. **Writing schema 1**: not offered; 0.2.0 writes only schema 2.
