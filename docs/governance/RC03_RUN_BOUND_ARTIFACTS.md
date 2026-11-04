# RC-03 — Direct ZIP consumption and run-specific browser evidence

**INTERNAL WORKING DRAFT — NO PUBLICATION OR CUSTOMER-DATA APPROVAL**

## REPO/REPOS
- `Solid-soup/opensource`

## Function description
RC-02 persists a sanitized WEB-13 receipt for three days after a successful
manual-only browser run. RC-03 adds a trusted `github.run_id` to that
allowlisted receipt and extends `tools/release_candidate_matrix.py` to
consume the downloaded GitHub Actions ZIP **without manual extraction**.

The matrix checks (1) the single expected artifact member,
`web13-synthetic-review.json`, (2) bounded ZIP and JSON sizes, (3) full
source-commit equality with the checked-out revision, (4) selected
browser, (5) schema and synthetic parity/negative checks, and (6)
receipt `github_run_id` against the supplied run URL. Invalid or missing
inputs fail closed as `NOT_VERIFIED`. The tool never grants a GO or
claims independent GitHub API verification of reviewer-supplied links.

## Reproducible reviewer process
Run Chromium, Firefox and Linux WebKit manually on the **same frozen
commit** via WEB-09 (`target=web13`). Download the corresponding
`web13-review-<browser>-<run_id>` ZIP files from each successful run.

```bash
python tools/release_candidate_matrix.py \
  --receipt chromium=/review/chromium.zip \
  --run-url chromium=https://github.com/Solid-soup/opensource/actions/runs/123456 \
  --receipt firefox=/review/firefox.zip \
  --run-url firefox=https://github.com/Solid-soup/opensource/actions/runs/123457 \
  --receipt webkit=/review/webkit.zip \
  --run-url webkit=https://github.com/Solid-soup/opensource/actions/runs/123458 \
  --require-browser-matrix > rc-review.json
```

Run IDs above are examples, **not evidence**. Replace every input with
actual files and their associated Actions URLs. The reviewer must also
inspect each run's real status, network hosts and complete job summary;
the local matrix cannot check GitHub's server-side authenticity.

## Safety and cost
- Manual-only browser executions; no new auto-triggered download jobs.
- Existing 3-day retention and `contents: read` permission stay intact.
- No raw logs, CSV, wheel archives, customer data, IP-sensitive algorithms
  or user-upload workflow added.
- D6 and `Private :: Do Not Upload` continue to gate package publishing.
- Linux WebKit is not iOS Safari compatibility evidence.
- Artifact ZIPs may contain hostile data: the reader accepts one
  known member only and limits compressed and decompressed size.

## Change history
- 2026-11-04: RC-03 run-ID binding, direct bounded ZIP evidence reader,
  adversarial ZIP tests and exporter/workflow regression coverage.
