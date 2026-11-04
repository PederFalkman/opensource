# WEB-09 — Candidate wheel → Web Worker → Python (synthetic pilot)

**Internal working draft; not approved for release.**

## Delivered in this branch

- `web09_candidate_loader.mjs`: bounded same-origin candidate manifest and wheel fetch with SHA-256 integrity verification. The manifest explicitly stays `candidate-not-approved`, which is **not package authenticity**.
- `web09_engine_worker.mjs`: an isolated module Web Worker, loading Pyodide 0.29.5, pandas/numpy and Pint, installing the already verified wheel only in its virtual interpreter, and running real `energydata_kit.assess_quality`. Checks the digest again inside the worker. Reports progress, completion and errors.
- `web09_worker_pilot.html`: an explicit-action, synthetic-only experiment; fixed Workbench fixture; no CSV/file upload, no release link. Supports cancellation by terminating the worker. A failed wheel/integrity step never loads Python.
- `browser_worker_smoke.py`: a temporary local HTTP server stages a newly built wheel and candidate manifest outside source control, opens Chromium, runs the fixed synthetic fixture, and compares every canonical v2 field against local Python.
- `tests/web09_worker.test.cjs`: offline loader integrity and syntax checks, exact baseline fixture comparison, and worker digest-before-import ordering.
- `.github/workflows/web09-worker-smoke.yml`: targeted browser validation once, then revert to manual-only triggering to control Actions costs.

## Boundaries

The new worker code still contacts Pyodide CDN, PyPI and wheel dependency origins after a button click; it does not verify every third-party runtime dependency. A candidate manifest plus hash checks file equality relative to the manifest, **not publisher identity or trust**. The worker remains synthetic-only, and the pilot only accepts one locally staged wheel. It must not be exposed publicly or used for customer decisions.

This is an **architectural pilot**, not an automatically installable or secure end-user product. Real browser worker parity is pending until the workflow completes.

## Next gates

1. Ensure real Chromium worker parity and ordinary CI/security are green; record run ID and failures.
2. Remove the automatic PR trigger after initial browser validation.
3. Pin approved wheel, runtime/dependency assets, licence/SBOM and publisher provenance against an independent trusted release manifest.
4. Implement and benchmark full-process/WASM memory controls and user-failure recovery, including termination and retry.
5. Verify multiple browsers, larger and malformed datasets before opening any customer CSV path.
6. Keep `index.html` preview-only, and require a separate IP/privacy/accessibility/release decision before main Workbench integration.
