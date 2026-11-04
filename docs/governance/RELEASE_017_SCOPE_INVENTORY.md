# 0.17.0 — release scope versus Workbench scope

**Internal working draft. No release or publication approval.**

## REPO/REPOS
- `Solid-soup/opensource`

## Baseline and observed change
The last documented GitHub release is `energydata-kit-v0.16.0`.
A GitHub compare against `main`, inspected on 2026-11-04, showed
276 commits and extensive Workbench, testing, CI and documentation changes,
but no changed Python implementation file beyond
`src/energydata_kit/__init__.py`. The latter **must be diff-reviewed**:
path classification alone cannot establish that it only changes the
version string. Package metadata and README also changed.

Do not advertise WEB-09–WEB-20 as newly shipped Python library APIs or
as an independently verified Workbench release. The currently developed
`energydata-kit 0.17.0.dev0` still carries the
`Private :: Do Not Upload` guard.

## Reproducible scope report

```bash
git fetch --tags
python tools/release_scope_report.py \
  --base energydata-kit-v0.16.0 --head HEAD > release-scope-local.json
python tools/release_status_report.py > release-readiness-local.json
```

The first command requires local git history and returns an error instead
of claiming an empty diff when the tag is unavailable. The JSON contains
deduplicated changed-file lists split between Python package, Workbench
and other repository code. It does not inspect binary content or sign
ownership/IP findings, and it never grants publication approval.

## Decision required before 0.17.0
- Review the exact source diff, especially `__init__.py` and dependency
  metadata, and establish which **package-specific changes** justify 0.17.0.
- If the changes are only version, packaging or documentation, explicitly
  decide whether to issue a package maintenance release or defer a new
  Python library version until new approved API changes exist.
- Independently verify browser-E2E for the Workbench, which remains
  synthetic-only and separate from any Python package release.
- Use the existing G1–G7 release gates and explicit version-scoped D6
  decision for any actual GitHub release.

## Change history
- 2026-11-04: Added read-only per-file release-scope comparison, conservative
  classifier, fail-closed missing-baseline behavior and synthetic offline
  regression tests. No release/guard changes.
