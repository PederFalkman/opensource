# EnergyData Kit — first five minutes

A short, honest entry point to Solid Soup Open Engineering. **No account, cloud service, customer data or Solid Soup commercial software required.** This guide is documentation, not a claim that the web prototype runs the Python engine.

## Choose your route

### Route A: Try the browser prototype (no installation)

1. Open [the workbench source](../../apps/workbench/index.html) in this repository.
2. Download `index.html` and open it locally in a modern browser.
3. Click **Load example dataset**. The dataset is synthetic and includes gaps, a duplicate timestamp and a missing value.
4. Inspect the four quality metrics and line chart; export the JSON preview if useful.

**Important:** This interface currently uses simplified browser-side checks. Its JSON is labelled `browser-preview` and must not be confused with a verified EnergyData Kit quality report. Full timezone/DST semantics, units and report comparisons belong to the Python library. There is no hosted deployment.

### Route B: Run the real Python package locally

Requires Python 3.11+ and a terminal.

```bash
git clone https://github.com/Solid-soup/opensource.git
cd opensource/packages/energydata-kit
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install .
```

Then save this as `example.py` in the current directory:

```python
import pandas as pd
import energydata_kit as ek

idx = pd.date_range("2026-01-01", periods=8, freq="15min", tz="UTC")
idx = idx.delete(3)  # deliberate missing interval
readings = pd.Series(range(len(idx)), index=idx, name="power_kw")
report = ek.assess_quality(readings, freq="15min")
print(report.to_json())
```

Run `python example.py`. The report is created locally and does not alter the measurements.

**For real data:** Use the documented `energydata-kit report` CLI, including explicit timestamp column, time zone and measurement semantics. Read the [package documentation](../../packages/energydata-kit/README.md) for CSV/Parquet, DST ambiguity, quality flags, units and reproducible reports.

## What this project is — and is not

EnergyData Kit validates time-series measurements. It is **not** a forecasting engine, electrical network solver, connection strategy product or automatic data-repair service. It intentionally keeps missing values and suspicious measurements visible instead of silently changing data.

The open-source package is Apache-2.0 licensed; the released artifacts are available on [GitHub releases](https://github.com/Solid-soup/opensource/releases), but not on PyPI. Do not use `pip install energydata-kit` assuming it comes from this repository.

## For contributors

Start with the [existing-tools audit](../architecture/EXISTING_TOOLS_AUDIT.md), [IP boundary](../governance/IP_BOUNDARY.md) and [contribution guide](../../CONTRIBUTING.md). Improvements to documentation, interoperability and clearly justified data-quality gaps are welcome; MICA's proprietary algorithms, customer data and operating policies are not.
