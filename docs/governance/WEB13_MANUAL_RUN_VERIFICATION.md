# WEB-13 — Locate and verify manual browser runs

**INTERNAL WORKING DRAFT — EVIDENCE DISCOVERY, NOT RELEASE APPROVAL**

## REPO/REPOS
- `Solid-soup/opensource`

## Purpose
Find the Chromium, Firefox and Linux WebKit manual WEB-09 runs without
guessing run IDs or interpreting a green workflow as a publication approval.
This procedure reads GitHub-hosted run **metadata**; the existing
`tools/release_candidate_matrix.py` validates downloaded synthetic review
receipts separately. Neither independently establishes G1–G7 or Workbench
production readiness.

## Step 1 — enumerate actual manual runs
With GitHub CLI authenticated for the repository:

```bash
gh run list \
  --repo Solid-soup/opensource \
  --workflow web09-worker-smoke.yml \
  --event workflow_dispatch \
  --limit 50 \
  --json databaseId,headSha,status,conclusion,createdAt,url
```

Find three successful **completed** runs. They must have the same
`headSha` equal to the frozen release-candidate commit. A run triggered
against `main` at a later SHA does not count as evidence for the earlier
candidate. Run metadata alone does not prove whether the run selected
`target=web13`; check its workflow input/job summary and artifact.

## Step 2 — inspect each run and review artifact
Replace `RUN_ID` with an actual ID from step 1:

```bash
gh run view RUN_ID --repo Solid-soup/opensource
gh api repos/Solid-soup/opensource/actions/runs/RUN_ID/artifacts \
  --jq '.artifacts[] | [.id, .name, .expired] | @tsv'
```

For a valid WEB-13 review run, expect exactly one relevant non-expired
artifact named `web13-review-<browser>-<RUN_ID>`, where browser is
`chromium`, `firefox` or `webkit`. An artifact name is **not** proof that
its JSON passes validation. Download each artifact privately, not into
the public repository:

```bash
mkdir -p "$HOME/web13-private-review"
gh run download RUN_ID \
  --repo Solid-soup/opensource \
  --name web13-review-BROWSER-RUN_ID \
  --dir "$HOME/web13-private-review/BROWSER"
```

`gh run download` extracts artifacts by default. To run the ZIP-based
RC-03 matrix, download the corresponding archive from the GitHub Actions
artifact UI instead. Alternatively, supply the extracted
`web13-synthetic-review.json` path to the matrix.

## Step 3 — validate on the frozen candidate
Check out the exact full commit first. Supply a real path and run URL
per browser, not placeholders:

```bash
python tools/release_candidate_matrix.py \
  --receipt chromium=/private/chromium/web13-synthetic-review.json \
  --run-url chromium=https://github.com/Solid-soup/opensource/actions/runs/CHROMIUM_RUN_ID \
  --receipt firefox=/private/firefox/web13-synthetic-review.json \
  --run-url firefox=https://github.com/Solid-soup/opensource/actions/runs/FIREFOX_RUN_ID \
  --receipt webkit=/private/webkit/web13-synthetic-review.json \
  --run-url webkit=https://github.com/Solid-soup/opensource/actions/runs/WEBKIT_RUN_ID \
  --require-browser-matrix > "$HOME/web13-private-review/rc-matrix.json"
```

A `RECEIPT_VALID_REVIEW_REQUIRED` status confirms the locally checked
schema, SHA/browser and reviewer-supplied run ID, not GitHub server
authenticity or publication authorization. The reviewer must inspect
GitHub job conclusions and network behavior. All artifacts expire after
three days; re-run manually if expired.

## Failure and safety handling
- A missing or expired artifact is `NOT_VERIFIED`, never presumed passed.
- Do not manually rewrite a `github_run_id`, browser or SHA to make a
  receipt match.
- Do not store private account credentials, signed IP agreements, customer
  files, wheel contents or raw browser log output in public issues.
- Keep `Private :: Do Not Upload` and D6/G7 version-specific approval
  requirements unchanged.
- Linux WebKit is not iOS Safari certification.

## Change history
- 2026-11-05: Added bounded operator procedure for actual GitHub manual
  run discovery and artifact review. No workflow dispatch, publication or
  customer-data enablement.
