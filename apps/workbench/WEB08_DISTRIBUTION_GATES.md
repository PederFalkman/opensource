# WEB-08 — Installation-free EnergyData Kit distribution gates

**Internal working draft. No deployment or publication approval.**

## What WEB-07 demonstrated

Chromium/Pyodide 0.29.5 executed a locally built EnergyData Kit 0.17.0.dev0 wheel. Four hard-coded, synthetic-only scenarios returned identical canonical quality-report fields to local Python (see `WEB07_BROWSER_VALIDATION_2026-11-03.md`). Current experiment still requires a developer-selected wheel and initially downloads third-party runtime/dependencies. Therefore it is **not** an installation-free customer product.

## Proposed no-install distribution architecture (not implemented)

1. Select an approved tagged EnergyData Kit release from this OSS repository, independent of proprietary Solid Soup code.
2. Build a deterministic, CI-attested wheel with source commit, version, file size, SHA-256 and licence/SBOM evidence. No unreviewed local wheel selection for end users.
3. Produce a versioned **static** asset manifest including pinned Pyodide runtime, NumPy, pandas, Pint and EnergyData Kit wheel file hashes, license list, cumulative compressed sizes, allowed origins and cache policy. Review content security policy and integrity enforcement for all assets.
4. Serve static assets from an approved origin (or a reviewed self-hosted distribution). The browser computes and validates expected wheel hashes before execution; dependency artefacts need their own reviewed provenance and integrity strategy. Do not blindly load packages from dynamic PyPI without review.
5. Run the Python engine in a dedicated Web Worker with explicit progress, cancellation, failure recovery and memory limits. The main Workbench's `browser-preview` results remain distinctly marked; the Python path becomes selectable only after release gates.
6. Allow user-provided CSV only **after** browser isolation, limits, accessibility, privacy/security review and transparent network behavior have passed. WEB-07 remains synthetic-only.

## Quantitative gate measurements

A new optional Chromium CDP measurement in `browser_parity_smoke.py` reports encoded transferred bytes for completed requests, including external versus loopback traffic; V8 heap used/total after each scenario; per-scenario elapsed seconds; and trusted wheel file size. A missing metric must be marked absent, never assumed zero.

**Limitations:** CDP `Network.loadingFinished.encodedDataLength` does not measure memory/disk/uncompressed assets and may miss cached/incomplete requests. Chromium `Performance.getMetrics` V8 heap **excludes Python/WebAssembly linear memory and native browser memory**. Browser process RSS/peak memory requires a separately specified OS-level measurement and runner profile. The first scenario includes runtime cold-load; later scenarios reuse a warm engine. Repeat runs with cache disabled/enabled and report distribution (median, p95), not single samples.

## Required gates before main Workbench integration

| Gate | Status and evidence required |
|---|---|
| Canonical result correctness | Four synthetic cases passed in Chromium; additional malformed/large-series tests, negative paths and controlled real datasets remain |
| Package supply chain | Release-signed wheel, deterministic build, pinned dependency/runtime assets, SBOM, licence and origin review |
| Install-free UX | No manual wheel/hash selection; downloaded assets verified against reviewed manifest |
| Performance | Cold and warm times, total transfer bytes, cache behavior, peak WASM/process memory across supported hardware |
| Browser coverage | Chromium, Firefox and Safari (incl. macOS/iOS where applicable), with reproducible numerical parity |
| Privacy | No unexpected uploads; full network inspection, no trackers, explicit consent for runtime dependency downloads |
| Security | Content security policy, worker isolation, untrusted-file limits, cancellation, runtime provenance |
| Accessibility | Keyboard, screen reader, progress/errors, responsive UI |
| Publication | Explicit IP/legal/owner approval; no proprietary source, test data or customer datasets |

No shipping ETA, support claim or software release is implied by this design.
