# Release decisions for energydata-kit 0.1.0

**Status:** prepared 2026-10-16 (OSS-22), facts refreshed 2026-10-17
(OSS-48) · **For:** management, legal counsel
and the technical lead who sign off the release gates in `RELEASE_GATES.md`.

This page collects every decision that still blocks the first release, the
evidence already in the repository for each, and the exact questions to
answer. It does not make any of these decisions. Engineering work for 0.1.0
is complete; nothing below needs more code before the decisions are made.
Since the first version of this page, five correctness passes (OSS-40 to
OSS-47) fixed the bugs they found, and the changelog's `[Unreleased]`
section has been folded into the 0.1.0 notes, so the only failing
readiness checks are the ones these decisions resolve (LICENSE, licence
declaration, upload guard).

## Where things stand

| Gate | State | Evidence in the repository |
|---|---|---|
| G1 Ownership | **Open: decision needed** | See D2 below |
| G2 Licence | **Open: decision needed** | See D3 below |
| G3 IP boundary review | **Open: review needed** | See D4 below |
| G4 Third-party licences | Evidence ready; needs legal confirmation | `THIRD_PARTY_LICENSES.md`, kept in sync by `tools/check_third_party.py` in CI |
| G5 CI green | Green on `main`; re-checked on the release commit | `.github/workflows/ci.yml`, `security.yml` |
| G6 Documentation honest | Reviewed in OSS-20 and OSS-45; re-checked in the release PR | Package `README.md` (capabilities and known limitations), `CHANGELOG.md`, `examples/GUIDE.md` (executed by the tests) |
| G7 Publication | **Open: decision needed** | See D6 below |

The mechanical release steps are rehearsed on every change by the *Release
dry run* CI job (`tools/release_dry_run.py`), with a placeholder licence. The
real release PR will therefore only differ by the decisions recorded here.

## Decisions

### D1. Repository visibility (owner: management)

The GitHub repository is **public** (observed 2026-10-15), so every pushed
commit and branch is already visible. Without a LICENSE file the default is
"all rights reserved": people may read the code but not reuse it.

- **Question:** keep the repository public while G1–G3 are open, or make it
  private until they pass?
- **If private:** nothing else changes; CI keeps running. Making it public
  again later is part of G7.
- **If public:** record the decision here; no change needed.

### D2. Ownership, G1 (owner: management, with counsel)

- **Question:** does the publishing legal entity own all code in the
  repository, so that it can license it?
- **Facts for the answer** (from `git log` on `main` at `0b5be89`, after #53,
  2026-10-17): 125 commits.
  - 63 by an AI coding assistant (author "Claude", with a `Co-Authored-By`
    trailer) in sessions run by the repository owner: 55 contain the code,
    docs and roadmap updates, 8 merge `main` into a pull-request branch.
  - 58 by the repository owner: 52 pull-request merges, 4 merges of `main`
    into a pull-request branch, and 2 own commits (the initial commit and a
    roadmap note).
  - 4 Dependabot updates of pinned GitHub Actions.
  - No external contributor has committed.

  The counts grow with every pull request; the categories have not changed.
  To recount: `git log --format='%an %s' main`.
- **Ask counsel to confirm** how employment terms and AI-assisted authorship
  affect ownership and the ability to license, and whether future external
  contributions need a contributor agreement or a Developer Certificate of
  Origin sign-off.
- **Evidence to record:** written confirmation, linked from the release PR.

### D3. Licence, G2 (owner: legal) — DECIDED 2026-10-18

**Apache-2.0, granted by owner decision on 2026-10-18.** Answers to the three
questions below, in order: (1) Apache-2.0; (2) `Copyright 2026 Mica AB`, the
entity already used across the portfolio's other repositories; (3) no `NOTICE`,
for the reason this section already gave. The licence-only scope was explicit:
publication was **not** authorised, so G7's `Private :: Do Not Upload`
classifier stays in place.

What landed, exactly as the "After the decision" paragraph below specifies:
`LICENSE` at the repository root, a byte-identical copy in
`packages/energydata-kit/`, and `license = "Apache-2.0"` plus
`license-files = ["LICENSE"]` in the package `pyproject.toml` (the build-system
floor moved to `hatchling>=1.27`, the first version with PEP 639 support for
that SPDX form). Verified by building rather than by inspection: the wheel
reports `License-Expression: Apache-2.0` and ships
`dist-info/licenses/LICENSE`, the sdist ships `LICENSE`, both byte-identical to
the root file, and `Private :: Do Not Upload` is still in the wheel metadata.

**Still open, and not resolved by this decision:** D2/G1 ownership — counsel on
how employment terms and AI-assisted authorship affect the ability to license,
and whether external contributions need a CLA or DCO. A licence grant is not
an ownership opinion.

Apache-2.0 is the preferred candidate. `THIRD_PARTY_LICENSES.md` assumes it
and found no conflict: every shipped dependency is permissively licensed.

- **Questions:**
  1. Apache-2.0, or another permissive licence (MIT, BSD-3-Clause)?
  2. The copyright line, e.g. `Copyright 2026 <legal entity>`.
  3. Is a `NOTICE` file wanted? Apache-2.0 requires one only if the project
     chooses to have it; no third-party code is copied into the repository
     (see `DUPLICATION_REGISTER.md`), so none is needed for attribution.
- **After the decision:** one PR adds the licence text as `LICENSE` at the
  repository root **and** an identical copy in `packages/energydata-kit/`
  (the build only ships licence files from inside the package directory;
  found by the release dry run), plus `license = "<SPDX id>"` in
  `pyproject.toml`. `tools/check_release_readiness.py` then passes those
  three checks.

### D4. IP boundary review, G3 (owner: technical lead)

A person who knows the private Solid Soup / MICA codebase confirms that the
release contains no proprietary code, data, parameters or algorithms.

- **Evidence to start from:**
  - `IP_BOUNDARY.md`: the rules and the out-of-scope list.
  - `tools/check_ip_boundary.py` in CI: forbidden imports, dependency
    allowlist, no direct or VCS dependencies.
  - `docs/architecture/EXISTING_TOOLS_AUDIT.md`: two private repositories
    were reviewed read-only (names withheld); nothing was used as a source.
  - `docs/architecture/DUPLICATION_REGISTER.md`: no code copied from any
    project; similar public tools are named where behaviour overlaps.
  - Test data is synthetic (`energydata_kit.synthetic` and inline values).
- **Questions for the reviewer:**
  1. Does any module reproduce private code, structure or algorithms?
  2. Do any defaults, thresholds, fixtures or examples come from customer
     or internal data? (The package ships no domain limits: bounds, run
     lengths and jump limits are always supplied by the caller.)
  3. Is anything in the out-of-scope list (forecasting, grid calculations,
     ratings, optimization, connection planning) present?
- **Evidence to record:** a signed review note in the release PR.

### D5. Branch protection on `main` (owner: repository admin)

Not a release gate, but it protects the release commit.

- **Suggested settings:** require a pull request; require the CI checks
  *IP boundary*, the *energydata-kit* test jobs, *energydata-kit packaging*,
  *Release dry run*, *Secret scan (gitleaks)*, *Dependency audit
  (pip-audit)* and *Dependency review*; require code-owner review
  (`.github/CODEOWNERS`); block force pushes.

### D6. Publication, G7 (owner: management)

- **Questions:**
  1. Publish to PyPI, or keep releases as GitHub-only build artifacts?
  2. Confirm the name `energydata-kit`. On 2026-10-16 (OSS-22, OSS-36) and
     again on 2026-10-17 (OSS-48) the names `energydata-kit` and
     `energydata_kit` were not taken on PyPI or TestPyPI (HTTP 404 from
     their JSON APIs); availability can change until the first upload.
  3. Who owns the PyPI project and its trusted-publishing configuration?
- **After approval:** the release PR removes the `Private :: Do Not Upload`
  classifier; trusted publishing is set up in a separate, reviewed change.
  Nothing in the repository uploads anything today.

## Suggested order

1. D1 visibility (it affects how the other steps are handled in public).
2. D2 ownership, then D3 licence; they usually go to counsel together.
3. D4 IP review, on the commit intended for release.
4. D5 branch protection, any time before the release PR.
5. D6 publication approval.
6. Release PR from `RELEASE_CHECKLIST.md`. `main` already has version
   `0.1.0` and a dated `## [0.1.0]` changelog section (OSS-24, #30; nothing
   is released; `[Unreleased]` is empty since OSS-48). The release PR folds
   in anything added there since, sets the section's date to the release day, adds LICENSE (root and
   package) and the licence declaration, and removes the guard;
   then tag `energydata-kit-v0.1.0`. The *Release build* workflow re-runs the
   strict readiness check on the tag and records build provenance.

## Not decided here

- Proposed work parked in `ROADMAP.md` until after these gates.
- Version numbers after 0.1.0 and the support policy for old pandas releases.
