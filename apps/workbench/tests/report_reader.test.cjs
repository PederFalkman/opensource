"use strict";
// Read the exact browser validator from the offline HTML: no duplicated logic.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const begin = source.indexOf("function readCanonicalReport(input) {");
const end = source.indexOf('\n$("loadPython").onclick', begin);
assert(begin >= 0 && end > begin, "expected canonical reader in index.html");
const context = vm.createContext({});
vm.runInContext(source.slice(begin, end), context);
const read = context.readCanonicalReport;
function base() {
  return {
    schema_version: "2",
    package_version: "0.17.0.dev0",
    n_rows: 4, n_missing_intervals: 1, n_duplicate_timestamps: 1,
    n_expected_intervals: 4, n_missing_explained: 0,
    n_gaps: 1, gaps: [{start: "2026-01-01T00:30:00Z", end: "2026-01-01T00:30:00Z", missing_count: 1}],
    completeness: 0.75,
    flag_counts: {"DUPLICATE_TIMESTAMP": 1},
    fingerprint: "a".repeat(64)
  };
}
test("unwrapped canonical report is supported", () => {
  assert.equal(read(base()).report.n_rows, 4);
});
test("canonical Python adapter wrapper is supported", () => {
  const r = base();
  assert.equal(read({report:r, engine:"python-validated",
    adapter_version:"energydata.workbench.python.v1",package_version:r.package_version,
    source:"sample.csv"}).source, "sample.csv");
});
test("reject invalid and inconsistent reports", () => {
  const cases = [
    {...base(), n_rows:-1},
    {...base(), n_duplicate_timestamps:5},
    {...base(), n_missing_intervals:5},
    {...base(), n_missing_explained:2},
    {...base(), completeness:1.2},
    {...base(), completeness:NaN},
    {...base(), flag_counts:{DUPLICATE_TIMESTAMP:-1}},
    {...base(), gaps:"not an array"},
    {...base(), n_gaps:0},
    {...base(), fingerprint:"not-sha256"},
    {report:base(),engine:"browser-preview",adapter_version:"energydata.workbench.python.v1",
     package_version:"0.17.0.dev0"},
    {report:base(),engine:"python-validated",adapter_version:"energydata.workbench.python.v1",
     package_version:"wrong"}
  ];
  for (const r of cases) assert.throws(() => read(r));
});
test("missing optional counters in canonical report do not require custom keys", () => {
  const r = base();
  delete r.fingerprint;
  delete r.n_gaps;
  delete r.n_expected_intervals;
  assert.equal(read(r).package_version,r.package_version);
});
