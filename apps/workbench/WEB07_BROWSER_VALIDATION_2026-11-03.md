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

## Expanded multi-scenario validation (same date)

- Passing Chromium/Pyodide workflow run: [41686036602](https://github.com/Solid-soup/opensource/actions/runs/41686036602)
- Head commit tested: `e70ffdf10a67cfe9515ebc7f073838a82dd4143b`
- Four hard-coded **synthetic-only** test cases; exact canonical schema-v2 field comparisons against the local Python adapter
- Case results:

| Scenario | Rows | Canonical parity | Differences | Measured seconds |
|---|---:|---|---:|---:|
| Baseline (gaps, duplicate, blank) | 95 | PASS | 0 | 6.61 |
| Autumn DST / two explicit offsets | 5 | PASS | 0 | 0.10 |
| Spring DST / explicit offset transition | 4 | PASS | 0 | 0.08 |
| Mixed UTC offsets and Z | 4 | PASS | 0 | 0.08 |

- Browser page errors: **0**
- Detected outbound synthetic dataset payload requests under the existing narrow heuristic: **0**
- Dependency/network domains observed: `cdn.jsdelivr.net`, `pypi.org`, `files.pythonhosted.org`
- The first multi-scenario attempt failed because the harness could read stale completion state while the next asynchronous assessment was starting. The page now clears completion status synchronously before its first await; the harness requires the run button to be re-enabled before reading each result. The next run passed all four cases.

**Interpretation:** This establishes parity for four carefully controlled synthetic scenarios, not every possible time-series input. The `6.61 s` includes initial browser runtime/dependency loading in this one run, while later cases reused the same engine and finished in `0.08–0.10 s`. These are single observations, not repeated benchmarks. Full network-byte, memory, Safari/Firefox, accessibility, signing and offline distribution checks remain outstanding.

## First Chromium transfer and V8-heap measurement (same date)

The instrumented, real Chromium/Pyodide smoke test **passed** in GitHub Actions run [41696897076](https://github.com/Solid-soup/opensource/actions/runs/41696897076), testing commit `fc003bac973fb53c6b079ab270fcafa670d8a53c`.

| Synthetic scenario | Parity | Seconds | External encoded bytes completed during case | V8 heap used after case |
|---|---|---:|---:|---:|
| Baseline (95 rows) | PASS | 7.40 | 13,683,608 | 19,969,612 |
| Autumn DST (5 rows) | PASS | 0.09 | 0 | 20,531,308 |
| Spring DST (4 rows) | PASS | 0.08 | 0 | 21,024,132 |
| Mixed UTC offsets (4 rows) | PASS | 0.08 | 0 | 21,461,136 |

- Completed external requests recorded during baseline: **22**
- External hostnames: `cdn.jsdelivr.net`, `files.pythonhosted.org`, `pypi.org`
- Locally built EnergyData Kit wheel size: **78,552 bytes**
- Zero canonical report field differences and zero browser JavaScript page errors across all four cases
- No suspected outbound synthetic dataset payload requests under the narrow request-body heuristic
- V8 heap total after each case: **34,975,744 bytes**

**Accounting warning:** `Network.loadingFinished.encodedDataLength` sums selected *completed Chromium CDP network requests*; it is not total uncompressed assets or a complete accounting of network traffic. Zero additional external requests in subsequent scenarios means the already-loaded interpreter was reused in that browser session, **not** that a new browser could start offline. V8 heap excludes WebAssembly linear memory, Python heap, browser native memory and process RSS. The increase in V8 heap after these cases is not a measured memory leak. The elapsed times are one sample per scenario and are not statistical benchmarks.

After the measurement, `.github/workflows/web07-browser-parity.yml` was returned to **manual-only** triggering to avoid repeated heavyweight downloads on PR edits. These values are observations, not release acceptance criteria.

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
