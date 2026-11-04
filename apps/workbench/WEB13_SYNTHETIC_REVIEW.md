# WEB-13 — Integrated synthetic Python review UI

**Internal working draft. No customer data, signed releases, external distribution or production authorization.**

## REPO/REPOS
- `Solid-soup/opensource` only.

## Functional description
A separate static `web13_synthetic_review.html` connects the existing candidate wheel loader to `web09_engine_worker.mjs` without altering the production-facing `index.html`. Users select exactly one of four built-in synthetic fixtures, click Run, see loading/analyzing/error/completion states, cancel, inspect canonical-v2 quality metrics, and export a **synthetic-only** JSON report. The review page does not offer file selection or arbitrary CSV transport.

A small independent state module rejects invalid scenarios and malformed reports, prevents overlapping runs, and ignores late messages after cancellation or a new run. The current browser page performs the wheel SHA-256 check; the worker independently checks the supplied digest. The candidate loader does not establish publisher identity. WEB-11's independently supplied review pin is a separate unmerged security improvement.

## Verification
Fast offline Node regression tests cover scenario allowlist, stage transitions, stale completion/cancel-retry, overlapping runs, schema and engine checks. Browser execution must be manually verified on the *latest PR head* before merge, using only approved synthetic fixtures. Existing WEB-09 parity evidence belongs to older commits, not this new page.

## Important limitations and next gates
- Not a user-CSV Workbench; worker explicitly refuses CSV payloads.
- No signed release chain, complete SBOM, authenticated Pyodide distribution, or privacy/network approval.
- Pyodide and runtime dependencies currently download from external CDNs on cold start.
- Do not use operational, confidential, regulated or customer files.
- Next: merge and validate WEB-10/11/12 independently; bind separately governed manifest pin; manual targeted real-browser run and keyboard/accessibility checks; explicit security and release approval **before** any user file is permitted.
- Heavy Playwright jobs remain manual-only to protect GitHub usage.

## Change history
- 2026-11-04: First separate integrated synthetic review experience, state guards, regression tests and explicit data boundaries.

## WEB-14 addition — synthetic evidence envelope

The pilot exports `energydata-synthetic-review-evidence.json` with fixed scenario identifier, the SHA-256 of the fetched wheel, a single wall-clock elapsed measurement, and the original canonical-v2 Python wrapper. Its explicit `internal-unattested-synthetic-only` status and limitations prevent equating byte-integrity evidence with publisher authenticity or independent scientific verification. It is **not** a signed provenance ledger or a benchmark.

`web14_evidence.mjs` checks the allowlisted scenario, valid lowercase digest, bounded finite elapsed duration and internally consistent report counters before constructing the envelope. Dedicated Node tests cover malicious identifiers, invalid digests, implausible times, contradictory quality counters and forged data-source metadata. Latest-head test execution and browser end-to-end validation remain required.

### Traceable change history
- 2026-11-04: WEB-14 synthetic evidence export and stricter canonical validation added to experimental WEB-13 branch. No customer file input, new dependencies or automatic paid browser workflow.
