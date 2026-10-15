# Security policy

## Reporting a vulnerability or leak

**Do not open a public issue or pull request.** This repository is public.

- Use GitHub's private vulnerability reporting for this repository
  (*Security → Report a vulnerability*), or contact the repository owner
  directly.
- This includes suspected leaks of credentials, private code or data, and
  breaches of the [IP boundary](docs/governance/IP_BOUNDARY.md).

We aim to acknowledge reports within five working days.

## If a secret was committed

1. **Revoke and rotate it right away.** Assume it was copied: pushes to a
   public repository are visible at once.
2. Then notify the owner so history can be cleaned if needed.

## Supported versions

No version has been released. Security fixes apply to `main`.

## Automated controls

Secret scanning (gitleaks), dependency audit (pip-audit), GitHub dependency
review and Dependabot run in CI; see `.github/workflows/security.yml`.
