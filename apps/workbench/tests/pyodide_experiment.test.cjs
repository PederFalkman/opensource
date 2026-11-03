"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const cp = require("node:child_process");

const html = fs.readFileSync(path.join(__dirname, "..", "experimental_pyodide.html"),"utf8");
const match = html.match(/<script type="module">([\s\S]*?)<\/script>/);
assert(match, "experimental page must have a module script");
test("experimental Pyodide module parses as modern JavaScript", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "edk-pyodide-"));
  try {
    const file = path.join(dir, "probe.mjs");
    fs.writeFileSync(file, match[1], "utf8");
    const result = cp.spawnSync(process.execPath, ["--check",file], {encoding:"utf8"});
    assert.equal(result.status,0,result.stderr);
  } finally {fs.rmSync(dir,{recursive:true,force:true})}
});
test("no Python engine is loaded before explicit user action", () => {
  assert(html.includes(' $("run").onclick=async()=>') ||
         html.includes('$("run").onclick=async()=>'));
  const script = match[1];
  assert(script.indexOf('await import(RUNTIME+"pyodide.mjs")') >
         script.indexOf('$("run").onclick=async()=>'));
  assert(html.includes("This isolated prototype"));
  assert(html.includes("Use synthetic, non-sensitive CSV files only"));
});
test("real Python package API is invoked, not JS approximation", () => {
  assert(html.includes("ek.assess_quality(series"));
  assert(html.includes('schema_version'));
  assert(!html.includes("XMLHttpRequest"));
});
