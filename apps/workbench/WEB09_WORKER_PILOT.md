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

## First real Chromium Worker validation — 2026-11-04

- GitHub Actions: [run 41804021927](https://github.com/Solid-soup/opensource/actions/runs/41804021927).
- Tested branch commit: `300968236e399bda836f57963611cfe92dd2d7ab`.
- **PASS**: signed-off only as *numerical parity of one synthetic dataset* (no publisher attestation).
- Worker loaded actual Pyodide, consumed a same-origin SHA-256-checked local candidate wheel, executed `energydata_kit.assess_quality`, and returned canonical schema-v2 data.
- Canonical field differences from local Python: **0**. Browser JavaScript page errors: **0**.
- The observed dependency hosts were `cdn.jsdelivr.net`, `pypi.org`, `files.pythonhosted.org`; wheel served from `127.0.0.1`.
- Subsequent hardening on this branch moves synthetic CSV generation **inside the worker** and rejects any caller-supplied CSV field. This change needs latest-head CI and a further real browser execution to be considered verified.
- After this initial test, the expensive Chromium workflow was restored to `workflow_dispatch` only.

**Not established:** identity/authenticity of the candidate manifest, cross-browser behavior, dependency trust, full browser/process memory, customer-data security or production readiness.

## Expanded worker-internal parity validation — 2026-11-04

- [Chromium workflow 41805199318](https://github.com/Solid-soup/opensource/actions/runs/41805199318), tested commit `16b493ace258e1d221d7363e850de18098110e48`.
- **4/4 PASS**, no canonical schema-v2 field differences, no page errors.
- Scenarios: baseline with 95 readings, autumn DST with 5, spring DST with 4, mixed UTC offset with 4.
- The Worker now constructs all four fixed test fixtures internally; calls carrying a `csvText` field are rejected. The browser sends only an approved scenario ID and the already SHA-256-checked wheel.
- The Pyodide interpreter was reused across the four scenarios. External dependencies were requested from jsDelivr and Python package hosts; this does not prove offline usability or supply-chain authenticity.
- The expensive targeted browser workflow was immediately returned to manual-only triggering after PASS.
- The pilot's **Cancel** operation now aborts pending manifest/wheel fetches through an AbortSignal before terminating the worker; offline tests check that both requests receive the signal. Real browser cancellation/retry behavior remains a release gate.

**Sign-off boundary:** exact numerical parity for these four synthetic fixtures in tested Chromium. This does not authorize real CSV input, release, hosting or use in operational decisions.

## Cancellation and retry regression gate

The optional real-Chromium `browser_worker_smoke.py` now exercises **Run → immediate Cancel → check no report or late status overwrite → Run again** before executing the established four-scenario numerical parity matrix. This is designed to detect stale asynchronous messages and workers that fail to recover after termination. The cancel/retry sequence subsequently passed in Chromium (run 41821627726; see evidence below).

The heavy workflow remains manual-only to control GitHub Actions minutes.

## Real Chromium cancel/retry verification — 2026-11-04

- [GitHub Actions run 41821627726](https://github.com/Solid-soup/opensource/actions/runs/41821627726)
- Tested commit `1eea79b02b49c0fa0de00bea9d605791bf0599ac`
- **PASS:** browser clicked Run, immediately Cancel, confirmed canceled status and empty result, checked the Run control was enabled, waited for stale-message overwrite, then started a new run.
- The restarted isolated Worker completed the baseline and three additional synthetic scenario comparisons against local Python.
- Canonical v2 report parity: **4/4 PASS; zero field differences**.
- Browser page errors: **0**.
- Observed runtime dependency origins: `cdn.jsdelivr.net`, `pypi.org`, `files.pythonhosted.org`; candidate assets served from loopback.
- After verification the costly browser workflow returned to **manual-only**, with no automatic PR/push/schedule trigger.

**Limitations:** This is a single browser test of an immediate cancellation and recovery path; it does not guarantee cancellation during every possible Pyodide initialization, package download or Python computation stage. It does not measure cancellation latency distributions, worker/process memory, Safari/Firefox behavior, or dependency integrity beyond the candidate wheel. The pilot remains synthetic-only and not release-approved.

## Pending-request cancellation test (new, not yet browser-verified)

The Chromium smoke harness intercepts the **manifest fetch** and **wheel fetch** separately and proves cancellation/recovery with subsequent Python parity. The real-browser PASS is recorded below. Worker startup and active Python execution cancellations are separate remaining gates.

## Manifest and wheel download cancellation verified — 2026-11-04

- [Chromium workflow 41823191892](https://github.com/Solid-soup/opensource/actions/runs/41823191892), tested commit `dc453d9d635ed9b7169dd967c5d1c565443dfe7b`.
- **PASS:** held the candidate manifest request open, pressed Cancel, verified the UI reports cancellation, holds no result, and re-enables Run.
- **PASS:** held the candidate EnergyData Kit wheel request open, repeated the same cancellation assertions, including absence of late UI status overwrite.
- **PASS:** after these two intentional pending-fetch cancellations and the existing immediate-cancel smoke, the worker restarted and returned **4/4 exact canonical v2 Python report matches** for the fixed synthetic scenarios.
- Browser page errors: **0**. No customer data or wheel upload was used; all candidate files came from the disposable loopback test server.
- The first attempt (run `41822963199`) failed because the Playwright request observer fired before its route handler had been dispatched. The harness now allows one event-loop dispatch interval before checking interception. The subsequent run passed.
- Playwright may log an internal `asyncio.exceptions.CancelledError` when a deliberately suspended intercepted route is torn down; the actual browser assertions and job outcome passed. This is instrumentation cleanup, **not** evidence that a full network/privacy audit has been completed.
- The expensive browser workflow was restored to `workflow_dispatch` only.

**Scope:** two pending network download stages and restart in tested Chromium. This does not yet prove cancellation during arbitrary Pyodide runtime initialization, Python computation, Firefox/Safari execution, total WASM memory safety or signed dependency provenance.

## Next gates

1. Ensure real Chromium worker parity and ordinary CI/security are green; record run ID and failures.
2. Remove the automatic PR trigger after initial browser validation.
3. Pin approved wheel, runtime/dependency assets, licence/SBOM and publisher provenance against an independent trusted release manifest.
4. Implement and benchmark full-process/WASM memory controls and user-failure recovery, including termination and retry.
5. Verify multiple browsers, larger and malformed datasets before opening any customer CSV path.
6. Keep `index.html` preview-only, and require a separate IP/privacy/accessibility/release decision before main Workbench integration.
