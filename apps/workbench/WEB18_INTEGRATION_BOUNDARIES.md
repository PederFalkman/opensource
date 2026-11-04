# WEB-18 — Integrated Workbench trust-boundary regression gates

**Internal working draft. Not an external release approval.**

## REPO/REPOS
- `Solid-soup/opensource`

## Purpose
WEB-10 through WEB-17 are merged into `main`, but the user CSV preflight and browser Python execution remain separate trust domains. This gate prevents an accidental future change from silently forwarding user files into the experimental Python Worker, or promoting a browser-only preview to authoritative Python.

## Function descriptions
- Public preview (`index.html`): bounded local CSV preview. It is never labeled Python-validated.
- Local preflight (`web17_local_csv_preflight.html`): local CSV structural check with a restrictive CSP and no network or Worker transfer.
- Synthetic review (`web13_synthetic_review.html`): runs fixed synthetic fixtures using the existing Worker protocol; exports internal, non-attested evidence.
- Worker (`web09_engine_worker.mjs`): rejects externally supplied CSV payloads and only accepts fixed synthetic scenario identifiers.
- Candidate loader: staged package integrity checks are not publisher authentication.

## CI and verification
`node --test apps/workbench/tests/web18_integration_boundaries.test.mjs` provides static fail-closed integration regressions and is automatically picked up by the existing `*.test.mjs` offline Node job in `.github/workflows/ci.yml`.

These are source-contract tests, **not runtime browser security tests**. A real browser end-to-end run remains an independent requirement, as do dependency provenance, accessibility, signed artifacts, network/privacy evaluation and explicit owner approval before real customer data is handled by the experimental Worker.

## Traceable change record
- 2026-11-04: WEB-18 added after merging WEB-10, WEB-11, WEB-12, WEB-13/14 and WEB-17. No runtime logic changed; all checks offline and synthetic-only.
