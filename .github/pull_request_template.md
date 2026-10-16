## Summary

<!-- What does this change and why? -->

## Testing

<!-- Commands run and results. -->

## IP-boundary checklist

- [ ] Written for this repository, or from a credited, license-compatible public source
- [ ] Does not reproduce private Solid Soup / MICA code, structure, algorithms, parameters or fixtures
- [ ] No customer, site or asset data; all test data is synthetic
- [ ] No credentials, private endpoints or internal hostnames
- [ ] Not in the out-of-scope list in `docs/governance/IP_BOUNDARY.md`
- [ ] New dependencies (if any) added to `tools/ip_boundary.toml` with justification

## Checks

- [ ] Package: `ruff check`, `ruff format --check`, `mypy`, `pytest`
- [ ] Repository: the `tools/check_*.py` scripts and `pytest tools/tests` (see `CONTRIBUTING.md`)
- [ ] `CHANGELOG.md` entry under `[Unreleased]` for user-visible changes
- [ ] Docs updated (package README, duplication register) for a new capability
