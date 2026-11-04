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

## Acceptance gates

1. The new offline tests must pass routine CI/security.
2. Explicitly run the memory envelope in a controlled browser environment and record its real sampled values, job/revision, and limitations.
3. Measure within-run phase snapshots and repeated runs; do not set release thresholds from a single test.
4. Firefox and Safari/WebKit compatibility and supply-chain trust remain independent requirements.
5. Do not integrate with customer-facing Workbench or permit customer data without release review.

**Current status:** observability instrumentation and regression tests implemented; actual memory numbers not yet measured by this WEB-10 tool.
