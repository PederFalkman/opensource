# RC-04 — Release-candidate handoff and evidence checklist

**Internal working draft. Review-only; no release approval.**

## REPO/REPOS
- `Solid-soup/opensource`

## Decision and scope
- The last recorded `energydata-kit` release is 0.16.0 (GitHub only).
- `main` currently targets 0.17.0.dev0. Package release, Workbench
  deployment and production customer CSV execution are separate decisions.
- The ownership transition document records a **user-reported** signed
  personal-to-Solid Soup AB assignment. Its asset schedule and legal scope
  require private review. This file does not make G1 pass.
- `Private :: Do Not Upload` remains active. D6 is not approved for 0.17.0.

## Freeze and browser evidence
Choose a candidate commit on `main` after all planned source/documentation
changes have merged. Record its **full 40-character SHA**, and do not merge
additional PRs while collecting evidence for that candidate.

From [WEB-09 browser worker pilot](../../.github/workflows/web09-worker-smoke.yml),
manually dispatch `target=web13` on that SHA for:

| Engine | Required review evidence |
| --- | --- |
| Chromium | successful run URL, job summary, short-lived review artifact ZIP |
| Firefox | successful run URL, job summary, short-lived review artifact ZIP |
| Linux WebKit | successful run URL, job summary, short-lived review artifact ZIP |

Each successful run should generate a sanitized ZIP artifact retained for
three days. Download it before expiry. Do not keep raw runner evidence or
customer data in the public repository.

Example after checking out the exact candidate SHA:

```bash
python tools/release_candidate_matrix.py \
  --receipt chromium=/secure-review/chromium.zip \
  --run-url chromium=https://github.com/Solid-soup/opensource/actions/runs/CHROMIUM_ID \
  --receipt firefox=/secure-review/firefox.zip \
  --run-url firefox=https://github.com/Solid-soup/opensource/actions/runs/FIREFOX_ID \
  --receipt webkit=/secure-review/webkit.zip \
  --run-url webkit=https://github.com/Solid-soup/opensource/actions/runs/WEBKIT_ID \
  --require-browser-matrix > /secure-review/rc-matrix.json
```

The run IDs above are **placeholders**; only real run URLs and downloaded
artifacts are admissible. The matrix checks commit, browser, receipt schema
and run ID against the URL; it cannot independently confirm GitHub-hosted
run outcomes. A reviewer must inspect each actual workflow run, installed
browser and runtime network behavior. A Linux WebKit test is not a claim
about mobile Safari.

## Additional Workbench gates
Record a named reviewer and result for each item; leave unverified items open.

- Runtime dependency provenance and untrusted wheel/hash error paths.
- Third-party licensing, security advisory status and source integrity.
- Local data handling, browser storage, network egress and privacy checks.
- Keyboard access, screen reader semantics and meaningful error messages.
- Resource bounds, cancellation and large-file behavior.
- Incident response, deployment boundary and rollback plan.

These are not automatically satisfied by the synthetic browser smoke.
Production data import remains blocked unless separately approved.

## Package release gates (independent)
- G1: verify legal chain of title and Solid Soup AB's executed asset schedule.
- G2: ensure Apache-2.0 is correctly packaged without modifying previous grants.
- G3: obtain human review confirming the private IP boundary.
- G4: review dependency inventory and licence compatibility.
- G5: link CI/Security against the **exact** frozen release commit.
- G6: check documentation, limitations and dated release notes.
- G7/D6: obtain explicit authorized owner decision for the exact package
  version, distribution channel and release commit.

No script may infer approval. Keep any signed IP documents in private
company-controlled storage, not in this repository or CI artifacts.

## Change history
- 2026-11-05: RC-04 reconciled RC-01 documentation with RC-02/03 and the
  reported signed IP assignment; defined freeze/handoff and remaining
  manual gates. No runtime, licence, version, workflow trigger or access
  control change.
