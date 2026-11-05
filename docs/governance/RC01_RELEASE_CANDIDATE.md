# RC-01 — Release candidate decision packet

**INTERNAL WORKING DRAFT — NOT AN APPROVAL TO PUBLISH.**

## REPO/REPOS
- `Solid-soup/opensource`

## Scope and product separation
The Python package and the browser Workbench have **different** release
decisions. The last documented Python package GitHub release is 0.16.0.
The current package development version is 0.17.0.dev0 and retains the
`Private :: Do Not Upload` classifier. A green browser test does not
authorize a Python package release or production processing of user CSV.

The Workbench WEB-13 pilot runs four synthetic Python parity scenarios and
five negative checks in a real browser, including manifest pin, wheel digest
and cancellation. Its current test receipt is synthetic and does not attest
publisher identity or the provenance of Pyodide dependencies.

## Reproducible candidate evidence matrix
From the repository checkout:

```bash
python tools/release_candidate_matrix.py > rc01-local.json
```

The default report must say `NO_GO`, with missing browser receipts explicitly
marked `NOT_VERIFIED`. It is a planning and review report, not a request to
weaken gates.

For each browser, manually execute the WEB-09 workflow with target `web13`
on the **same frozen revision**. RC-02 retains a **sanitized**
`web13-synthetic-review.json` receipt for three days after a successful
run. RC-03 binds the receipt to its GitHub run ID, validates the exact
source commit and browser, and reads the downloaded ZIP directly.
The unfiltered browser result remains ephemeral; neither the review artifact
nor a green workflow proves publisher attestation or production readiness.
Download each actual run artifact before its three-day expiry, review the
corresponding Actions job and use the matching run URL. Do not invent evidence.

When actual local receipts and run URLs have been obtained:

```bash
python tools/release_candidate_matrix.py \
  --receipt chromium=/review/chromium.zip \
  --run-url chromium=https://github.com/Solid-soup/opensource/actions/runs/RUN_ID \
  --receipt firefox=/review/firefox.zip \
  --run-url firefox=https://github.com/Solid-soup/opensource/actions/runs/RUN_ID \
  --receipt webkit=/review/webkit.zip \
  --run-url webkit=https://github.com/Solid-soup/opensource/actions/runs/RUN_ID \
  --require-browser-matrix > rc01-review.json
```

Replace each `RUN_ID` with the corresponding GitHub Actions run number
and each path with a real local receipt. The script compares every receipt
with `git rev-parse HEAD`, its selected browser, and the run ID in the
supplied GitHub Actions URL, and validates the complete WEB-13 synthetic
schema. The ZIP must contain exactly the expected review JSON. If a PR has been merged after a
browser test, retest the frozen candidate commit: the earlier test is not
automatically applicable to the new HEAD.

A valid JSON receipt and syntactically matching run URL remain
**reviewer-supplied evidence**. The tool does not access GitHub's API and
cannot confirm the workflow was genuinely run or that it was successful.
An independent reviewer must inspect the actual GitHub Actions run and
job summary, wheel digest, exact source commit and network hosts.
**Linux WebKit is not iOS Safari certification.**

## Release gates and ownership
- **Package:** finalize version and changelog only for justified library
  changes; verify ownership (G1), Apache licence (G2), private IP review
  (G3), dependency licences (G4), CI on exact release commit (G5), docs
  (G6), and explicit version-specific owner decision D6 (G7). Keep the
  upload guard until a separate release PR has that approval.
- **Workbench:** additionally verify all intended browsers, publisher and
  dependency provenance, network destinations, resource limits, user-data
  privacy/security, accessibility, deployment isolation and incident plan.
- **No automatic go:** This tool reports `NO_GO` deliberately; only
  authorized humans may decide publication after reviewing independent
  evidence. It makes no GitHub tags, releases or uploads.
- **Cost control:** Browser workflows remain manually dispatched and do not
  run on push or PR. Successful WEB-13 runs now retain a small sanitized
  receipt for three days; no wheel or raw CSV is uploaded.
- **No user data:** The Workbench Python Worker remains synthetic-only.
  Existing local CSV preflight does not transfer customer files to it.

## Change history
- 2026-11-04: RC-01 added read-only candidate matrix, exact-revision
  browser receipt checks, conservative blockers and offline tests.
  Publication guard and data permissions unchanged.

## November 2026 ownership record
- `docs/governance/SOLID_SOUP_AB_OWNERSHIP_TRANSITION.md` records the
  individual's report that an assignment to Solid Soup AB was signed by
  both parties. This is **not** independent confirmation of the signed
  schedule, scope, authority, third-party rights or G1 sign-off.
- Until reviewed, keep the legal ownership verification and the version-
  specific publication decision D6 separate from automated release checks.

## Change history — continued
- 2026-11-05: Updated RC-01 handoff to match implemented RC-02/03 short-lived
  ZIP artifacts, exact run-ID binding and reported signed ownership agreement.
