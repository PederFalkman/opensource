# WEB-19 — Review-pinned synthetic Workbench end-to-end gate

**Internal working draft. Not approved for production, releases or customer data.**

## REPO/REPOS
- `Solid-soup/opensource`

## Functional change
The existing WEB-13 synthetic-only page now requires a lowercase SHA-256 digest of the exact *candidate manifest bytes* before requesting any candidate asset. The review digest must be supplied from an independently governed review record, not copied out of the manifest response. With a missing or malformed pin, the page does not fetch the manifest or wheel. With a mismatched but well-formed pin, the manifest request is made but the wheel request is refused. The existing wheel digest verification and Worker-side verification remain in effect.

This is a **technical check**, not a signature, identity proof, independently authenticated release channel or authorization for external data. Browser Python still fetches external runtime dependencies, and the Worker still accepts only four fixed synthetic scenarios.

## Manual browser integration
The existing `.github/workflows/web09-worker-smoke.yml` is still triggered only by `workflow_dispatch`. A new `target` choice defaults to `web13`; legacy `web09` remains available. Browser choice remains Chromium, Firefox or Linux WebKit. Selecting WEB-13 runs `web13_browser_smoke.py` against a locally built, ephemeral review-only wheel.

That smoke:
1. Constructs a **test-only** manifest and a digest of its bytes; this test receipt is not claimed to be independently governed release provenance.
2. Confirms missing pin causes zero candidate HTTP requests.
3. Confirms incorrect pin refuses wheel download.
4. Cancels an outstanding manifest request.
5. Executes four synthetic scenarios and compares every canonical report field with independent local Python reference computations.
6. Verifies exported JSON matches displayed evidence and checks for browser page errors.

Tests for the static review contract and manual workflow run in the existing low-cost Node test job. Real Playwright browser execution remains opt-in and has **not been run simply by adding this code**.

## Security and release gates
- Manual browser runs must pass on the latest head for the specific browser before claiming WEB-13 end-to-end verification.
- Investigate runtime network destinations, pin dependencies and Pyodide distribution, and provide signed/publisher-verified release provenance and an independently governed digest distribution mechanism.
- Preserve separate local CSV preflight and synthetic-only Worker. No user-CSV-to-Worker transfer without a new approved security/privacy review.
- Verify accessibility, timeout/restart behavior and memory pressure on supported devices.
- Do not publish candidate wheel assets or use operational datasets.

## Change history
- 2026-11-04: Introduced required independent manifest review pin in WEB-13, negative browser checks, explicit manual WEB-13 Actions target and offline regression contract tests.
