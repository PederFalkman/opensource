# WEB-10 — Browser matrix and timing for isolated Python Workbench

**Internal working draft — no publication, operational-data or release approval.**

## Implemented

The synthetic-only `browser_worker_smoke.py` now accepts `--browser chromium`, `--browser firefox`, or `--browser webkit`. It uses ephemeral localhost staging, candidate integrity verification, cancellation checks, and four independent canonical-v2 report comparisons. Unsupported browser identifiers fail before Playwright starts.

Each fixture includes elapsed wall-clock time between Run and completion. Initial load includes dependency downloads; later cases reuse Python. Single samples are not p95, full memory or process RSS. Request destinations are hostnames, not a privacy audit.

Local command (with a trusted wheel and installed browser):

```sh
python -m pip install -e packages/energydata-kit build playwright
python -m playwright install chromium firefox webkit
python apps/workbench/browser_worker_smoke.py --wheel /tmp/reviewed-build/energydata_kit-0.17.0.dev0-py3-none-any.whl --browser firefox
```

The manual-only workflow `.github/workflows/web09-worker-smoke.yml` has a browser selection. No automatic PR, push or scheduled runs. Tests for CLI selection are fast/offline.

## Evidence and limitations

WEB-09 Chromium four-case parity PASS: https://github.com/Solid-soup/opensource/actions/runs/41805199318

WEB-10 Firefox and WebKit are **not verified** merely because their options exist. Actual engine execution must be recorded with run IDs and numerical differences. Third-party dependencies remain fetched at runtime and the candidate manifest has no independently authenticated publisher. Real customer CSV, releases and production hosting remain prohibited.
