# IP boundary

**Status:** draft for review · **Applies to:** everything in this repository

This repository holds standalone, independently useful open-source tools. It
must never become a channel through which Solid Soup / MICA commercial
intellectual property leaves the company.

> **Note:** At the time of writing (2026-10-15) this GitHub repository is
> already **public**. Every commit pushed to any branch, including
> unmerged feature branches, is publicly visible right away. Treat every
> push as a publication.

## Non-negotiable rules

1. **No imports from proprietary repositories.** Public packages must not
   import, vendor, submodule or depend on any private Solid Soup / MICA
   repository or package.
2. **No copying of internal algorithms or commercial models.** That includes
   paraphrased or "cleaned-up" rewrites of private code.
3. **No customer data.** No customer-specific data, parameters, site
   identifiers, asset lists, thresholds or internal test fixtures. Test data
   must be synthetic and generated in this repository
   (see `energydata_kit.synthetic`).
4. **No private infrastructure.** No private API endpoints, hostnames,
   credentials, tokens or proprietary connector logic.
5. **No RODOT operational or recovery algorithms.**
6. **No proprietary optimization.** That covers financial, capacity and
   network optimization.
7. **No extraction by similarity.** Being *able* to implement something
   publicly does not justify moving private code here. Public functionality
   must be built from public knowledge (standards, textbooks, public
   libraries) and written from scratch in this repository.

## Out of scope for public packages

Even when written from scratch, these capabilities stay out of this
repository unless an explicit, documented decision says otherwise:

- forecasting (load, generation, price)
- grid, power-flow or hosting-capacity calculations
- dynamic line or transformer ratings
- connection planning and capacity allocation
- economic or dispatch optimization
- industrial decision support

## What *is* in scope

Generic, commodity tooling that many organizations could write and that gives
no competitive advantage. Examples: timestamp handling, data-quality checks,
unit metadata, report serialization, synthetic test data, packaging and CI
helpers.

## Automated checks

`tools/check_ip_boundary.py` runs in CI on every pull request
(`.github/workflows/ci.yml`, job *IP boundary*). It fails the build when:

- any Python file in `packages/` or `tools/` imports a module on the
  `forbidden_imports` list in `tools/ip_boundary.toml` (static imports,
  `importlib.import_module("…")` and `__import__("…")` with literal names);
- any package declares a dependency that is not on its reviewed allowlist
  in `tools/ip_boundary.toml`;
- any dependency is a direct or VCS reference (`pkg @ git+…`, URLs), which
  could pull code from private repositories.

Also in place:

- **Secret scanning:** gitleaks runs on every pull request, on `main`, and
  weekly (`.github/workflows/security.yml`).
- **Dependency review and audit:** GitHub dependency review on pull requests;
  `pip-audit` of resolved runtime dependencies; Dependabot.
- **Code owners:** `.github/CODEOWNERS` requires maintainer review for
  governance docs, `tools/` (including the allowlist), workflows and package
  manifests.

### Limits of automation

These checks are tripwires, not proof. They cannot detect copied logic that
was renamed, translated or re-typed, and the denylist is deliberately generic
because this repository is public: listing private module names here would
itself disclose them. **Human review is the primary control.** Every pull
request author confirms the checklist below.

## Contributor checklist (every pull request)

- [ ] I wrote this code for this repository, or it comes from a public source
      whose license allows it and is credited (see *Third-party code*).
- [ ] I did not look at private Solid Soup / MICA code while writing it, or,
      if I am familiar with such code, this contribution does not reproduce
      its structure, algorithms, parameters or fixtures.
- [ ] No customer, site or asset data; all test data is synthetic.
- [ ] No credentials, private endpoints or internal hostnames.
- [ ] The functionality is not in the out-of-scope list above.

## Third-party code

Prefer depending on a maintained library over copying code. If copying is
unavoidable, it is allowed only when:

1. the source license is compatible with the intended project license
   (Apache-2.0 candidate: MIT, BSD, Apache-2.0 are fine; GPL/AGPL code must
   not be copied; MPL-2.0 is file-scoped, so get a maintainer decision first);
2. the copyright notice and license text are kept, and the origin is recorded
   in the file header and in `docs/architecture/DUPLICATION_REGISTER.md`.

No third-party code has been copied into this repository so far.

## Escalation

If you suspect a breach (private code, data or credentials committed), do not
open a public issue. Follow `SECURITY.md`. Rotating a leaked credential takes
priority over removing it from history: the repository is public, so assume
anything pushed has been copied.
