# Release checklist (template)

Copy this into the description of the release pull request for a package and
fill it in. It complements `RELEASE_GATES.md`: the gates say *what* must be
true; this list says *how* to show it and what to change. Nothing here
publishes a package. Publishing is a separate, explicitly approved step (G7).

**Package:** `energydata-kit` · **Version:** `X.Y.Z` · **Release PR:** #…

## Human gates (from `RELEASE_GATES.md`)

- [ ] **G1 Ownership confirmed.** Link to written confirmation: …
- [ ] **G2 License chosen.** Legal sign-off: … · LICENSE PR merged: #…
- [ ] **G3 IP boundary review.** Reviewer and signed note: …
- [ ] **G4 Third-party licenses.** `THIRD_PARTY_LICENSES.md` refreshed with
      `python tools/check_third_party.py --report` and confirmed by legal;
      runtime table below filled in; duplication register up to date.
- [ ] **G5 CI green** on the release commit. CI run: …
- [ ] **G6 Documentation honest.** README capabilities and limitations
      reviewed; CHANGELOG section complete.
- [ ] **G7 Publication approved.** Written approval naming package, version
      and index: …

## Changes in the release PR

- [ ] `__version__` set to `X.Y.Z` (no `.devN`).
- [ ] `CHANGELOG.md`: `## [Unreleased]` content moved under
      `## [X.Y.Z] - YYYY-MM-DD`; a fresh empty `## [Unreleased]` above it.
- [ ] `pyproject.toml`: `license = "<SPDX id>"` declared; `license-files`
      includes the LICENSE if needed.
- [ ] `pyproject.toml`: classifier `Private :: Do Not Upload` removed (only
      after G7).
- [ ] `python tools/check_release_readiness.py energydata-kit --strict` passes
      locally.

## After merge

- [ ] Tag the merge commit `energydata-kit-vX.Y.Z` (annotated, signed if
      possible). The *Release build* workflow then re-runs the strict
      readiness check against the tag, builds and `twine check`s the files,
      and records a build provenance attestation.
- [ ] Compare the SHA-256 digests in the workflow summary with a local
      `python -m build` from the same commit.
- [ ] Publishing to an index is **not** automated. If G7 approved it, set up
      trusted publishing in a separate, reviewed change.

## Runtime dependency licenses (G4)

| Dependency | Version range | License |
|---|---|---|
| numpy | | |
| pandas | | |
| pint | | |
| pandera (optional extra) | | |
