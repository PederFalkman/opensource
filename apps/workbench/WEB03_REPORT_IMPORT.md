# WEB-03: Offline quality-report import contract

The Workbench remains a static, offline-first browser prototype. The browser preview never becomes authoritative. A user can import an external canonical EnergyData Kit v2 JSON report; the import panel displays only selected fields after structural checks.

## Accepted forms

- Plain canonical `QualityReport.to_dict()` with `schema_version: "2"`.
- The exact `energydata.workbench.python.v1` wrapper containing `engine: "python-validated"`, `package_version`, and its canonical `report`.

Only canonical v2 counters and supported metadata are checked. The viewer does **not** require invented fields outside the canonical schema.

## Safety

Imported JSON is **not authenticated**. A user can alter it or fabricate metrics and a plausible fingerprint; structural validation is not cryptographic proof. Never use the browser preview or an unverified imported report as scientific/operational assurance. No server, uploads, cookies or hidden persistence are introduced.

Checks include non-negative integer counters, finite bounded completeness, optional positive flag counts, gap-list shape, optional gap-count consistency, wrapper version consistency, and fingerprint shape when present. Rendering uses DOM `textContent` for user-controlled strings. A 2 MiB import-size limit remains in place.

## Automated tests

Run `node --test apps/workbench/tests/report_reader.test.cjs` from the repository root. The tests extract the actual inline reader from `index.html`, rather than maintaining a separate shadow validator. The Python adapter tests remain `python -m pytest -q apps/workbench/tests/test_python_report.py` in an environment with EnergyData Kit installed. CI includes both under the Python 3.12 matrix entry.

## Not done

This is **not** an embedded Python runtime, data authentication service, scientific validation, or a public deployment. Evaluate WASM/Pyodide, performance, dependency weight, offline behavior and IP/privacy gates separately before implementation.
