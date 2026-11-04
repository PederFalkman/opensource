# EnergyData Kit 0.17.0 — release preparation status

**Internal working draft. No decision to publish 0.17.0 is recorded here.**

## REPO/REPOS
- `Solid-soup/opensource`

## Scope
The project has earlier recorded GitHub-only releases. The repository is
currently developing `energydata-kit` 0.17.0.dev0 with the
`Private :: Do Not Upload` classifier in place. Open-source repository
visibility is not equivalent to approval to publish a new package release.

## Reproducible local readiness report
From repository root:

```bash
python tools/release_status_report.py > release-readiness-local.json
python tools/release_status_report.py --strict
python tools/check_release_readiness.py energydata-kit --strict
```

The first command is **read-only**, generates no release, never approves
publication and reports mechanical checks plus seven explicitly unresolved
human-review gates. `--strict` fails while any mechanical gate remains
unsatisfied. The local output is an internal review artifact, **not a signed
provenance attestation**. Do not commit customer data or secrets to it.

## Required release sequence
1. Establish the exact `0.17.0` release scope and freeze the release diff.
2. Verify ownership and IP review of **this** release, third-party licence
   evidence and honest documentation. Record actual owner decisions; do not
   copy earlier release approvals as if they covered 0.17.0.
3. Prepare the release PR: final version, dated changelog, explicit D6
   owner approval for `energydata-kit 0.17.0`, and only then remove upload
   guard in the same reviewed PR.
4. Run strict readiness, all required CI/security jobs and packaging
   checks on the exact release commit.
5. Apply the expected release tag, build a draft GitHub release, and publish
   only when the owner explicitly authorizes that release. No PyPI upload
   is implied.

## Workbench is a separate decision
The experimental synthetic-only Workbench and local CSV preflight do not
authorize user CSV execution. Browser E2E, signed provenance, runtime
dependencies, security/privacy and accessibility review remain independent.

## Change history
- 2026-11-04: Added machine-readable, read-only release preparation report
  and offline regression tests. Publication guard remains intact.
