# Release checklist (template)

Copy this into the description of the release pull request for a package and
fill it in. It complements `RELEASE_GATES.md`: the gates say *what* must be
true; this list says *how* to show it and what to change. Nothing here
publishes a package. Publishing is a separate, explicitly approved step (G7).

**Package:** `energydata-kit` · **Version:** `X.Y.Z` · **Release PR:** #…

## Human gates (from `RELEASE_GATES.md`)

The questions and evidence for each open gate are in `RELEASE_DECISIONS.md`.

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
- [ ] Changelog date set to the day the release PR merges (`main` may carry
      the dated section early, with an earlier date).
- [ ] Anything under `## [Unreleased]` folded into the `X.Y.Z` section
      (checked by *nothing left unreleased*).
- [ ] `LICENSE` (and `NOTICE` if required) at the repository root **and an
      identical copy in `packages/energydata-kit/`**: the build backend only
      ships licence files from inside the package directory.
- [ ] `pyproject.toml`: `license = "<SPDX id>"` declared.
- [ ] `pyproject.toml`: classifier `Private :: Do Not Upload` removed (only
      after G7), in the same PR as the owner's approval line in
      `RELEASE_DECISIONS.md` (`**D6 approved:** YYYY-MM-DD ...` on a line of
      its own); without it CI fails (`check_release_readiness.py --guard`).
- [ ] `python tools/check_release_readiness.py energydata-kit --strict` passes
      locally.
- [ ] Before opening the PR, `python tools/release_dry_run.py energydata-kit --build`
      passed on `main` (CI runs it on every change).

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
| pyarrow (optional extra `[parquet]`) | | |
