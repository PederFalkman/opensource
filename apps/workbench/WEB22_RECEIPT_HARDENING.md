# WEB-22 — Fail-closed browser evidence receipt validation

**Internal working draft. No production, publication or customer-data approval.**

## REPO/REPOS
- `Solid-soup/opensource`

## Problem
The WEB-21 summary validator assumed JSON fields such as `browser`,
`cases[*].scenario` and `negative_checks[*]` were hashable strings.
Malformed JSON could trigger `TypeError: unhashable type` while trying to
render a GitHub Actions summary. A malformed receipt must be rejected,
not crash the secondary reporting step or be presented as passed.

## Functional change
- Check browser and scenario identifiers are strings before set membership.
- Check all negative-test identifiers are strings before comparing their set.
- Require each scenario's difference count to be exactly integer zero
  (Python boolean `False` no longer passes by equality with zero).
- Treat malformed receipts as `NOT VERIFIED` with nonzero CLI exit status.
- Keep raw errors, hosts, URLs and untrusted fields out of Markdown output.

## Verification
Fast offline Python tests exercise malformed nested objects, lists, numeric
scenario entries and booleans, and invoke the CLI against malformed JSON.
Existing normal four-scenario, five-negative-test and source-commit tests
remain part of the Python 3.12 Workbench suite.

No Playwright or browser runtime is triggered by this change. The real
browser E2E remains manual-only and must pass independently on an intended
revision before any browser capability is called verified.

## Change history
- 2026-11-04: WEB-22 receipt type safety and adversarial regression tests.
  No runtime Python engine, customer import or release gate changes.
