# WEB-23 — Exact-revision browser evidence binding

**Internal working draft. Not a production or customer-data release.**

## REPO/REPOS
- `Solid-soup/opensource`

## Function description
The manually dispatched WEB-13 Python-in-browser test already records
the selected engine, ephemeral wheel SHA-256, source commit (when running
in Actions), four synthetic parity/export cases and five negative checks.
WEB-23 closes a verification ambiguity: a syntactically valid local receipt
must not be presented as proof for a **different Actions revision or browser**.

`render_web13_evidence_summary.py` now accepts
`--expected-commit <40-hex SHA>` and
`--expected-browser chromium|firefox|webkit`.
It fails closed (nonzero status, **NOT VERIFIED** in the summary) when
the receipt omits the commit, mismatches the expected SHA, uses another
browser, or contains malformed input. The manual workflow passes
`github.sha` and the exact browser input as separate trusted arguments.
A successful receipt remains **internal, synthetic, unattested**.

## Manual evidence procedure
1. In Actions, select **WEB-09 browser worker pilot (targeted)**.
2. Choose branch `main`, target `web13`, engine `chromium`. Run once.
3. Review the job summary's PASS, full commit SHA and wheel digest.
4. Separately run Firefox and Linux WebKit only when needed; each result
   proves only its own engine and revision. A Linux WebKit PASS is not an
   iOS Safari compatibility certification.
5. Record the links to actual successful Actions runs in the review record;
   a user-reported green test without a run URL is not independent evidence.

## Release candidate boundaries
- No automatic Playwright installation on push or PR.
- No runtime code, user CSV transmission, package publishing or D6
  approval changes.
- The workflow's `contents: read` permission remains unchanged.
- Dependency provenance, accessibility, privacy review and publisher
  attestation remain separate publication gates.

## Traceable change history
- 2026-11-04: Require exact GitHub source SHA and selected browser in
  evidence summary, add positive/negative CLI tests and fail-closed rules.
