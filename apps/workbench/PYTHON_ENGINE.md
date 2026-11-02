# WEB-02 — Real Python quality report, local-only

**This adapter invokes the actual `energydata-kit` Python library.** It does not reimplement quality logic in JavaScript. The existing `index.html` remains a **non-authoritative browser preview** until WEB-03 is approved and implemented.

## Install and run

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e 'packages/energydata-kit' pytest
python apps/workbench/python_report.py my_meter.csv --timestamp timestamp --value kwh --interval-minutes 15 --output report.json
```

The resulting JSON contains `engine: python-validated`, exact package version and the canonical library `report` object, with schema version 2. All processing stays local. There is **no server, network call, upload, or data retention**.

The adapter requires ISO 8601 timestamps with explicit UTC offsets or Z and a CSV of at most 5 MiB. It does not infer ambiguous DST times; use the full library API for advanced DST policies, metadata, multi-series reporting, calendar grids, local-day completeness and flagged series.

### Verification

```bash
python -m pytest apps/workbench/tests/test_python_report.py -q
```

Tests use the installed library to check duplicate timestamps, gaps, DST offsets and invalid input. No source code or output of Solid Soup's proprietary platform is included.

## Next WEB-03 gate

Determine whether a browser-local Python runtime is feasible on supported devices. If not, any server-backed execution requires an explicit separate privacy/security and deployment decision. The static frontend must **never relabel its JavaScript preview as Python-validated**. The local CLI output can be imported or inspected separately, but no integration is claimed yet.

Tracking: [OSS #91](https://github.com/PederFalkman/opensource/issues/91).

## Open the canonical report in the Workbench

1. Generate a report locally with `--output report.json`.
2. Open `apps/workbench/index.html` directly in your browser.
3. Click **Import Python JSON** and select `report.json`.
4. The second, separate results panel displays the **canonical Python report's** row count, missing interval count, duplicate count, completeness and input fingerprint.

This is a **viewer for externally generated reports**, not in-browser execution of Python or a server connection. Imported JSON can be fabricated or edited: matching the expected format **does not authenticate the source**, and the UI labels it unverified. Independently verify the generating environment before making consequential engineering decisions.

The original browser-side preview remains non-authoritative and is never overwritten with the Python results. A real embedded Python runtime remains a separate WEB-03 feasibility/security decision.
