# RC-02 — Short-lived, sanitized browser evidence artifacts

**INTERNAL WORKING DRAFT. No production or public release approval.**

## REPO/REPOS
- `Solid-soup/opensource`

## Purpose
RC-01 requires complete, commit-bound real-browser receipts, but WEB-21/23
left the full JSON in ephemeral runner storage. It could not be recovered
for the release matrix after the workflow finished. RC-02 connects those
systems without retaining raw test traces, user files or wheel archives.

## Behavior
The existing **manual-only** `WEB-09 browser worker pilot (targeted)`
workflow now, only when `target=web13` and the browser test succeeds:

1. Validates the raw receipt against the selected browser and
   `github.sha` using the WEB-13 validator.
2. Extracts only an allowlisted set of synthetic evidence fields:
   schema, classification, engine, source SHA, wheel SHA-256, PASS status,
   the four named parity/export outcomes, and the five negative checks.
   Host names, arbitrary exception strings, raw data and fixture rows
   are **not included**.
3. Uploads only the small `web13-synthetic-review.json` as a named
   GitHub Actions artifact, with **3-day retention**, no automatic runs
   and read-only repository permissions. The upload action is immutable
   SHA-pinned. It neither uploads the wheel nor records customer data.

A failed test, absent receipt, untrusted schema or wrong source commit
must not produce the review artifact. GitHub workflow logs still need
reviewed handling: they are independent of this sanitized artifact.

## Using evidence with RC-01
From the GitHub Actions run on the chosen frozen commit, download the
`web13-review-<browser>-<run_id>` artifact and extract its single JSON.
Use its actual run URL, along with the extracted JSON, as inputs to:

```bash
python tools/release_candidate_matrix.py \
  --receipt chromium=/path/to/web13-synthetic-review.json \
  --run-url chromium=https://github.com/Solid-soup/opensource/actions/runs/123456 \
  --require-browser-matrix
```

This example intentionally supplies **only one engine**, so strict matrix
mode returns nonzero until Firefox and Linux WebKit receipts are added.
Do not invent placeholders for either missing browser. Downloaded
artifacts are still not publisher-attested; the reviewer must separately
confirm the job's outcome, commit, network behavior and provenance.
A receipt from an older commit cannot establish PASS on a later release
candidate. Artifacts expire after three days and must not be treated as
permanent audit storage without an approved retention plan.

## Test and release gates
- Ordinary CI runs only offline Python tests, never downloads a browser.
- Manual Chromium/Firefox/WebKit execution remains a separate gate.
- Pyodide publisher/dependency trust, accessibility, privacy/security
  review and production operations remain unsatisfied until reviewed.
- `Private :: Do Not Upload`, D6 sign-off and customer CSV-to-Worker
  restrictions remain unchanged.

## Change history
- 2026-11-04: RC-02 added a validated allowlist exporter, bounded
  three-day artifact upload on successful manual browser runs and
  regression tests. No production or package version change.
