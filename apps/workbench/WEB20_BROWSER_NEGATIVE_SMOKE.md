# WEB-20 — Synthetic browser download-interruption and integrity negative tests

**Internal working draft. No customer files, deployment or production authorization.**

## REPO/REPOS
- `Solid-soup/opensource`

## Function description
Extend the existing manually invoked WEB-13 Python browser smoke to cover two
failure modes in addition to manifest pinning, four-scenario parity and JSON export.

1. Pending wheel fetch is intercepted and left unresolved until Cancel is clicked.
   The browser must show Cancelled, leave the report empty and Export disabled,
   re-enable Run, and resist late callbacks.
2. A wheel response whose byte length is unchanged but one byte is flipped is
   substituted **only in an ephemeral test server**. The browser must refuse it
   with the wheel SHA-256 mismatch before starting the Python Worker, retain no
   report, and keep Export disabled.
3. After removing the test routes, the same page must still execute the four
   fixed synthetic scenarios, compare canonical Python results to independent
   local references and export matching synthetic evidence.

## How to verify
Existing `.github/workflows/web09-worker-smoke.yml` remains manual-only. Select
`target=web13` and `browser=chromium` for the first approved review run;
Firefox and Linux WebKit are separate choices. The workflow builds an ephemeral
local wheel and does **not** publish candidate packages.

Fast Python contract tests run in the ordinary CI path:
`python -m pytest -q apps/workbench/tests/test_web13_browser_smoke.py`.
These checks inspect the harness, but **do not execute Playwright**.
The actual browser behavior must be verified by a separate manual invocation
before marking this milestone complete.

## Security / IP constraints
Do not treat the test-generated manifest digest as independently authorized
publisher provenance. Do not forward local CSV files to the Python Worker.
The additional wheel corruption test modifies only bytes in an intercepted
HTTP response, never any committed artifact or installable package.

## Traceable change history
- 2026-11-04: WEB-20 pending-wheel cancellation and same-size wheel
  corruption checks added to manual WEB-13 E2E; matching offline contract
  tests added. No changes to runtime code, schedules or automatic browser usage.
