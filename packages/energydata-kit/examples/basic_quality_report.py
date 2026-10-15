"""Run the full quality workflow on a deterministic synthetic series.

Usage: ``python examples/basic_quality_report.py``
"""

import energydata_kit as ek


def main() -> None:
    series = ek.make_synthetic_series(
        periods=96,
        freq="15min",
        seed=42,
        drop=[10, 11, 12, 60],
        duplicate=[30],
        nan_at=[5],
        inf_at=[70],
    )
    meta = ek.MeasurementMetadata(
        name="synthetic_power",
        unit="kW",
        resolution="15min",
        aggregation="mean",
        interval_label="start",
        description="Synthetic example signal; not real data.",
    )

    report = ek.assess_quality(series, metadata=meta, bounds=(0.0, None))
    print(report.to_json())

    flagged = ek.flag_series(series, freq="15min", insert_missing=True)
    issues = flagged[flagged[ek.FLAG_COLUMN] != 0]
    print(f"\n{len(issues)} flagged rows:")
    for ts, row in issues.iterrows():
        print(f"  {ts.isoformat()}  {', '.join(ek.decode_flags(row[ek.FLAG_COLUMN]))}")


if __name__ == "__main__":
    main()
