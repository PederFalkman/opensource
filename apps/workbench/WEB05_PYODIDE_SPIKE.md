# WEB-05 experimental browser Python (Pyodide) — no publication approval

This is a **technical spike** in `experimental_pyodide.html`, not a working product claim. It is deliberately separate from the default Workbench `index.html`. The existing WEB-02 local Python CLI remains the accepted source of canonical reports.

## Reproducible manual experiment

1. Install development tools locally and build a **pure-Python wheel** of this repository's EnergyData Kit:
   `cd packages/energydata-kit && python -m pip install build && python -m build --wheel`.
2. Independently hash the locally built wheel and retain the digest alongside the build metadata. On macOS: `shasum -a 256 packages/energydata-kit/dist/energydata_kit-*.whl`; on Linux: `sha256sum packages/energydata-kit/dist/energydata_kit-*.whl`. Confirm the file was built from the intended source revision. A digest by itself **does not** authenticate source or authorship.
3. From the repository root, generate the identical synthetic CSV for the local Python baseline using the standard Workbench **Download example CSV** action. The experimental page uses its own fixed copy of that fixture, checked row-by-row in tests; there is no CSV file input.
4. Open `apps/workbench/experimental_pyodide.html` in a modern browser (a local HTTP server may be required by the runtime's fetch/CORS rules).
5. Choose the local `energydata_kit-*.whl`, paste the independently calculated SHA-256 into the hash field, and press **Load Python and analyze**. The experiment generates its own fixed synthetic readings; it cannot accept customer CSV uploads. A mismatched or missing wheel checksum must be rejected **before loading any Pyodide runtime**.
6. Inspect error/status output. If a canonical v2 report appears, download it and compare it with the local Python result from `python_report.py` using the offline exact-field comparator:\n\n   `python apps/workbench/compare_parity.py local-report.json synthetic-pyodide-report.json`\n\n   Exit code 0 means canonical field equality; 1 indicates differences and 2 means invalid input. Any difference blocks adoption. This is not source authentication.

## Optional real-Chromium smoke gate (synthetic only)

From the repository root, in an environment where `energydata-kit` is installed from the local source:

```bash
python -m pip install -e packages/energydata-kit playwright
python -m playwright install chromium
python -m pip install build
cd packages/energydata-kit
python -m build --wheel
cd ../..
python apps/workbench/browser_parity_smoke.py --wheel packages/energydata-kit/dist/energydata_kit-*.whl
```

The harness automatically launches a loopback-only static server, obtains the exact browser synthetic fixture, creates a local authoritative Python report, and launches Chromium against the experimental Pyodide page. It verifies that the two in-browser fixture generators agree on every row and that only a wheel file picker exists. It selects the trusted local wheel, checks its SHA-256 before runtime import and compares **every canonical report field** after the browser run. Results include runtime duration, page errors, observed external hostnames, and suspicious outbound request bodies. A return code of zero requires no canonical diffs, page errors or detected payload requests.

**Limitations:** This is a manual experiment, not a scheduled or PR-triggered CI job. Network access is required for CDN packages. Request-body inspection is a narrow heuristic, **not a complete network/privacy audit**. It does not measure peak browser memory, byte-accurate transfer cost, browser matrix compatibility, or prove wheel authenticity. Document those separately before publication. Neither the script nor the experimental page accepts customer CSV input.

## Expanded synthetic scenario parity gate

The experimental page now exposes four **hard-coded, synthetic-only** cases in a selector: `baseline`, `dst_fall`, `dst_spring`, and `mixed_offsets`. The browser smoke harness runs all four cases sequentially in the same Chromium session, using the actual EnergyData Kit wheel and comparing every canonical report field to the local Python adapter. This exercises reuse of a warm runtime as well as mixed ISO 8601 offsets and repeated local wall-clock times. Each case reports its own measured elapsed time.

The fixture selector cannot import CSV files. The baseline scenario remains byte-for-byte equivalent in value content to the main Workbench example. **The browser experiment is still not ready for release**: multiple supported browsers, offline package integrity, network transfer size and memory limits are unverified.

## Runtime and dependencies

- Candidate Pyodide `0.29.5`, fixed CDN version path; binary assets load from jsDelivr, Python packages may load from PyPI or the Pyodide distribution.
- `numpy`, `pandas`, `micropip` are loaded through Pyodide, and `pint==0.24.4` via micropip.
- `pyodide.unpackArchive` unpacks the explicitly selected wheel into the interpreter's site-packages directory. **This is not equivalent to an audited package manager install**; dependencies are installed separately.
- The experimental wheel must be built from *trusted source* and should be inspected before execution. A user-supplied SHA-256 is checked before runtime loading; this is a file-equality check, not an independent signature or provenance attestation. The wheel is executable Python, not inert report data.
- Browser-only computation does **not** imply offline execution: first-run third-party runtime/dependency downloads require a network connection. It also does not imply a privacy audit: loaded third-party code must be independently reviewed.

## Verification matrix (all pending until measured)

| Requirement | Proof required |
|---|---|
| Runtime/dependency compatibility | Actual browser result from shipped wheel, exact version logs |
| Canonical report parity | Same synthetic CSV compared field-by-field with Python CLI, not merely matching headline metrics |
| Winter and fall DST offsets | Same gap and duplicate treatment as the Python adapter |
| CSV parse abuse | Malformed quotes, nonnumeric values, ambiguous wall time and size refusal |
| Network boundary | Inspect outgoing requests in browser devtools; no CSV/wheel payloads sent |
| Performance | Cold start, warm run, total transferred bytes, peak memory, supported browser/device |
| Accessibility | Keyboard navigation, focus, status and errors tested manually |
| Supply chain/IP | Confirm SHA-256 of local wheel before running; pin third-party asset hashes or self-host an approved bundle; review licenses |

**Go/no-go:** Do not add a link from the main Workbench or deploy externally until all checks pass. A green Node syntax test proves only syntax and explicit-action wiring, *not* Pyodide execution or report parity. Any failure keeps the local Python CLI + report import workflow as the supported path.
