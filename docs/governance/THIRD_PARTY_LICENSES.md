# Third-party licences

Evidence for release gate **G4** (see `RELEASE_GATES.md`). This page records
the licences of every package energydata-kit depends on. It does **not**
choose a licence for energydata-kit; that is gate G2. The compatibility notes
assume the preferred candidate, Apache-2.0, and need legal confirmation.

The energydata-kit wheel contains only its own code. Dependencies are
installed separately by the user's package installer; nothing third-party is
copied into the repository or the release files (see the duplication
register).

## Direct dependencies of `energydata-kit`

Every dependency declared in `packages/energydata-kit/pyproject.toml` must
have exactly one row here, with matching scopes. `tools/check_third_party.py`
enforces this in CI. Scopes: `runtime` (installed with the package),
`extra:pandera` (optional extra), `dev` (dependency group for contributors),
`build` (build backend).

| Package | Scopes | Licence (SPDX) | Shipped to users | Source of licence information |
|---|---|---|---|---|
| `numpy` | runtime | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Installed as a dependency | `License-Expression` metadata (2.x wheels, including bundled libraries); 1.26 declares BSD |
| `pandas` | runtime | BSD-3-Clause | Installed as a dependency | `License` metadata and classifier |
| `pint` | runtime | BSD-3-Clause | Installed as a dependency | LICENSE file (three-clause BSD text); metadata says only "BSD" |
| `pandera` | extra:pandera, dev | MIT | Only with the `[pandera]` extra | `License` metadata and classifier |
| `hatchling` | build | MIT | No (build backend only) | `License-Expression` on PyPI |
| `build` | dev | MIT | No | `License-Expression` metadata |
| `hypothesis` | dev | MPL-2.0 | No | `License-Expression` metadata |
| `mypy` | dev | MIT | No | `License-Expression` metadata |
| `pandas-stubs` | dev | BSD-3-Clause | No | `License-Expression` metadata |
| `pytest` | dev | MIT | No | `License-Expression` metadata |
| `ruff` | dev | MIT | No | `License-Expression` metadata |

## Dependencies of runtime dependencies

Installed automatically with numpy, pandas and Pint. Taken from the package
metadata in two test environments on 2026-10-15: Python 3.13 with pandas
3.0.6, numpy 2.5.4 and Pint 0.26.1, and Python 3.11 with the lowest supported
versions (pandas 2.1.4, numpy 1.26.4, Pint 0.24.4). Which of these are
installed depends on the versions and platform. To refresh both tables, run
`python tools/check_third_party.py --report` in an environment where the
package is installed; it lists every installed runtime dependency, direct and
indirect, with the licence its metadata declares.

| Package | Required by | Licence (SPDX) | Notes |
|---|---|---|---|
| `python-dateutil` | pandas | Apache-2.0 OR BSD-3-Clause | Dual licensed |
| `six` | python-dateutil | MIT | |
| `pytz` | pandas 2.x | MIT | Not required by pandas 3 |
| `tzdata` | pandas 2.x; pandas 3 on Windows and Emscripten | Apache-2.0 | IANA time-zone data packaged for Python |
| `flexcache` | pint | BSD-3-Clause | |
| `flexparser` | pint | BSD-3-Clause | |
| `platformdirs` | pint | MIT | |
| `typing_extensions` | pint | PSF-2.0 | |

With the `[pandera]` extra, these are added:

| Package | Required by | Licence (SPDX) |
|---|---|---|
| `pydantic`, `pydantic_core` | pandera | MIT |
| `annotated-types`, `typing-inspection` | pydantic | MIT |
| `typeguard` | pandera | MIT |
| `typing-inspect` | pandera | MIT |
| `mypy_extensions` | typing-inspect | MIT |
| `packaging` | pandera | Apache-2.0 OR BSD-2-Clause |

## Assessment (for legal review)

- **Runtime and optional dependencies** are all under permissive licences
  (BSD, MIT, PSF-2.0, Apache-2.0, 0BSD, Zlib, CC0-1.0, or a choice that
  includes one of them). None is copyleft. Using them unmodified from an
  Apache-2.0 package raises no known compatibility problem.
- **hypothesis (MPL-2.0)** is a dev-only test tool. It is not a dependency of
  the published package, and no Hypothesis code is copied into this
  repository, so MPL-2.0's file-level conditions are not triggered.
- **CI tools** (gitleaks, pip-audit, twine and the GitHub Actions in
  `.github/workflows`) run only in CI and are not dependencies of the
  package.
- **Copied code:** none. Any future copy must be credited and recorded in
  `docs/architecture/DUPLICATION_REGISTER.md`.

Package metadata is self-declared. Before the release, legal review should
confirm the runtime rows against each project's LICENSE file, starting with
packages whose metadata is vague (e.g. Pint's "BSD").
