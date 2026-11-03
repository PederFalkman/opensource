# EnergyData Kit — Online Workbench (prototype)

A static, offline-first browser demo for the open-source `energydata-kit` package. Visual direction follows Solid Soup's demo system: deep green/charcoal, white surfaces, quiet mint accents, strict grid and minimal UI.

## Run locally

Open `index.html` in a modern browser, or serve this directory with `python -m http.server 8080` and navigate to `http://localhost:8080`. No dependencies, analytics, uploads or network services are used.

## Prototype features

- Local CSV import (up to 5 MB) with validated comma-separated quoting, BOM, CRLF and embedded quoted newlines. Malformed quoting and empty headers are rejected.
- Deterministic synthetic power dataset with missing intervals, one duplicate instant and a missing value. The **Download example CSV** action exports this exact fixture for use with the local Python analysis.
- Timestamp and value-column selection, expected interval selection.
- Basic browser-only quality diagnostics; visual series preview; JSON export.
- Explicit warning that browser checks are not equivalent to the Python library.

## Try the same dataset in both engines

1. Click **Load example dataset** in the Workbench to inspect its browser-only preview.
2. Click **Download example CSV** to save the same deterministic file locally.
3. From the repository root, with the Python package installed, run:

```bash
python apps/workbench/python_report.py synthetic-example.csv --timestamp timestamp --value power_kw --interval-minutes 15 --output report.json
```

4. Import `report.json` with **Import Python JSON** and compare the independently generated canonical counts. That file is still explicitly marked as an **unverified import**.

The browser preview is not authoritative and is not expected to match the Python engine on all edge cases. No hosted deployment exists.

## Constraints

This prototype requires explicit ISO-8601 UTC offsets or Z; it does not support local ambiguous timestamps, full DST interval semantics, metadata-based units, known-outage policies, flagged CSV or the authoritative `assess_frame`/quality-report schema. It assumes expected evenly spaced observations. It is **not** operational or engineering assurance software.

## Planned authoritative integration

1. Define a stable, versioned adapter matching released `energydata-kit` assessment and report APIs (do not reimplement Python validation in TypeScript).
2. Prefer **local WASM/Pyodide** only after feasibility and dependency-size testing; otherwise use a minimal sandboxed Python HTTP backend with strict upload limits, no retention, no proprietary Solid Soup access, and explicit consent to transfer data.
3. Separate `demo-preview` from `python-validated` states, with visible engine/version and report provenance.
4. Add local-calendar DST tests, multi-series reports, metadata form, known outages, and accessible data tables.
5. Host only after threat modeling, accessibility, legal/IP and publication review. No automatic deployment.

Tracking issue: see OSS-WEB workstream in GitHub issues.