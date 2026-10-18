# Release gates

**Status:** draft for review

No package from this repository is published (PyPI or elsewhere), and no
open-source license is granted, until every gate below is signed off and
recorded in the release pull request. A gate is either passed or not; "mostly"
counts as not.

As a technical guard, `energydata-kit` carries the PyPI classifier
`Private :: Do Not Upload`, which PyPI rejects on upload. Removing it is part of
gate G7.

Supporting tooling (none of it publishes anything):

- `RELEASE_DECISIONS.md`: the open decisions for G1–G3 and G7, the
  evidence already in the repository and the questions to answer.
- `RELEASE_CHECKLIST.md`: template for the release pull request.
- `tools/check_release_readiness.py`: reports the mechanical conditions (final
  version, dated changelog section, LICENSE at the root and shipped with the
  package, declared license, guard removed, tag matching version); `--strict`
  fails if any is unmet.
- `tools/release_dry_run.py`: rehearses the release PR edits in a temporary
  copy with a placeholder licence, runs the strict readiness check and (with
  `--build`) builds, `twine check`s and inspects the files. Runs in CI on every
  change; it never changes the repository and never uploads.
- `THIRD_PARTY_LICENSES.md`: licence table for every dependency (evidence
  for G4), kept in sync with `pyproject.toml` by
  `tools/check_third_party.py` in CI.
- `.github/workflows/release-build.yml`: builds and `twine check`s the release
  files on demand; for an `energydata-kit-v*` tag it first requires the strict
  readiness check and then records a build provenance attestation.

## Gates

| # | Gate | Evidence required | Owner |
|---|---|---|---|
| G1 | **Ownership confirmed.** The publishing legal entity owns all contributed code (employment / contractor agreements cover it). | Written confirmation from management / counsel | Management |
| G2 | **License chosen — PASSED 2026-10-18.** Apache-2.0, granted by owner decision. `LICENSE` at the repository root and a byte-identical copy in `packages/energydata-kit/`; `license = "Apache-2.0"` and `license-files` in the package `pyproject.toml`. No `NOTICE` — per D3, none is required because no third-party code is copied into the repository. Verified in the built artifacts, not just the gate: the wheel carries `License-Expression: Apache-2.0` and ships `dist-info/licenses/LICENSE`, and the sdist ships `LICENSE`, both byte-identical to the root file. | Owner decision 2026-10-18; LICENSE PR | Legal |
| G3 | **IP boundary review.** A maintainer who knows the private codebase confirms that the release contains no proprietary code, data or algorithms (see `IP_BOUNDARY.md`). | Signed review note in the release PR | Technical lead |
| G4 | **Third-party licenses.** All runtime dependencies have licenses compatible with the chosen project license. Any copied code is credited and recorded in the duplication register. | Dependency license table in the release PR | Maintainer |
| G5 | **CI green.** Lint, type check, tests on all supported Python versions (including lowest supported dependency versions), packaging test, IP-boundary check, secret scan and dependency audit all pass on the release commit. | Link to CI run | Maintainer |
| G6 | **Documentation honest.** The README states only verified capabilities and lists known limitations; `CHANGELOG` entry exists. | Review | Maintainer |
| G7 | **Publication approved.** Explicit approval to publish, naming the package, version and index. Only then remove `Private :: Do Not Upload` and set up trusted publishing. | Written approval | Management |

## Repository visibility

Making this repository public was supposed to be a gated step. **The GitHub
repository is already public** (observed 2026-10-15). Until G1 to G3 are
passed, the owners should decide whether to:

- make the repository private until the gates are passed, or
- keep it public and accept that all branches are visible now.

**Updated 2026-10-18.** The second limb of that trade-off has changed: there is
now a `LICENSE` (Apache-2.0, G2), so the repository is no longer public under an
implied "all rights reserved" with no terms for a reader at all. The visibility
decision itself still needs an owner, because G1 (ownership) and G3 (IP boundary
review) are not passed — a granted licence is not a substitute for either. It is
not made by this document.

## Versioning

- Semantic Versioning. While in `0.x`, minor versions may break the API.
- `QualityFlag` bit values and the report `schema_version` are compatibility
  contracts: changing them requires a major version bump (or a minor bump in
  `0.x`) and a changelog entry.
