# Security policy

## Reporting a vulnerability or leak

**Do not open a public issue or pull request.** This repository is public.

- Use GitHub's private vulnerability reporting for this repository
  (*Security → Report a vulnerability*), or contact the repository owner
  directly through their GitHub profile.
- Include the affected version or commit, the steps to reproduce, and the
  impact as you understand it. Reproduce with synthetic data (for example
  `energydata_kit.make_synthetic_series`); never attach real meter, customer
  or site data, or a live credential.

We aim to acknowledge reports within five working days.

## What to report here

- Vulnerabilities in the packages, for example input that makes
  `energydata-kit report` read or write files other than those named on the
  command line, or exhaust memory far out of proportion to the input size.
- Weaknesses in CI or the release process: workflow permissions, unpinned
  actions, or anything that could alter what a release build contains.
- Leaks: credentials, private Solid Soup / MICA code or data, customer or site
  data, or any other breach of the [IP boundary](docs/governance/IP_BOUNDARY.md).

Not security issues: wrong quality flags or report contents (open a normal
issue with the bug report template), and known vulnerabilities in a
dependency (report them to that project; `pip-audit` in CI tracks published
advisories).

## How reports are handled

1. Acknowledge the report and agree on how to stay in touch.
2. Reproduce and assess it; tell the reporter whether it is accepted.
3. Prepare the fix privately (a GitHub security advisory and its temporary
   private fork), with tests, through the usual review and CI.
4. Publish the fix and the advisory together, crediting the reporter unless
   they prefer otherwise.

## If a secret or private data was committed

1. **Revoke and rotate a secret right away.** Assume it was copied: pushes to
   a public repository are visible at once, and forks, clones and caches keep
   it even after history is rewritten.
2. Then notify the owner privately, as above.
3. Removing it from history (rewriting `main`, asking GitHub to purge cached
   views) is decided by the owner. It limits further spread; it does not undo
   exposure.

## Supported versions

| Version | Security fixes |
|---|---|
| `main` | Yes |
| 0.1.0 | Not released yet ([release gates](docs/governance/RELEASE_GATES.md)) |

No version has been released, so fixes go to `main`. The support policy for
released versions (for example, fixes only in the latest 0.x release) is to be
set with the first release; until then nothing here promises patches for a
particular version.

## How the package limits exposure

- The package code makes no network requests, does not unpickle data and does
  not execute code from input files. The command line reads the CSV or JSON
  files it is given and writes only the outputs named with `-o` and
  `--flags-csv`.
- Runtime dependencies are limited to an allowlist (`tools/ip_boundary.toml`),
  checked in CI with their licences (`tools/check_third_party.py`).

## Automated controls

Secret scanning (gitleaks), dependency audit (pip-audit), GitHub dependency
review and Dependabot run in CI; see `.github/workflows/security.yml`. All
GitHub Actions are pinned to commit SHAs and checked by
`tools/check_workflow_pins.py`. Release builds from a tag record a build provenance
attestation (`.github/workflows/release-build.yml`); nothing is uploaded to a
package index.
