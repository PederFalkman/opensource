# EnergyData Kit — Online Workbench (prototype)

A static, offline-first browser demo for the open-source `energydata-kit` package. Visual direction follows Solid Soup's demo system: deep green/charcoal, white surfaces, quiet mint accents, strict grid and minimal UI.

## Run locally

Open `index.html` in a modern browser, or serve this directory with `python -m http.server 8080` and navigate to `http://localhost:8080`. No dependencies, analytics, uploads or network services are used.

## Prototype features

- Local CSV import (up to 5 MB) including basic quoted-field handling.
- Deterministic synthetic power dataset with missing intervals, one duplicate instant and a missing value.
- Timestamp and value-column selection, expected interval selection.
- Basic browser-only quality diagnostics; visual series preview; JSON export.
- Explicit warning that browser checks are not equivalent to the Python library.

## Constraints

This prototype requires explicit ISO-8601 UTC offsets or Z; it does not support local ambiguous timestamps, full DST interval semantics, metadata-based units, known-outage policies, flagged CSV or the authoritative `assess_frame`/quality-report schema. It assumes expected evenly spaced observations. It is **not** operational or engineering assurance software.

## Planned authoritative integration

1. Define a stable, versioned adapter matching released `energydata-kit` assessment and report APIs (do not reimplement Python validation in TypeScript).
2. Prefer **local WASM/Pyodide** only after feasibility and dependency-size testing; otherwise use a minimal sandboxed Python HTTP backend with strict upload limits, no retention, no MICA access, and explicit consent to transfer data.
3. Separate `demo-preview` from `python-validated` states, with visible engine/version and report provenance.
4. Add local-calendar DST tests, multi-series reports, metadata form, known outages, and accessible data tables.
5. Host only after threat modeling, accessibility, legal/IP and publication review. No automatic deployment.

Tracking issue: see OSS-WEB workstream in GitHub issues.