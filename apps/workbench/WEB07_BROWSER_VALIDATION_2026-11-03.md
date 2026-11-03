# WEB-07 Chromium/Pyodide validation record — 2026-11-03

**Internal technical evidence; not external release approval.**

## Observed result

- Repository: `Solid-soup/opensource`
- PR: [#198](https://github.com/Solid-soup/opensource/pull/198)
- GitHub workflow: `WEB-07 manual Chromium/Pyodide parity`
- Run ID: [41675200757](https://github.com/Solid-soup/opensource/actions/runs/41675200757)
- Tested commit: `207bdac22e7708a99c6f8282e127293035dda679`
- Test: `apps/workbench/browser_parity_smoke.py`
- Input: fixed **synthetic** 15-minute power series, no CSV user upload
- Artifact: locally built `energydata_kit-0.17.0.dev0-py3-none-any.whl`
- Wheel SHA-256: `479e3f4e6224dfbea2ab48b0f04f6dc509e4c72ad1626ecad3a66933c297546d`
- Runtime: Chromium (GitHub-hosted Ubuntu runner), Pyodide 0.29.5
- Canonical v2 report comparison: **PASS**
- Canonical field-level differences: **0**
- Browser page errors: **0**
- Observed time (from browser experiment start through returned JSON): **7.32 seconds**
- External hostnames observed: `cdn.jsdelivr.net`, `files.pythonhosted.org`, `pypi.org`
- Suspected dataset-bearing outbound requests under existing heuristic: **0**

The browser loaded Pyodide/dependencies, verified the local wheel digest, executed `energydata_kit.assess_quality`, returned a schema-v2 report, and compared all canonical report fields against the local Python adapter using the same synthetic fixture. The first run (ID `41674871563`) failed before Pyodide execution because the browser smoke harness referenced a module-scoped function as a global; the corrected run above passed.

## Interpretation and limitations

**Proven:** the selected package build can run successfully in the tested Chromium/Pyodide combination and produce identical canonical v2 report fields for this one synthetic fixture.

**Not proven:**
- Report parity for real customer datasets, different series/metadata, DST corner cases, large inputs, alternative browsers, or different device architectures
- Offline-first startup: initial dependencies were fetched over the network
- Privacy/security of all remote runtime code: request-body monitoring is a narrow heuristic, not a network exfiltration proof
- Runtime memory consumption, transfer-byte size, cold-vs-warm statistical performance, or accessibility
- Supply-chain provenance: verifying a user-supplied wheel SHA-256 is file equality, not signature validation
- A zero-install, ready-to-use product: this experimental page still requires a locally built, trusted wheel and separately calculated digest

## Next gates

1. Expand automatic synthetic fixtures: explicit mixed time-zone offsets, spring/fall DST, missing/duplicate readings, malformed CSV and large-scale limits. Compare **all** canonical report fields.
2. Collect transfer bytes, cold/warm times, peak memory and reproducibility on supported Chromium, Firefox and Safari versions.
3. Decide on a reviewed, pinned, locally hosted wheel/dependency bundle for a genuinely installation-free product; define supply-chain and cache policy.
4. Keep experimental route separated from default Workbench until explicit accessibility, IP/privacy and release decisions.

This record belongs to Solid Soup Open Engineering only; it includes no proprietary platform code or customer information.
