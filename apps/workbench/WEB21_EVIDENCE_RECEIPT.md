# WEB-21 — Auditable synthetic browser receipt

**Internal working draft. No production or customer-data authorization.**

## REPO/REPOS
- `Solid-soup/opensource`

## Function description
The manually invoked WEB-13 Playwright smoke now supports
`--evidence-file PATH`, writing its existing synthetic-only JSON result to
an explicitly selected local file. The receipt additionally includes the
SHA-256 of the ephemeral wheel and, where present, the GitHub runner commit.
It records browser, all four synthetic parity/export outcomes, the five
negative security checks, observed host names, and browser exceptions.

The existing manual-only GitHub Actions workflow uses this flag and renders
a **bounded** summary in its GitHub Actions job summary. This is readable
without searching through the entire job log. The summary validator rejects
incomplete or inconsistent evidence and deliberately excludes raw hosts,
URLs, errors, datasets and arbitrary free text. Reviewers must consult the
full job log under appropriate access when investigating network behavior.

## Run
Open Actions > **WEB-09 browser worker pilot (targeted)** > Run workflow.
Select `target=web13` and `browser=chromium`. Other supported choices
are Firefox and Linux WebKit. Each browser must be run independently.
The workflow is not triggered by pushes, PRs or a schedule.

A complete PASS reports actual execution **only for that selected browser
and commit**, not signed package provenance, customer-data authorization,
privacy certification or a general production release.

No candidate wheel, raw fixture CSV, or customer content is retained by
this change. Job summary is only a reviewed synthetic test summary;
the full receipt remains inside the ephemeral runner unless separately
handled under an approved retention policy.

## Verification and limits
- Offline Python tests check the evidence schema and fail-closed summary.
- Standard CI never starts Playwright, downloads Pyodide or runs a browser.
- A browser-E2E check is complete only after an actual manual job succeeds
  on the intended revision.
- The evidence file is written for completed runs; early exceptions or
  timeouts produce no receipt and the job summary must state NOT VERIFIED.

## Change history
- 2026-11-04: Added local receipt output, commit/wheel binding, manual
  workflow step summary, bounded validation and regression tests.
