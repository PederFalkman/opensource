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
| DataFrame schema validation | Pandera, Great Expectations | **Not duplicated** | — | Recommended alongside energydata-kit. |
| Gap-run detection on a fixed UTC grid | Pecos `check_timestamp`, pvanalytics `quality.time` (similar, not identical) | **Implemented** (~20 lines on pandas) | `intervals.find_missing_intervals` | Needs tz-aware UTC grid semantics and non-destructive output; Pecos modifies data, pvanalytics is PV-specific. Independently written. |
| Non-destructive quality flags | SaQC (GPL) | **Implemented** | `flags` | GPL prevents reuse in a permissive package; our flag model is a small, independent bitmask. |
| Reproducible report + fingerprint | none found | **Implemented** | `report` | Gap identified in audit. |
| Synthetic test series | numpy RNG | **Implemented** (generic sinusoid + noise) | `synthetic` | Must be generated here to keep test data free of real/customer data. |
| Range (bounds) check | Pecos, pvanalytics, Pandera checks | **Implemented** (5 lines) | `flags.out_of_bounds_mask` | Trivial; needed to emit our flag. Bounds are caller-supplied; no domain limits shipped. |

## Copied third-party code

None.
