"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const start = html.indexOf("function syntheticGrid() {");
const end = html.indexOf("\nfunction downloadText(", start);
assert(start >= 0 && end > start, "expected synthetic fixture function");
const context = vm.createContext({});
vm.runInContext(html.slice(start, end), context);
const dataset = JSON.parse(JSON.stringify(context.syntheticGrid()));
test("example data can be reused for Python and browser", () => {
  assert.deepEqual(dataset[0], ["timestamp","power_kw"]);
  assert.equal(dataset.length, 96); // header + 95 measurements, including duplicate
  assert.equal(dataset.length - 1 - new Set(dataset.slice(1).map(r => r[0])).size, 1);
  assert.equal(dataset.filter(r => r[1] === "").length, 1);
  assert.equal(new Set(dataset.slice(1).map(r=>r[0])).size, 94);
  assert.equal(dataset[1][0], "2026-10-19T00:00:00.000Z");
});
test("two consecutive 15-minute slots absent in synthetic fixture", () => {
  const times = new Set(dataset.slice(1).map(r=>r[0]));
  const start = Date.UTC(2026, 9, 19, 0, 0);
  assert.equal(times.has(new Date(start + 28*900000).toISOString()), false);
  assert.equal(times.has(new Date(start + 29*900000).toISOString()), false);
});
