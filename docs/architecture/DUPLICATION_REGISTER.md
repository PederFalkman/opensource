# Duplication register

Records each capability energydata-kit could have rebuilt, and whether it was
reused, wrapped or (deliberately) implemented. Update it in the same PR as
any new capability or copied code.

| Capability | Existing implementation | Decision | Where | Justification |
|---|---|---|---|---|
| Datetime parsing, tz localization/conversion, DST policies | pandas | **Reused** (thin wrapper) | `timestamps.normalize_timestamps` | Adds only input-consistency rules: reject mixed naive/aware input and silent assumptions. |
| Regular grid generation, duplicate detection, NaN detection | pandas / numpy | **Reused** | `intervals`, `flags` | Wrapped to return energy-friendly results (gap runs, every-occurrence masks). |
| Unit parsing and dimensionality | Pint | **Reused** | `metadata.validate_unit`, `units_compatible` | Registry extended with `var` only. No conversion API wrapped: use Pint directly. |
| Unit-aware arrays | pint-pandas | **Not duplicated** | — | Out of scope; recommended to users. |
| DataFrame schema validation | Pandera, Great Expectations | **Not duplicated**; Pandera **integrated** as an optional extra | `pandera_checks` | Our masks are exposed as Pandera checks instead of building a schema engine. |
| Gap-run detection on a fixed UTC grid | Pecos `check_timestamp`, pvanalytics `quality.time` (similar, not identical) | **Implemented** (~20 lines on pandas) | `intervals.find_missing_intervals` | Needs tz-aware UTC grid semantics and non-destructive output; Pecos modifies data, pvanalytics is PV-specific. Independently written. |
| Non-destructive quality flags | SaQC (GPL) | **Implemented** | `flags` | GPL prevents reuse in a permissive package; our flag model is a small, independent bitmask. |
| Reproducible report + fingerprint | none found | **Implemented** | `report` | Gap identified in audit. |
| Synthetic test series | numpy RNG | **Implemented** (generic sinusoid + noise) | `synthetic` | Must be generated here to keep test data free of real/customer data. |
| Range (bounds) check | Pecos, pvanalytics, Pandera checks | **Implemented** (5 lines) | `flags.out_of_bounds_mask` | Trivial; needed to emit our flag. Bounds are caller-supplied; no domain limits shipped. |
| Start/end interval relabelling | pandas offset arithmetic | **Reused** (one-line shift, wrapped for explicitness) | `semantics.relabel_intervals` | No reviewed tool models interval labels (audit gap 1). |
| Unit vs. aggregation consistency | Pint dimensionality | **Reused** for dimensions; rules **implemented** | `semantics.check_metadata_consistency` | Four generic physics rules; no domain thresholds. |
| Per-local-day completeness | none found (Pecos/pvanalytics count spacing, not local days) | **Implemented** | `semantics.local_day_completeness` | Audit gap 2 (DST-aware expected counts). Independently written. |
| Stale / flat-line detection | Pecos `check_delta`, pvanalytics `quality.gaps` stale checks, OpenSTEF flatliner | **Implemented** (run-length on numpy) | `flags.stale_mask` | Needed as a non-destructive flag; reference tools are data-modifying, PV-specific or forecasting-centred (MPL). Behavior compared at the documentation level only; no code read or copied. |
| Cumulative-counter decrease | Pecos `check_increment` (similar) | **Implemented** (forward-fill comparison) | `flags.counter_decrease_mask` | A few lines on pandas; flags only the drop row. Independently written. |
| Jump between consecutive values | Pecos `check_increment` / `check_delta` (similar idea) | **Implemented** (forward-fill comparison) | `flags.jump_mask` | A few lines on pandas; caller-supplied absolute limit, flags the row where the change lands. Independently written; no code read or copied. |
| Local-calendar grids (daily/weekly/monthly in a time zone) | pandas `date_range` with a tz-aware start | **Reused** | `intervals.expected_grid(tz=...)` | pandas already lays out calendar offsets in wall-clock time across DST; we only add origin and window handling. |
| Table Schema metadata export | frictionless-py | **Spec implemented directly** (~40 lines, no dependency) | `table_schema` | Producing the JSON needs no library; frictionless-py would add a large dependency for a dict. |

## Copied third-party code

None.
