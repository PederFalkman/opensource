# Release decisions for energydata-kit

## 0.13.0 (released 2026-10-24)

**Status:** decided 2026-10-24. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-24 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-200) sets the version to
`0.13.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.13.0 under D6 further down. The 0.12.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.13.0, as recorded by the repository owner on 2026-10-24:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.12.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.12.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.12.0; no
  package index.

**Since the preparation** (`d8ae7ca` to the release PR's base `a023469`):
only OSS-199 (#171, docs). Nothing touched the package code or
`pyproject.toml`.

**What 0.13.0 contains** (P-41 and P-42 approved by the owner on
2026-10-23; proposals in `docs/architecture/ROADMAP.md`, OSS-196):

- `compare --fail-on-changed-metadata` exits with status 1 when the two
  reports describe the data differently, for example another unit
  (P-41, OSS-197, #169). Before, a changed unit was listed and the
  command exited 0 with every `compare` option.
- When `--timestamp-col`, `--time-col` or `--value-col` is not found but
  one column matches it once surrounding spaces are removed, the error
  names that column (P-42, OSS-198, #170). The command still exits 2.
- No report- or comparison-format change (schema 2), no new or renamed
  public Python name, nothing removed. Commands that worked with 0.12.0
  give the same output and exit status; only the text of one error
  message gains a hint. The changelog's `[Unreleased]` section has the
  release notes.

**What did not change since 0.12.0** (`git diff 4c7bd98` on
`pyproject.toml`, 2026-10-24): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-195). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.13.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-24**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.12.0. Commits since the 0.12.0 release commit (`4c7bd98`), on `main` at `d8ae7ca`: 10, of which 6 by the AI coding assistant in the owner's sessions (5 with changes, 1 a merge of `main` into a branch) and 4 by the owner (pull-request merges #167 to #170); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-24**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.13.0 PR. P-41 lets `compare`'s exit status follow the metadata changes it already lists; P-42 adds a hint to an error message | — |
| G4 Third-party licences | **Passed 2026-10-24**: the 0.12.0 position stands; unchanged since 0.12.0 (no dependency change) | — |
| G5 CI green | Green on every 0.13.0 PR and on `main`; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and help text updated with each step; both changes are covered by tests on the lowest and current pandas | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-24**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.12.0 release commit to the 0.13.0 release commit:
`git diff 4c7bd98 <release commit> -- packages/energydata-kit/src`
(2 files, about 30 added lines: `cli.py` and the version in
`__init__.py`). Points to confirm, each also checked by a tool:

- No new import: besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: P-41 compares two saved reports' metadata; P-42
  compares column names. No number is introduced.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes set `compare`'s exit status from differences it
  already reports and add a hint to an error message.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.13.0`, moves `[Unreleased]` under a dated
`## [0.13.0]` heading, records the answers under G1, G3 and G4, and adds
the owner's D6 line naming `energydata-kit 0.13.0`; only with that line
does it remove the upload guard. It passes `check_release_readiness.py
--strict`. The owner then tags the merged commit `energydata-kit-v0.13.0`,
the *Release build* workflow prepares the draft GitHub release, and the
owner publishes it. The release PR is OSS-200.

## 0.12.0 (released 2026-10-23)

**Status:** decided 2026-10-23. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-23 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-194) sets the version to
`0.12.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.12.0 under D6 further down. The 0.11.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.12.0, as recorded by the repository owner on 2026-10-23:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.11.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.11.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.11.0; no
  package index.

**Since the preparation** (`4f16d34` to the release PR's base `c44bea7`):
only OSS-193 (#165, docs). Nothing touched the package code or
`pyproject.toml`.

**What 0.12.0 contains** (P-39 and P-40 approved by the owner on
2026-10-23; proposals in `docs/architecture/ROADMAP.md`, OSS-190):

- `compare --fail-on-removed-columns` exits with status 1 when a column of
  the earlier report is missing from the later one (P-39, OSS-191, #163).
  Before, a removed column was listed and the command exited 0, even with
  `--fail-if-worse`.
- `compare --fail-on-changed-parameters` exits with status 1 when the two
  reports were made with different parameters (P-40, OSS-192, #164).
  Before, a changed step could read as a completeness improvement and
  exit 0 with `--fail-if-worse`.
- No report- or comparison-format change (schema 2), no new or renamed
  public Python name, nothing removed, and no change to the output or exit
  status of commands that worked with 0.11.0. The changelog's
  `[Unreleased]` section has the release notes.

**What did not change since 0.11.0** (`git diff 29bf8ee` on
`pyproject.toml`, 2026-10-23): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-189). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.12.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-23**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.11.0. Commits since the 0.11.0 release commit (`29bf8ee`), on `main` at `4f16d34`: 10, of which 6 by the AI coding assistant in the owner's sessions (5 with changes, 1 a merge of `main` into a branch) and 4 by the owner (pull-request merges #161 to #164); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-23**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.12.0 PR. P-39 and P-40 let `compare`'s exit status follow the removed columns and changed parameters the comparison already lists | — |
| G4 Third-party licences | **Passed 2026-10-23**: the 0.11.0 position stands; unchanged since 0.11.0 (no dependency change) | — |
| G5 CI green | Green on every 0.12.0 PR and on `main`; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and help text updated with each step; both options are covered by tests on the lowest and current pandas | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-23**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.11.0 release commit to the 0.12.0 release commit:
`git diff 29bf8ee <release commit> -- packages/energydata-kit/src`
(2 files, about 25 added lines: `cli.py` and the version in
`__init__.py`). Points to confirm, each also checked by a tool:

- No new import: besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: both options compare two saved reports' column
  lists and parameters; no number is introduced.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes set `compare`'s exit status from differences it
  already reports.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.12.0`, moves `[Unreleased]` under a dated
`## [0.12.0]` heading, records the answers under G1, G3 and G4, and adds
the owner's D6 line naming `energydata-kit 0.12.0`; only with that line
does it remove the upload guard. It passes `check_release_readiness.py
--strict`. The owner then tags the merged commit `energydata-kit-v0.12.0`,
the *Release build* workflow prepares the draft GitHub release, and the
owner publishes it. The release PR is OSS-194.

## 0.11.0 (released 2026-10-23)

**Status:** decided 2026-10-23. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-23 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-188) sets the version to
`0.11.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.11.0 under D6 further down. The 0.10.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.11.0, as recorded by the repository owner on 2026-10-23:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.10.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.10.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.10.0; no
  package index.

**Since the preparation** (`79a01b1` to the release PR's base `8ba8c40`):
only OSS-187 (#159, docs). Nothing touched the package code or
`pyproject.toml`.

**What 0.11.0 contains** (P-37 and P-38 approved by the owner on
2026-10-23; proposals in `docs/architecture/ROADMAP.md`, OSS-184):

- `report --fail-on metadata` exits with status 1 when the report lists
  metadata issues (P-37, OSS-185, #157). Before, an inconsistent
  description such as `SUM_OF_POWER` was printed and the command exited
  0, even with `--fail-on-issues`.
- `report --all-value-cols` assesses every column except the timestamps,
  giving the same report as one `--value-col` per column (P-38, OSS-186,
  #158). Before, each column had to be named, and a column added to an
  export later was silently not assessed.
- No report- or comparison-format change (schema 2), no new or renamed
  public Python name, nothing removed, and no change to the output or exit
  status of commands that worked with 0.10.0. The changelog's
  `[Unreleased]` section has the release notes.

**What did not change since 0.10.0** (`git diff c1be62d` on
`pyproject.toml`, 2026-10-23): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-183). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.11.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-23**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.10.0. Commits since the 0.10.0 release commit (`c1be62d`), on `main` at `79a01b1`: 8, of which 4 by the AI coding assistant in the owner's sessions (all with changes) and 4 by the owner (pull-request merges #155 to #158); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-23**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.11.0 PR. P-37 lets the exit status follow the existing metadata checks; P-38 chooses which input columns the existing checks run on | — |
| G4 Third-party licences | **Passed 2026-10-23**: the 0.10.0 position stands; unchanged since 0.10.0 (no dependency change) | — |
| G5 CI green | Green on every 0.11.0 PR and on `main`; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and help text updated with each step; both options are covered by tests on the lowest and current pandas | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-23**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.10.0 release commit to the 0.11.0 release commit:
`git diff c1be62d <release commit> -- packages/energydata-kit/src`
(2 files, about 25 added lines: `cli.py` and the version in
`__init__.py`). Points to confirm, each also checked by a tool:

- No new import: besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: the metadata checks are unchanged generic
  unit/aggregation consistency checks, and no column is chosen or skipped
  by guessing.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes set the exit status from issues the report
  already lists and select which input columns are assessed.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.11.0`, moves `[Unreleased]` under a dated
`## [0.11.0]` heading, records the answers under G1, G3 and G4, and adds
the owner's D6 line naming `energydata-kit 0.11.0`; only with that line
does it remove the upload guard. It passes `check_release_readiness.py
--strict`. The owner then tags the merged commit `energydata-kit-v0.11.0`,
the *Release build* workflow prepares the draft GitHub release, and the
owner publishes it. The release PR is OSS-188.

## 0.10.0 (released 2026-10-23)

**Status:** decided 2026-10-23. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-23 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-182) sets the version to
`0.10.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.10.0 under D6 further down. The 0.9.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.10.0, as recorded by the repository owner on 2026-10-23:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.9.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.9.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.9.0; no
  package index.

**Since the preparation** (`76b58d1` to the release PR's base `cf72bde`):
only OSS-181 (#153, docs). Nothing touched the package code or
`pyproject.toml`.

**What 0.10.0 contains** (P-35 and P-36 approved by the owner on
2026-10-23; proposals in `docs/architecture/ROADMAP.md`, OSS-178):

- `report --fail-on empty` exits with status 1 when the input has no data
  rows (P-35, OSS-179, #151). Before, an export that came back with only
  its header exited 0, even with `--fail-on-issues`.
- `report --min-completeness FRACTION` exits with status 1 when
  completeness is below the caller's fraction, without the known outages
  when they are given (P-36, OSS-180, #152). Before, `--fail-on gaps`
  was the only completeness-based failure, all or nothing. When
  completeness is not checked the option is refused (status 2) rather
  than passed.
- No report- or comparison-format change (schema 2), no new or renamed
  public Python name, nothing removed, and no change to the output or exit
  status of commands that worked with 0.9.0. The changelog's
  `[Unreleased]` section has the release notes.

**What did not change since 0.9.0** (`git diff e098747` on
`pyproject.toml`, 2026-10-23): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-177). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.10.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-23**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.9.0. Commits since the 0.9.0 release commit (`e098747`), on `main` at `76b58d1`: 8, of which 4 by the AI coding assistant in the owner's sessions (all with changes) and 4 by the owner (pull-request merges #149 to #152); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-23**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.10.0 PR. P-35 and P-36 change only when `report` exits with status 1, from numbers the report already has | — |
| G4 Third-party licences | **Passed 2026-10-23**: the 0.9.0 position stands; unchanged since 0.9.0 (no dependency change) | — |
| G5 CI green | Green on every 0.10.0 PR and on `main`; re-checked on the release commit | — |
| G6 Documentation honest | README, guide, changelog and help text updated with each step; both options are covered by tests on the lowest and current pandas | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-23**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.9.0 release commit to the 0.10.0 release commit:
`git diff e098747 <release commit> -- packages/energydata-kit/src`
(2 files, about 75 added lines: `cli.py` and the version in
`__init__.py`). Points to confirm, each also checked by a tool:

- No new import: besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: the completeness fraction is the caller's, with
  no default; the package suggests no value.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes compare the report's row count and completeness
  with what the caller asked for and set the exit status.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.10.0`, moves `[Unreleased]` under a dated
`## [0.10.0]` heading, records the answers under G1, G3 and G4, and adds
the owner's D6 line naming `energydata-kit 0.10.0`; only with that line
does it remove the upload guard. It passes `check_release_readiness.py
--strict`. The owner then tags the merged commit `energydata-kit-v0.10.0`,
the *Release build* workflow prepares the draft GitHub release, and the
owner publishes it. The release PR is OSS-182.

## 0.9.0 (released 2026-10-23)

**Status:** decided 2026-10-23. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-23 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-176) sets the version to
`0.9.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.9.0 under D6 further down. The 0.8.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.9.0, as recorded by the repository owner on 2026-10-23:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.8.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.8.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.8.0; no
  package index.

**Since the preparation** (`dcb8bb1` to the release PR's base `e8394fe`):
only OSS-175 (#147, docs). Nothing touched the package code or
`pyproject.toml`.

**What 0.9.0 contains** (P-34 and P-33 approved by the owner on
2026-10-23; proposals in `docs/architecture/ROADMAP.md`, OSS-172):

- `report --time-col COL` joins a separate time-of-day column with
  `--timestamp-col`, ISO forms only (P-34, OSS-173, #145). Before, the
  date column alone read every row of a day as one timestamp without an
  error.
- `report --thousands SEP` reads values with a thousands separator (P-33,
  OSS-174, #146). Before, such values were all flagged `NON_NUMERIC`.
- No report- or comparison-format change (schema 2), no new or renamed
  public Python name, nothing removed, and no change to the output of
  commands that worked with 0.8.0. The changelog's `[Unreleased]` section
  has the release notes.

**What did not change since 0.8.0** (`git diff 32411b5` on
`pyproject.toml`, 2026-10-23): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-171). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.9.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-23**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.8.0. Commits since the 0.8.0 release commit (`32411b5`), on `main` at `dcb8bb1`: 8, of which 4 by the AI coding assistant in the owner's sessions (all with changes) and 4 by the owner (pull-request merges #143 to #146); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-23**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.9.0 PR. P-34 joins two input columns into a timestamp; P-33 changes how numbers are read from CSV | — |
| G4 Third-party licences | **Passed 2026-10-23**: the 0.8.0 position stands; unchanged since 0.8.0 (no dependency change) | — |
| G5 CI green | Green on every 0.9.0 PR and on `main`; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and help text updated with each step; both options are covered by tests on the lowest and current pandas | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-23**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.8.0 release commit to the 0.9.0 release commit:
`git diff 32411b5 <release commit> -- packages/energydata-kit/src`
(2 files, about 70 added lines: `cli.py` and the version in
`__init__.py`). Points to confirm, each also checked by a tool:

- No new import: besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: the column names and the separator are the
  caller's; nothing is detected or guessed.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes join two input columns and read numbers with a
  separator.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.9.0`, moves `[Unreleased]` under a dated
`## [0.9.0]` heading, records the answers under G1, G3 and G4, and adds the
owner's D6 line naming `energydata-kit 0.9.0`; only with that line does it
remove the upload guard. It passes `check_release_readiness.py --strict`.
The owner then tags the merged commit `energydata-kit-v0.9.0`, the
*Release build* workflow prepares the draft GitHub release, and the owner
publishes it. The release PR is OSS-176.

## 0.8.0 (released 2026-10-23)

**Status:** decided 2026-10-23. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-23 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-170) sets the version to
`0.8.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.8.0 under D6 further down. The 0.7.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.8.0, as recorded by the repository owner on 2026-10-23:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.7.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.7.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.7.0; no
  package index.

**Since the preparation** (`eaf3272` to the release PR's base `1566b05`):
only OSS-169 (#141, docs). Nothing touched the package code or
`pyproject.toml`.

**What 0.8.0 contains** (P-29 and P-30 approved by the owner on
2026-10-23; proposals in `docs/architecture/ROADMAP.md`, OSS-166):

- `report --encoding NAME` reads CSV input in another text encoding; the
  flags and gaps CSVs follow it (P-29, OSS-167, #139). The encoding is
  named by the caller and never guessed.
- With `--assume-tz`, `--known-outage` times without a UTC offset are read
  in that zone, as the data's timestamps are (P-30, OSS-168, #140). The
  Python API is unchanged.
- No report- or comparison-format change (schema 2), no new or renamed
  public Python name, nothing removed, and no change to the output of
  commands that worked with 0.7.0. The changelog's `[Unreleased]` section
  has the release notes.

**What did not change since 0.7.0** (`git diff 230483c` on
`pyproject.toml`, 2026-10-23): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-165). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.8.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-23**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.7.0. Commits since the 0.7.0 release commit (`230483c`), on `main` at `eaf3272`: 8, of which 4 by the AI coding assistant in the owner's sessions (all with changes) and 4 by the owner (pull-request merges #137 to #140); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-23**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.8.0 PR. P-29 changes how input files are decoded; P-30 interprets the caller's outage times in the caller's stated zone | — |
| G4 Third-party licences | **Passed 2026-10-23**: the 0.7.0 position stands; unchanged since 0.7.0 (no dependency change) | — |
| G5 CI green | Green on every 0.8.0 PR and on `main`; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and help text updated with each step; both additions are covered by tests on the lowest and current pandas | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-23**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.7.0 release commit to the 0.8.0 release commit:
`git diff 230483c <release commit> -- packages/energydata-kit/src`
(2 files, about 75 added lines: `cli.py` and the version in
`__init__.py`). Points to confirm, each also checked by a tool:

- No new dependency: `cli.py` now imports `codecs` from the standard
  library; besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: the encoding and the time zone are the caller's;
  nothing is detected or guessed.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes decode input files and read outage times in a
  given zone.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.8.0`, moves `[Unreleased]` under a dated
`## [0.8.0]` heading, records the answers under G1, G3 and G4, and adds the
owner's D6 line naming `energydata-kit 0.8.0`; only with that line does it
remove the upload guard. It passes `check_release_readiness.py --strict`.
The owner then tags the merged commit `energydata-kit-v0.8.0`, the
*Release build* workflow prepares the draft GitHub release, and the owner
publishes it. The release PR is OSS-170.

## 0.7.0 (released 2026-10-22)

**Status:** decided 2026-10-22. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-22 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-164) sets the version to
`0.7.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.7.0 under D6 further down. The 0.6.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.7.0, as recorded by the repository owner on 2026-10-22:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.6.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.6.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.6.0; no
  package index.

**Since the preparation** (`2f29520` to the release PR's base `30e19d6`):
only OSS-163 (#135, docs). Nothing touched the package code or
`pyproject.toml`.

**What 0.7.0 contains** (P-26 and P-27 approved by the owner on
2026-10-22; proposals in `docs/architecture/ROADMAP.md`, OSS-160):

- With several input files, `report --flags-csv` ends with a `source`
  column naming each row's file (P-26, OSS-161, #133). This changes the
  flags CSV of several-file runs; the release notes say so. One-file runs
  and the JSON report are unchanged.
- `report --freq inferred` uses the most common step between timestamps
  as the expected step, on request only (P-27, OSS-162, #134). Without a
  step, the summary now names that step; nothing is guessed silently.
- No `Pandas4Warning` with pandas 3.1 (OSS-159, #131): the same values,
  read without the deprecated call. Results are unchanged.
- No report- or comparison-format change (schema 2), no new or renamed
  public Python name, nothing removed. The changelog's `[Unreleased]`
  section has the release notes.

**What did not change since 0.6.0** (`git diff ba19231` on
`pyproject.toml`, 2026-10-22): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-159). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.7.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-22**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.6.0. Commits since the 0.6.0 release commit (`ba19231`), on `main` at `2f29520`: 8, of which 4 by the AI coding assistant in the owner's sessions (all with changes) and 4 by the owner (pull-request merges #131 to #134); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-22**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.7.0 PR. P-26 labels flagged rows with their input file; P-27 reuses the existing most-common-step count as an opt-in grid; the pandas 3.1 fix changes how timestamps are read, not what they are | — |
| G4 Third-party licences | **Passed 2026-10-22**: the 0.6.0 position stands; unchanged since 0.6.0 (no dependency change) | — |
| G5 CI green | Green on every 0.7.0 PR and on `main` after #131; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and guide updated with each step; the guide's several-files and `--freq inferred` examples run in the test suite | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-22**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.6.0 release commit to the 0.7.0 release commit:
`git diff ba19231 <release commit> -- packages/energydata-kit/src`
(3 files, about 75 added lines: `cli.py`, `timestamps.py` and the version
in `__init__.py`). Points to confirm, each also checked by a tool:

- No new dependency: `cli.py` now imports numpy, already a runtime
  dependency used throughout the package; besides the standard library,
  the code still imports only numpy, pandas and Pint (Pandera and pyarrow
  optional). `python tools/check_ip_boundary.py`, run in CI, refuses
  forbidden imports and any dependency off the reviewed allowlist.
- No domain limits ship: the inferred step comes from the caller's own
  timestamps and is used only on request; the file names are the caller's.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes label rows with their file, choose a grid step
  the caller asks for, and read timestamps without a deprecated call.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.7.0`, moves `[Unreleased]` under a dated
`## [0.7.0]` heading, records the answers under G1, G3 and G4, and adds the
owner's D6 line naming `energydata-kit 0.7.0`; only with that line does it
remove the upload guard. It passes `check_release_readiness.py --strict`.
The owner then tags the merged commit `energydata-kit-v0.7.0`, the
*Release build* workflow prepares the draft GitHub release, and the owner
publishes it. The release PR is OSS-164.

## 0.6.0 (released 2026-10-22)

**Status:** decided 2026-10-22. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-22 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-158) sets the version to
`0.6.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.6.0 under D6 further down. The 0.5.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.6.0, as recorded by the repository owner on 2026-10-22:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.5.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.5.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.5.0; no
  package index.

**Since the preparation** (`9f8b8f4` to the release PR's base `b338d7e`):
OSS-157 (#129, docs only) and a Dependabot update (#128) that moves
`actions/download-artifact` from v7.0.0 to v8.0.2 in
`.github/workflows/release-build.yml`. Neither touches the package code or
`pyproject.toml`; the workflow change affects only how the tag build
collects the built files, and it first runs on the `energydata-kit-v0.6.0`
tag.

**What 0.6.0 contains** (approved as P-24 and P-25 by the owner on
2026-10-22; proposals in `docs/architecture/ROADMAP.md`, OSS-154):

- `compare_reports` and `compare --fail-if-worse` treat missing intervals
  inside known outages as explained, like `report --fail-on-issues` (P-24,
  OSS-155, #126). This changes `worse` (1 → 0) for comparisons of reports
  with outages; the release notes say so. Without outages, comparisons are
  unchanged.
- `report FILE...` reads several input files as one table (P-25,
  OSS-156, #127).
- No report- or comparison-format change (schema 2), no new or renamed
  public Python name, nothing removed. The changelog's `[Unreleased]`
  section has the release notes.

**What did not change since 0.5.0** (`git diff 34cf9c7` on
`pyproject.toml`, 2026-10-22): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-153). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.6.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-22**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.5.0. Commits since the 0.5.0 release commit (`34cf9c7`), on `main` at `9f8b8f4`: 8, of which 4 by the AI coding assistant in the owner's sessions (all with changes) and 4 by the owner (pull-request merges #124 to #127); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-22**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.6.0 PR. P-24 changes which report counts decide "worse"; P-25 changes how the command line reads its input | — |
| G4 Third-party licences | **Passed 2026-10-22**: the 0.5.0 position stands; unchanged since 0.5.0 (no dependency change) | — |
| G5 CI green | Green on every 0.6.0 PR; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and guide updated with each step; the guide's several-files example runs in the test suite | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-22**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.5.0 release commit to the 0.6.0 release commit:
`git diff 34cf9c7 <release commit> -- packages/energydata-kit/src`
(3 files, about 70 added lines: `cli.py`, `compare.py` and the version in
`__init__.py`). Points to confirm, each also checked by a tool:

- No new import: besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: the comparison uses counts already in the reports,
  and the file list is the caller's.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes decide when a comparison is worse and read
  several files.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.6.0`, moves `[Unreleased]` under a dated
`## [0.6.0]` heading, records the answers under G1, G3 and G4, and adds the
owner's D6 line naming `energydata-kit 0.6.0`; only with that line does it
remove the upload guard. It passes `check_release_readiness.py --strict`.
The owner then tags the merged commit `energydata-kit-v0.6.0`, the
*Release build* workflow prepares the draft GitHub release, and the owner
publishes it. The release PR is OSS-158.

## 0.5.0 (released 2026-10-21)

**Status:** decided 2026-10-21. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-21 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-152) sets the version to
`0.5.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.5.0 under D6 further down. The 0.4.0 to 0.1.0 records follow
and are unchanged.

**Decisions for 0.5.0, as recorded by the repository owner on 2026-10-21:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.4.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.4.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.4.0; no
  package index.

**What 0.5.0 contains** (approved as P-21 and P-23 by the owner on
2026-10-21; proposals in `docs/architecture/ROADMAP.md`, OSS-148):

- `report --fail-on-issues` no longer fails on missing intervals inside
  `--known-outage` periods (P-21, OSS-149, #120). This changes the exit
  status (1 → 0) for commands whose only gaps are explained; the release
  notes say so and give the old behaviour's replacement.
- `report --fail-on NAME`, repeatable, chooses which issues fail the exit
  status (P-23, OSS-150, #121).
- No report-format change (schema 2), no new or renamed public Python
  name, nothing removed. The changelog's `[Unreleased]` section has the
  release notes.

**What did not change since 0.4.0** (`git diff 6cc79fd` on
`pyproject.toml`, 2026-10-21): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-147). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.5.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-21**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.4.0. Commits since the 0.4.0 release commit (`6cc79fd`), on `main` at `2d42045`: 8, of which 4 by the AI coding assistant in the owner's sessions (all with changes) and 4 by the owner (pull-request merges #118 to #121); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-21**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.5.0 PR. Both changes decide the command line's exit status from counts the report already contains | — |
| G4 Third-party licences | **Passed 2026-10-21**: the 0.4.0 position stands; unchanged since 0.4.0 (no dependency change) | — |
| G5 CI green | Green on every 0.5.0 PR; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and guide updated with each step; the guide's `--fail-on` examples run in the test suite | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-21**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.4.0 release commit to the 0.5.0 release commit:
`git diff 6cc79fd <release commit> -- packages/energydata-kit/src`
(2 files, about 55 added lines: `cli.py` and the version in
`__init__.py`). Points to confirm, each also checked by a tool:

- No new import beyond `QualityFlag` from the package itself: besides the
  standard library, the code still imports only numpy, pandas and Pint
  (Pandera and pyarrow optional). `python tools/check_ip_boundary.py`,
  run in CI, refuses forbidden imports and any dependency off the reviewed
  allowlist.
- No domain limits ship: the exit status depends only on counts in the
  report and the issue names the caller passes.
- Tests and examples use synthetic data only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes decide when the command exits 1.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.5.0`, moves `[Unreleased]` under a dated
`## [0.5.0]` heading, records the answers under G1, G3 and G4, and adds the
owner's D6 line naming `energydata-kit 0.5.0`; only with that line does it
remove the upload guard. It passes `check_release_readiness.py --strict`.
The owner then tags the merged commit `energydata-kit-v0.5.0`, the
*Release build* workflow prepares the draft GitHub release, and the owner
publishes it. The release PR is OSS-152.

## 0.4.0 (released 2026-10-21)

**Status:** decided 2026-10-21. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-21 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-146) sets the version to
`0.4.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.4.0 under D6 further down. The 0.3.0, 0.2.0 and 0.1.0
records follow and are unchanged.

**Decisions for 0.4.0, as recorded by the repository owner on 2026-10-21:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.3.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.3.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 to 0.3.0; no
  package index.

**What 0.4.0 contains** (approved as P-17 and P-19 by the owner on
2026-10-21; proposals in `docs/architecture/ROADMAP.md`, OSS-142):

- `report --unit COLUMN=UNIT` without `--value-col` assesses the named
  columns (P-17, OSS-143, #114); an explicit `--value-col` still decides.
- Fast parsing of timestamp strings with `±HHMM` or `±HH` offsets (P-19,
  OSS-144, #115): 350,000 strings in about 0.4 s instead of 2.1–2.5 s.
  Same results and errors; 120,000 random batches matched the general
  parser on the lowest and current pandas, and a property test keeps
  comparing them.
- No report-format change (schema 2), no new or renamed public Python
  name, nothing removed. The changelog's `[Unreleased]` section has the
  release notes.

**What did not change since 0.3.0** (`git diff afa6974` on
`pyproject.toml`, 2026-10-21): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-141). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.4.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-21**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.3.0. Commits since the 0.3.0 release commit (`afa6974`), on `main` at `9e4a97b`: 8, of which 4 by the AI coding assistant in the owner's sessions (all with changes) and 4 by the owner (pull-request merges #112 to #115); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-21**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.4.0 PR. P-17 changes which columns the command line assesses; P-19 changes how timestamp strings are parsed, not what they mean | — |
| G4 Third-party licences | **Passed 2026-10-21**: the 0.3.0 position stands; unchanged since 0.3.0 (no dependency change) | — |
| G5 CI green | Green on every 0.4.0 PR; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog, guide and `PERFORMANCE.md` updated with each step; the guide's `--unit COLUMN=UNIT` example runs in the test suite | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-21**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.3.0 release commit to the 0.4.0 release commit:
`git diff afa6974 <release commit> -- packages/energydata-kit/src`
(3 files, about 35 added lines: `cli.py`, `timestamps.py` and the version
in `__init__.py`). Points to confirm, each also checked by a tool:

- No new import: besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: the change takes the column names and units the
  caller passes, and the offset bounds are those of real UTC offsets.
- Tests, benchmarks and examples use synthetic data only; no customer
  data, endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the changes select columns and parse timestamps faster.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.4.0`, moves `[Unreleased]` under a dated
`## [0.4.0]` heading, records the answers under G1, G3 and G4, and adds the
owner's D6 line naming `energydata-kit 0.4.0`; only with that line does it
remove the upload guard. It passes `check_release_readiness.py --strict`.
The owner then tags the merged commit `energydata-kit-v0.4.0`, the
*Release build* workflow prepares the draft GitHub release, and the owner
publishes it. The release PR is OSS-146.

## 0.3.0 (released 2026-10-21)

**Status:** decided 2026-10-21. The repository owner recorded the answers for G1,
G3, G4 and D6 on 2026-10-21 (below; the written confirmations are held by the
owner and not copied here). The release PR (OSS-140) sets the version to
`0.3.0`, dates the changelog and removes the upload guard together with the
D6 line for 0.3.0 under D6 further down. The 0.2.0 and 0.1.0 records
follow and are unchanged.

**Decisions for 0.3.0, as recorded by the repository owner on 2026-10-21:**

- **G1 Ownership:** counsel confirmed that the publishing entity owns the
  code added since 0.2.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.2.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0 and 0.2.0; no
  package index.

**What 0.3.0 contains** (approved as P-14 to P-16 by the owner on
2026-10-20; proposals in `docs/architecture/ROADMAP.md`, OSS-135):

- Faster parsing of timestamp strings whose UTC offset changes across DST
  (P-16, OSS-136, #107): about 2.3 s → 0.4 s for 350,000 strings. Same
  results and errors; 120,000 random inputs matched the previous code on
  the lowest and current pandas, and a property test keeps comparing them.
- `report --gaps-csv FILE` (P-14, OSS-137, #108): every gap as a CSV, also
  beyond `--max-listed`, on the same grid as the report.
- `report --unit COLUMN=UNIT`, repeatable (P-15, OSS-138, #109): units for
  several columns without a Table Schema.
- No report-format change (schema 2), no new or renamed public Python
  name, nothing removed. The changelog's `[Unreleased]` section has the
  release notes.

**What did not change since 0.2.0** (`git diff 344c862` on
`pyproject.toml`, 2026-10-21): no runtime dependency, optional extra,
version range or data file was added or changed. The only `pyproject.toml`
change is the restored upload guard (OSS-134). `THIRD_PARTY_LICENSES.md` is
unchanged.

| Gate | State for 0.3.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-21**: counsel confirmed (held by the owner). Counsel confirmed ownership for 0.1.0 (D2) and for the code added up to 0.2.0. Commits since the 0.2.0 release commit (`344c862`), on `main` at `ef01c86`: 15, of which 10 by the AI coding assistant in the owner's sessions (7 with changes, 3 merging `main` into a pull-request branch) and 5 by the owner (pull-request merges #105 to #109); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-21**: signed off by the technical lead (held by the owner). The `IP boundary` CI job passed on every 0.3.0 PR. P-14 and P-15 are command-line options over checks the package already has; P-16 changes how timestamp strings are parsed, not what they mean | — |
| G4 Third-party licences | **Passed 2026-10-21**: the 0.2.0 position stands; unchanged since 0.2.0 (no dependency change) | — |
| G5 CI green | Green on every 0.3.0 PR; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and guide updated with each step; the guide's examples of both new options run in the test suite | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-21**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.2.0 release commit to the 0.3.0 release commit:
`git diff 344c862 <release commit> -- packages/energydata-kit/src`
(3 files, about 160 added lines: `cli.py`, `timestamps.py` and the version
in `__init__.py`). Points to confirm, each also checked by a tool:

- No new import: besides the standard library, the code still imports only
  numpy, pandas and Pint (Pandera and pyarrow optional).
  `python tools/check_ip_boundary.py`, run in CI, refuses forbidden imports
  and any dependency off the reviewed allowlist.
- No domain limits ship: the new options take what the caller passes
  (a file name, units); nothing has a built-in threshold.
- Tests and examples use synthetic series only; no customer data,
  endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the additions write out gaps the report already finds, attach
  caller-given units, and parse timestamps faster.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.3.0`, moves `[Unreleased]` under a dated
`## [0.3.0]` heading, records the answers under G1, G3 and G4, and adds the
owner's D6 line naming `energydata-kit 0.3.0`; only with that line does it
remove the upload guard. It passes `check_release_readiness.py --strict`.
The owner then tags the merged commit `energydata-kit-v0.3.0`, the
*Release build* workflow prepares the draft GitHub release, and the owner
publishes it. The release PR is OSS-140.

## 0.2.0 (released 2026-10-20)

**Status:** decided 2026-10-20. The repository owner recorded the answers
for G1, G3, G4 and D6 on 2026-10-20 (below; the written confirmations are
held by the owner and not copied here). The release PR (OSS-133) sets the
version to `0.2.0`, dates the changelog and removes the upload guard
together with the D6 line for 0.2.0 under D6 further down.

**Decisions for 0.2.0, as recorded by the repository owner on 2026-10-20:**

- **G1 Ownership:** counsel confirmed in writing that the publishing entity
  owns the code added since 0.1.0 and can license it.
- **G3 IP boundary review:** signed off by the technical lead.
- **G4 Third-party licences:** the 0.1.0 position is enough; no dependency
  changed.
- **D6 Publication (G7):** a GitHub release only, like 0.1.0; no package
  index. `main` stays at
`0.2.0.dev0` with the upload guard until the owner decides the items below.
The 0.1.0 record follows further down and is unchanged.

**What 0.2.0 contains** (approved as P-7 to P-10 by the owner on
2026-10-20; design in `docs/architecture/SCHEMA_2.md`):

- Report schema 2 (OSS-104, #95): additive fields only; `report_schema.json`
  keeps the schema-1 definitions unchanged and validates both.
- `max_gap` (OSS-105, #96), `jump_max_rate` (OSS-106, #97),
  `counter_rollover` with the `COUNTER_ROLLOVER` flag (OSS-107, #99) and
  overlap matching of gaps in `compare_reports` (OSS-108, #101).
- New public names: `jump_rate_mask`, `counter_rollover_mask` and the
  Pandera `jump_rate_check`; new keyword-only options on existing functions.
  Nothing removed or renamed. The changelog's `[Unreleased]` section has
  the release notes, including what changes for 0.1.0 users.

**What did not change since 0.1.0** (`git diff 827a2df` on `pyproject.toml`,
2026-10-20): no runtime dependency, optional extra or version range was
added or changed, and no data file was added (`report_schema.json` grew).
The only `pyproject.toml` change is the restored upload guard (OSS-97).
`THIRD_PARTY_LICENSES.md` is unchanged.

| Gate | State for 0.2.0 | Open question |
|---|---|---|
| G1 Ownership | **Passed 2026-10-20**: counsel confirmed in writing (held by the owner). Counsel confirmed ownership of the repository's code for 0.1.0 (D2). Commits since then fall in the same categories: on `main` at `67a74aa`, 26 commits after the 0.1.0 merge (`827a2df`): 15 by the AI coding assistant in the owner's sessions (12 with changes, 3 merging `main` into a pull-request branch) and 11 by the owner (9 pull-request merges and 2 own commits adding the browser prototype in `apps/workbench/`, which is outside the package and not shipped); no external contributor | — |
| G2 Licence | Passed: Apache-2.0, unchanged | — |
| G3 IP boundary review | **Passed 2026-10-20**: signed off by the technical lead (held by the owner). Evidence: the `IP boundary` CI job on every PR; P-7 to P-10 are generic data-quality checks designed in the public `SCHEMA_2.md` | — |
| G4 Third-party licences | **Passed 2026-10-20**: the 0.1.0 position stands; unchanged since 0.1.0 (no dependency change) | — |
| G5 CI green | Green on every 0.2.0 PR; re-checked on the release commit | — |
| G6 Documentation honest | README, changelog and guide updated with each step; the guide's new examples run in the test suite | Review on the release commit |
| G7 Publication (D6) | **Passed 2026-10-20**: GitHub release only; approval line under D6 below | — |

**For the G3 reviewer** (the technical lead). The package code to review
is the diff from the 0.1.0 merge to the release commit:
`git diff 827a2df <release commit> -- packages/energydata-kit/src`
(8 files, about 1,100 added lines, more than half of them in
`report_schema.json`).
Points to confirm, each also checked by a tool:

- Besides the standard library, the code imports only numpy, pandas and
  Pint, plus Pandera in its optional extra (Parquet files are read through
  pandas with the optional pyarrow). `python tools/check_ip_boundary.py`,
  run in CI, refuses forbidden imports and any dependency off the reviewed
  allowlist.
- No domain limits ship: every threshold (`max_gap`, `jump_max_rate`,
  `counter_rollover`) is a caller argument that is off unless given.
- Tests and examples use synthetic series only (`make_synthetic_series` or
  inline values); no customer data, endpoints or credentials.
- Nothing forecasts, optimises, or computes grid, capacity or financial
  quantities: the additions decide which consecutive readings to compare
  and how to label a counter drop or a changed gap.

**Finishing the release** (done in the release PR, OSS-133):

1. The owner's D6 line under D6 below, in the owner's words, naming
   `energydata-kit 0.2.0`, and short notes under G1, G3 and G4 recording
   the answers (confirmations held by the owner, not copied).
2. Remove the `Private :: Do Not Upload` classifier, and make the
   readiness test expect nothing to fail (`--strict` exits 0).
3. Set the changelog date to the day the release PR merges.
4. Update the status lines in both READMEs, `SECURITY.md`,
   `CONTRIBUTING.md` and `RELEASE_GATES.md` for the chosen channel.

**After the decisions:** a release PR built from `RELEASE_CHECKLIST.md`
sets `__version__` to `0.2.0`, moves `[Unreleased]` under a dated
`## [0.2.0]` heading, removes the upload guard together with the owner's
D6 line for 0.2.0, and passes `check_release_readiness.py --strict`; the
tag `energydata-kit-v0.2.0` then runs the *Release build* workflow, which
now also creates the draft GitHub release (P-11, OSS-101). None of this is
done before the owner's decisions.

## 0.1.0 (released 2026-10-19)

**Status:** prepared 2026-10-16 (OSS-22), facts refreshed 2026-10-17
(OSS-48) and 2026-10-18 (OSS-60, OSS-69, OSS-77, OSS-85) · **For:** management, legal counsel
and the technical lead who sign off the release gates in `RELEASE_GATES.md`.

This page collects every decision that still blocks the first release, the
evidence already in the repository for each, and the exact questions to
answer. It does not make any of these decisions. Engineering work for 0.1.0
is complete; nothing below needs more code before the decisions are made.
Since the first version of this page, correctness passes (OSS-40 to OSS-49,
OSS-59, OSS-62, OSS-64, OSS-65, the whole-package reviews OSS-67 and
OSS-71 and the review of the later code, OSS-78) fixed the bugs they found, and the five approved proposals P-2 to P-6 were added (OSS-54 to OSS-58; see "What changed since OSS-48" below).
D3 is decided (Apache-2.0, #66), so the licence checks pass, and the
changelog entries for the work above are part of the 0.1.0 notes (OSS-61).
The readiness check fails on two items only, both waiting on D6:
*upload guard removed* and *publication approved (D6)*, the owner's
approval line under D6 below. Since OSS-83, CI refuses removing the guard
before that line exists. The release itself is rehearsed: the release
edits pass the strict readiness check and build a wheel and sdist that pass
`twine check` (not uploaded; the dry run does this on every change). After
the decisions, the release PR needs only those edits, the D6 line, the
release date and the sign-offs below.

## What changed since OSS-48

What reviewers of D2, D4 and D6 should know about the work added since the
facts were last refreshed:

- **New optional extra `[parquet]`** (OSS-58): the command line reads
  Parquet files with `pyarrow>=14.0.1` (Apache-2.0; the minimum fixes
  CVE-2023-47248). It is not installed by default, is listed in
  `THIRD_PARTY_LICENSES.md` and the IP-boundary allowlist, and is checked
  by pip-audit in CI.
- **New data file in the package:** `report_schema.json` (OSS-54), a JSON
  Schema for the report format, written for this project.
- **Report schema 1 gained fields** before its first release (OSS-56,
  OSS-57): `n_missing_explained`, `completeness_excluding_outages`,
  `parameters.known_outages` and the frame-level `timestamps` section. The
  changelog says schema 1 is fixed from the 0.1.0 release on.
- **`--format markdown`** (OSS-55): a second rendering of the existing
  summary, with no new facts.
- **Platforms:** Python 3.14 (OSS-51) and Windows and macOS (OSS-52) are
  tested in CI. The lowest-dependencies job also pins Pandera 0.24, the
  lowest the `[pandera]` extra allows (OSS-64).
- **Hardening after the features** (OSS-59 to OSS-67): each area was probed
  again and the real bugs fixed with regression tests; the roadmap's
  "Pre-release hardening at a glance" table lists them. Changes a user
  notices: a date without a time of day is naive and needs `assume_tz`;
  options are type-checked when given (no booleans or text for numbers,
  `cumulative` is `True` or `False`); an unknown time zone is an error, not
  a traceback; CLI metadata options need `--unit`.
- **Calendar resolutions in metadata** (OSS-68, #74, decided by the
  owner): a resolution with no fixed length (`"MS"`, `"W-MON"`) counts in
  the metadata's time zone; `"D"` stays a 24-hour step, after a second
  review (OSS-71) showed the local-day version broke zones where DST skips
  midnight.
- **Since then** (OSS-72 to OSS-76): two command-line edge cases of
  `--flags-csv` fixed (#76); internal tidying with no behaviour change
  (#77); `assess_quality` builds its grid once, 10–40 % faster, reports
  byte-identical (#78); a documentation accuracy audit for G6 (#79); the
  release branch refreshed (no PR). No new dependency, data file or report
  field since OSS-58.
- **Since OSS-77** (OSS-78 to OSS-83): a review of the code merged after
  OSS-71 found one small `--flags-csv` bug (equal calendar steps such as
  `"MS"` and `"1MS"` refused), fixed in #81. On 2026-10-18 #82 merged the
  release rehearsal into `main` by mistake, removing the upload guard
  while D1, D2, D4 and D6 were open; nothing was tagged or published, and
  #84 reverted it within half an hour. To stop a repeat, #85 ties the
  guard to the D6 record (see D6). No package behaviour changed.

## Where things stand

| Gate | State | Evidence in the repository |
|---|---|---|
| G1 Ownership | **Passed 2026-10-19**: confirmed in writing by counsel | D2 below |
| G2 Licence | **Passed 2026-10-18**: Apache-2.0 | D3 below; `LICENSE` at the root and in the package (#66) |
| G3 IP boundary review | **Passed 2026-10-19**: signed off by the technical lead | D4 below |
| G4 Third-party licences | Evidence ready; needs legal confirmation | `THIRD_PARTY_LICENSES.md`, kept in sync by `tools/check_third_party.py` in CI |
| G5 CI green | Green on `main` (Python 3.11 to 3.14 on Linux, lowest supported dependencies, Windows and macOS); re-checked on the release commit | `.github/workflows/ci.yml`, `security.yml` |
| G6 Documentation honest | Reviewed in OSS-20 and OSS-45; full accuracy audit of README, guide, architecture docs, docstrings and `--help` against the code in OSS-75 (#79); confirmed on the release commit | Package `README.md` (capabilities and known limitations), `CHANGELOG.md`, `examples/GUIDE.md` (executed by the tests) |
| G7 Publication | **Passed 2026-10-19**: GitHub release only, no package index | D6 below |

The mechanical release steps are rehearsed on every change by the *Release
dry run* CI job (`tools/release_dry_run.py`), now with the real licence. The
real release PR will therefore only differ by the decisions recorded here.

## Decisions

### D1. Repository visibility (owner: management) — DECIDED 2026-10-19

**Make the repository private for now**, recorded by the repository owner on
2026-10-19. The visibility change is made in the GitHub settings by the
owner; nothing in the repository does it. While private, the GitHub release
(D6) is visible only to people with access; making the repository public
again is a separate decision.


The GitHub repository is **public** (observed 2026-10-15), so every pushed
commit and branch is already visible. Since #66 (2026-10-18) it carries an
Apache-2.0 `LICENSE`, so readers may reuse the code under those terms; G1
(ownership) and G3 (IP review) are still open, and a licence does not
replace either (see `RELEASE_GATES.md`).

- **Question:** keep the repository public while G1–G3 are open, or make it
  private until they pass?
- **If private:** nothing else changes; CI keeps running. Making it public
  again later is part of G7.
- **If public:** record the decision here; no change needed.

### D2. Ownership, G1 (owner: management, with counsel) — DECIDED 2026-10-19

**Confirmed in writing by counsel**, as recorded by the repository owner on
2026-10-19: the publishing legal entity owns the code in the repository and
can license it. The written confirmation is held by the owner and is not
copied here. Not recorded here: whether external contributions need a CLA
or DCO (still open; no external contributions are accepted until it is
settled, see `CONTRIBUTING.md`).


- **Question:** does the publishing legal entity own all code in the
  repository, so that it can license it?
- **Facts for the answer** (from `git log` on `main` at `a1a8ea0`, after #85,
  2026-10-18): 215 commits.
  - 121 by an AI coding assistant (author "Claude", with a `Co-Authored-By`
    trailer) in sessions run by the repository owner: 100 contain the code,
    docs, licence and roadmap updates, 21 merge `main` into a pull-request
    branch.
  - 90 by the repository owner: 84 pull-request merges, 4 merges of `main`
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
and found no conflict: every shipped dependency is permissively licensed,
and so are the two optional extras (`[pandera]`, MIT, with its own
dependencies listed; `[parquet]`, pyarrow, Apache-2.0).

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

### D4. IP boundary review, G3 (owner: technical lead) — DECIDED 2026-10-19

**Signed off by the technical lead**, as recorded by the repository owner on
2026-10-19. The signed note is held by the owner. The package code has not
changed since `main` at `d6b8abe` (#86); the release PR changes only the
version date, the upload guard, a release-readiness test and these records.


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
  - Known outages (OSS-56) are periods the caller lists; the package only
    counts missing intervals inside them. It does not detect, predict,
    estimate or recover outages, and it fills no data. A reviewer may want
    to confirm this stays clear of the operational and recovery logic that
    `IP_BOUNDARY.md` excludes.
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
  *IP boundary*, the *energydata-kit* test jobs (Python 3.11 to 3.14, lowest
  dependencies, `windows-latest`, `macos-latest`), *energydata-kit packaging*,
  *Release dry run*, *Secret scan (gitleaks)*, *Dependency audit
  (pip-audit)* and *Dependency review*; require code-owner review
  (`.github/CODEOWNERS`); block force pushes.

### D6. Publication, G7 (owner: management) — DECIDED 2026-10-19

**D6 approved:** 2026-10-19, energydata-kit 0.1.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-20, energydata-kit 0.2.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-21, energydata-kit 0.3.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-21, energydata-kit 0.4.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-21, energydata-kit 0.5.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-22, energydata-kit 0.6.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-22, energydata-kit 0.7.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-23, energydata-kit 0.8.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-23, energydata-kit 0.9.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-23, energydata-kit 0.10.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-23, energydata-kit 0.11.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-23, energydata-kit 0.12.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

**D6 approved:** 2026-10-24, energydata-kit 0.13.0 as a GitHub release only (built wheel and sdist attached to the tagged release; no package index), recorded by the repository owner.

Nothing is uploaded to PyPI or any other index; publishing there would need
a new D6 decision and trusted publishing set up in a separate, reviewed
change.


- **Questions:**
  1. Publish to PyPI, or keep releases as GitHub-only build artifacts?
  2. Confirm the name `energydata-kit`. On 2026-10-16 (OSS-22, OSS-36),
     2026-10-17 (OSS-48) and 2026-10-18 (OSS-60) the names `energydata-kit` and
     `energydata_kit` were not taken on PyPI or TestPyPI (HTTP 404 from
     their JSON APIs); availability can change until the first upload.
  3. Who owns the PyPI project and its trusted-publishing configuration?
- **Evidence to record:** the owner adds one line under this heading,
  starting the line with `**D6 approved:** YYYY-MM-DD`, naming the package
  and version (for example `energydata-kit 0.2.0`), then the index and who
  approved. Since OSS-83, CI refuses removing the upload guard until that
  line exists, so a release merge cannot pass by editing the guard and its
  test together (as #82 did); since OSS-98 the line must name the version
  being released, so an earlier approval does not carry over.
- **After approval:** the release PR removes the `Private :: Do Not Upload`
  classifier together with that line; trusted publishing is set up in a
  separate, reviewed change. Nothing in the repository uploads anything
  today.

## Suggested order

1. D1 visibility (it affects how the other steps are handled in public).
2. D2 ownership (D3 licence is decided; counsel may still want to see
   the two together).
3. D4 IP review, on the commit intended for release.
4. D5 branch protection, any time before the release PR.
5. D6 publication approval.
6. Release PR from `RELEASE_CHECKLIST.md`: a fresh branch from the final
   `main` that reverts the OSS-81 revert (#84), which brings back the
   release edits rehearsed on `claude/oss-76-release-refresh`, and adds
   the owner's `**D6 approved:**` line. `main` already has version
   `0.1.0` and a dated `## [0.1.0]` changelog section (OSS-24, #30; nothing
   is released; `[Unreleased]` is empty since OSS-61). The release PR folds
   in anything added there since, sets the section's date to
   the release day and removes the guard (LICENSE and the licence
   declaration are already on `main` since #66);
   then tag `energydata-kit-v0.1.0`. The *Release build* workflow re-runs the
   strict readiness check on the tag and records build provenance.

## Not decided here

- Proposed work parked in `ROADMAP.md` until after these gates.
- Version numbers after 0.1.0 and the support policy for old pandas releases.
