# WEB-10 — Manual browser process-memory observability

**Internal working draft; no deployment, publication or operational claim.**

## Motivation and scope

The existing WEB-07 V8 heap measurements **exclude** Python/WebAssembly linear memory and the browser's native memory. WEB-09 has demonstrated Worker cancellation and recovery in real Chromium, but has not measured how browser memory behaves across those transitions. An OS-level sampler is a useful next observation, not a proof of reclamation.

## Implemented manual-only tools

- `browser_memory_probe.py`: reads resident set size (RSS) of **child processes of the synthetic-test Python harness**, with bounded sampling and a recorded sampled peak. It includes Playwright driver and the browser process tree, but excludes the parent Python harness itself.
- `browser_memory_gate.py`: runs the existing `browser_worker_smoke.py` (which stages a synthetic-only wheel on a disposable loopback static server), collects time-sampled RSS of its process descendants, records exit status and outputs a JSON measurement envelope.
- `tests/test_browser_memory_probe.py`: deterministic offline tests for aggregation, disappearing processes, missing samples and sampling lifecycle.

This probe does **not** record a customer dataset or send telemetry to an external service. It is an optional developer-run process measurement, not regular CI.

### Local usage

Run from the repository root after installing the existing WEB-09 browser prerequisites plus the optional psutil dependency:

```bash
python -m pip install psutil
python apps/workbench/browser_memory_gate.py \
  --wheel /tmp/edk-worker-wheel/energydata_kit-0.17.0.dev0-py3-none-any.whl \
  --sample-ms 100
```

The wheel path must exist and be a trusted local development build. No asset is automatically published or downloaded by the measurement wrapper; **the underlying WEB-09 smoke still downloads the Pyodide runtime and dependencies from their existing third-party origins**, so run it only in an approved network environment.

## What the result does and does not mean

- **Observed:** sampled peak and final aggregate RSS, number of process descendants in the last snapshot, sample count and interval, underlying browser smoke pass/fail.
- **Not observed:** isolated Pyodide/WASM linear memory, single-Worker private memory, browser GPU allocations, disk cache, or exact amount of memory freed when a Worker terminates.
- Summing RSS can **double-count shared memory pages** between processes. Samples miss spikes between intervals. A single before/after comparison is not evidence of a memory leak or memory release.
- Reproducible analysis requires repeated cold/warm runs on defined hardware, OS, browser build and pinned dependencies. Future work should add phase-tagged snapshots (prior to startup, before cancellation, after cancellation/GC, after restart) and OS-specific measurements.

## Optional proportional set size (PSS) sampling — implementation, not yet measured

The memory sampler now attempts Linux/OS process `memory_full_info().pss` alongside each periodic descendant-process RSS sample. The result includes `peak_complete_pss_bytes` and `complete_pss_samples`. **A PSS peak is reported only when every observed live descendant in that snapshot supplied a nonnegative PSS value.** Unsupported/denied/partial snapshots do not produce a guessed PSS total, and no samples means `null`, not zero.

PSS is a different allocation view from RSS and helps avoid some double counting of shared resident pages; it still covers the **Python test harness's descendant process tree** (browser plus Playwright driver), **not** an individual Web Worker or isolated Pyodide/WASM heap. The sampling routines enumerate live processes independently for RSS and PSS; rapidly changing process trees may prevent perfect timestamp alignment. The value is an observed sample maximum, not a continuous true peak or a memory-reclamation proof.

This is implementation and fast offline test coverage only. The previous 104-sample Chromium run did **not** collect PSS; its published RSS figures must not be relabeled. The first separate real PSS-enabled run is recorded below.

## First measured Linux PSS observation — 2026-11-04

- [Real Chromium workflow run 41837679380](https://github.com/Solid-soup/opensource/actions/runs/41837679380); tested commit `75dc4e36a937d382847c8ff974de5e18f625363a`.
- Synthetic isolated-Worker smoke: **PASS**, exit code 0, **4/4** canonical report parity. No timeout.
- Sampling interval: **100 ms**; total **97** samples, of which **88** provided complete PSS measurements for all *observed descendants*.
- Maximum sampled **complete-snapshot proportional-set-size sum: 632,248,320 bytes** (632.2 MB decimal).
- Maximum sampled **descendant-process RSS sum: 938,618,880 bytes** (938.6 MB decimal).
- Final descendant count **0** and final RSS sum **0 bytes** after the entire browser smoke and driver exited.

**Strict interpretation:** RSS and PSS peak values may come from different sample timestamps. Scope is the Playwright-driver and browser-descendant process tree of the Python smoke runner, not a separately identified browser Worker or Pyodide/WebAssembly heap. A missing/partial PSS sample is excluded from PSS peak accounting; 88 complete snapshots do not imply continuous coverage. Final process count zero is only observed **after all browser processes exit**, not proof that memory was reclaimed at the earlier individual Worker cancellation. This is one run, not a stable resource benchmark or release threshold. It must not be added to or directly compared as a matched experiment with the separate WEB-09 process-tree RSS figures collected by a different sampler.

The expensive workflow was returned to manual-only dispatch after the measurement.

## Acceptance gates

1. The new offline tests must pass routine CI/security.
2. Explicitly run the memory envelope in a controlled browser environment and record its real sampled values, job/revision, and limitations.
3. Measure within-run phase snapshots and repeated runs; do not set release thresholds from a single test.
4. Firefox and Safari/WebKit compatibility and supply-chain trust remain independent requirements.
5. Do not integrate with customer-facing Workbench or permit customer data without release review.

## First real Chromium process-tree measurement — 2026-11-04

- GitHub Actions: [run 41828378423](https://github.com/Solid-soup/opensource/actions/runs/41828378423)
- Tested commit: `ce0bc1e567c6f19a23c8384e0aa48d7088d0814f`
- WEB-09 synthetic Chromium/Pyodide smoke completed successfully (`smoke_exit_code: 0`).
- Descendant-process RSS sampled **104 times**, at **100 ms** intervals.
- Maximum *sampled sum* of Playwright-driver and Chromium-child process RSS: **946,016,256 bytes** (approximately **946 MB decimal / 902 MiB binary**).
- Final sampled descendant-process RSS: **0 bytes**, with **0 remaining descendant processes** after browser/test shutdown.
- The test did not time out.
- The heavyweight workflow was restored to **manual-only** triggering after collecting evidence.

**Critical limitation:** The approximately 946 MB number is not Pyodide WASM usage, nor even necessarily distinct physical browser memory; RSS summation can double-count shared pages and includes the Playwright driver. The zero final measurement is observed after the **entire browser smoke exits**, not at the moment a single Worker is terminated. It cannot be used to claim per-Worker memory reclamation or memory leak absence. A phase-tagged, replicated experiment is the next gate.

**Current status:** Initial manual Chromium process-tree RSS sample recorded, with strict interpretation limits. Phase-specific Worker reclamation and replicated statistics remain unverified.
