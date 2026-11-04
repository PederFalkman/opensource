# WEB-17 — Local CSV structural preflight

**Internal working draft. No release, customer-data execution, external hosting or engineering decision approval.**

## REPO/REPOS
- `Solid-soup/opensource`

## Functional description
A dedicated page, `apps/workbench/web17_local_csv_preflight.html`, accepts a user-selected CSV as a **local structural check only**. The companion `web17_csv_preflight.mjs` decodes strict UTF-8 and validates 5 MiB maximum, 50,000 data rows, 128 columns, 16,384 characters per field, unique non-empty headers, quoted fields, CRLF and row-width consistency. The module returns **metadata only** (row count, column count, header labels and an explicit `approved_for_python:false`), not parsed rows. Empty physical lines are ignored; quoted empty fields are retained.

Unlike the separate WEB-13 review pilot, WEB-17 does **not** load Pyodide, download a wheel, send data to a Web Worker, call network APIs or upload files. It makes no claims about canonical Python results. All preflight output is non-authoritative metadata and may contain user-supplied column names. The page must not be deployed for real customer use until it receives a separate privacy and accessibility review.

## Testing and release gates
- Fast offline Node tests: `node --test apps/workbench/tests/web17_csv_preflight.test.mjs apps/workbench/tests/web17_preflight_contract.test.mjs`
- Existing Python 3.12 CI job now runs these tests without installing a browser.
- [ ] Latest-head CI and Security green
- [ ] Browser manual testing for file reset, invalid UTF-8, multiline quote, max-size and keyboard/screen-reader behavior
- [ ] Compare semantics against WEB-12 preview parser before sharing a single parsing library
- [ ] Reconcile with #205 (separate preview import) and #206 (synthetic Python pilot)
- [ ] Obtain separate security/privacy and IP/release approval before any customer-data runtime execution

## Controls and known limitations
This preflight reports CSV *structure*, not timestamp quality, measurement values, daylight-saving correctness, numeric suitability, canonical report parity or provenance. A successful import must never imply a file is safe to execute or suitable for engineering decisions. No synthetic worker command or arbitrary CSV execution is enabled. This page is intentionally not linked from the primary Workbench.

## Traceable change history
- 2026-11-04: Added separate local-only CSV preflight module and UI, strict bounds, offline tests and dedicated low-cost CI step. No change to existing public-facing `index.html` or to the synthetic Python Worker.

## Browser CSP hardening

The standalone review page now applies a restrictive Content Security Policy: `default-src 'none'`, `connect-src 'none'`, `worker-src 'none'`, `form-action 'none'` and `script-src 'self'`. To avoid relying on unsafe inline scripts, UI event handling resides in `web17_local_csv_preflight_ui.mjs` and imports the bounded parser from a second same-origin module. CSP is defense-in-depth; it is not a substitute for tested privacy controls or an externally validated deployment configuration.

### Additional change history
- 2026-11-04: Added strict browser CSP and external same-origin controller module, with static regression contracts; no Python Worker or external runtime introduced.
