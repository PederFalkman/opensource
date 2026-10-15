# Existing tools audit

**Date:** 2026-10-15 · **Purpose:** avoid duplicating mature tools and confirm
that energydata-kit fills a real gap.

Versions, release dates, licenses and Python floors come from the PyPI JSON
API on the date above. Commit activity was not checked (GitHub API not
reachable from the audit environment), so "maintenance" means release recency
only. Licenses must be re-verified before any code reuse.

## 1. This repository

Before OSS-01 (2026-10-15), the repository held only a one-line `README.md` and a
standard Python `.gitignore`. There were no workflows, packages or license file.
The GitHub repository is **public**.

## 2. Related repositories in the owner's account

| Repository | Visibility | Origin | License file | Overlap with energydata-kit | Decision |
|---|---|---|---|---|---|
| PINNeAPPle | Public | Its metadata points to the PINNeAPPle-Labs upstream | Apache-2.0 (+ NOTICE) | Weak. Generic dataset-quality checks for physics/ML arrays; no timestamp, time-zone or energy semantics. | Do not depend on it (PINN framework, out of scope). Nothing copied. |
| pinnfactory | Public | Its metadata points to the PINNeAPPle-Labs upstream | Apache-2.0 | None (PINN code generator) | Not relevant. |
| energydb | Public | Its README names rebase-energy/energydb as home | Apache-2.0 | Partial. A thin Pint-based unit helper inside a time-series storage library. No timestamp validation, gap detection or flags. | Possible future interop target; do not copy. energydata-kit uses Pint directly. |
| Private Solid Soup / MICA repositories (2 reviewed, names withheld from this public document) | Private | Not forks | None | One has a narrow schema-drift guard for a data source; the other has no relevant data-quality tooling. | **Not used as a source.** No code, structure, fixtures or parameters were copied or consulted while writing energydata-kit. |

The private repositories were reviewed read-only to confirm that this package
does not duplicate or extract internal work. The review found nothing that
energydata-kit needs from them.

## 3. Public open-source alternatives

| Tool | License | Latest (date) | Overlap with scope | Decision |
|---|---|---|---|---|
| pandas | BSD-3-Clause | 3.0.6 (2026-09-17) | Building blocks: `tz_localize(ambiguous, nonexistent)`, `date_range`, `duplicated`, `isna` | **Depend on** |
| numpy | BSD-3-Clause | — | Array math | **Depend on** |
| Pint | BSD | 0.26.1 (2026-09-10; needs Python ≥ 3.12, older releases support 3.11) | Unit registry, parsing, dimensionality, conversion | **Depend on** for unit validation; no own unit system |
| pint-pandas | BSD | 0.8.0 (2026-03-20) | Unit-aware pandas dtype | Reference; possible optional extra later |
| Pandera | MIT | 0.34.1 (2026-10-06) | DataFrame schema/dtype validation (pass/fail) | **Do not duplicate**; recommend alongside. Possible integration later. |
| Great Expectations | Apache-2.0 | 1.24.0 (2026-10-07) | General data-validation framework, human-readable data docs | Do not duplicate; heavy for this use case |
| frictionless-py | MIT | 5.20.0 (2026-10-08) | Table Schema / Data Package metadata | Reference for a future metadata export format |
| Pecos (Sandia) | BSD-3-Clause | 1.0.0 (2025-04-03) | Closest overlap: timestamp, missing, range and delta checks; HTML reports. Not interval-aware; its timestamp check modifies data. | Reference for stale/delta checks (roadmap); do not copy |
| SaQC (UFZ) | GPL-3.0-or-later | 2.10.0 (2026-08-24) | General time-series QC with non-destructive flags | Design reference only. GPL rules out copying code into a permissively licensed package. |
| pvanalytics | MIT | 0.2.2 (2024-11-27) | PV-specific QC: gaps, stale values, timestamp spacing | Reference; PV-specific |
| OpenSTEF (LF Energy) | MPL-2.0 | 4.4.8 (2026-10-12) | Forecasting framework with completeness and flatliner validation helpers | Do not depend on (forecasting-centric, heavy). Forecasting is out of scope. |
| entsoe-py | MIT | 0.8.1 (2026-09-04) | ENTSO-E market/grid data client | Not relevant (data download out of scope) |
| pvlib | BSD-3-Clause | 0.16.1 (2026-09-26) | PV modelling | Not relevant |
| tsfresh, solar-data-tools | MIT / BSD-2-Clause | — | ML features / PV analytics | Not relevant |
| PowSyBl and other LF Energy grid projects | — | not checked | Grid simulation | Not relevant (out of scope by IP boundary) |

Sources: `https://pypi.org/project/<name>/` for each package;
https://github.com/sandialabs/pecos; https://pecos.readthedocs.io;
https://github.com/pvlib/pvanalytics; https://github.com/OpenSTEF/openstef;
https://git.ufz.de/rdm-software/saqc.

## 4. Gap analysis

Mature tools already cover schema validation, unit systems, table metadata and
generic NaN/range checks. energydata-kit does not reimplement them. The gaps it
targets, which none of the reviewed permissive tools address directly:

1. **Interval semantics.** None of the reviewed tools records whether a
   timestamp labels the start or the end of an interval, or whether a value is
   instantaneous, a mean or a sum. energydata-kit records these in
   `MeasurementMetadata` and, since OSS-02, uses them: explicit start/end
   relabelling, unit-vs-aggregation consistency advice and per-local-day
   completeness.
2. **DST-safe gap and duplicate detection.** Gap detection on a UTC grid, with
   explicit policies for ambiguous and nonexistent local times, so the 92/100
   interval days at 15-minute resolution are not misreported. Since OSS-05,
   daily/weekly/monthly data in local time can use an explicit local-calendar
   grid (`tz=`) as well.
3. **Stable bitmask quality flags.** A documented, composable integer flag set
   under a permissive license (SaQC has a richer model but is GPL).
4. **Byte-reproducible reports.** Deterministic JSON plus a data fingerprint,
   suitable for CI and audit trails, rather than human-oriented HTML.

## 5. Legally reusable public code

No code was copied. Candidates for future *reference* (not copying) are Pecos
(BSD-3) and pvanalytics (MIT) for stale-value and delta checks. Copying from
either would be license-compatible with Apache-2.0 if attribution is kept, but
writing independently is preferred. SaQC (GPL) and OpenSTEF (MPL-2.0) must not
be copied into this repository.
