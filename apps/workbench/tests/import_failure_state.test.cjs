"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
const begin=html.indexOf("function clearPreviewAfterImportFailure(message){");
const end=html.indexOf('\n$("upload").onclick',begin);
assert(begin>=0&&end>begin,"expected failed-CSV-import cleanup in HTML");
const ids=["total","missing","duplicates","invalid","timestampIssues",
  "missingStatus","duplicateStatus","invalidStatus","source","chart","error"];
const elements=Object.fromEntries(ids.map(id=>[id,{textContent:"OLD DATA"}]));
const context=vm.createContext({elements});
vm.runInContext('let rows=[1,2],report={engine:"browser-preview"},filename="old.csv"; const $=id=>elements[id];',context);
vm.runInContext(html.slice(begin,end),context);

test("failed import invalidates stale browser-preview data and export state",()=>{
  vm.runInContext('clearPreviewAfterImportFailure("CSV malformed")',context);
  assert(vm.runInContext("rows.length===0 && report===null && filename==='' ",context));
  for(const id of ids.slice(0,8))assert.equal(elements[id].textContent,"—");
  assert.equal(elements.source.textContent.includes("No dataset loaded"),true);
  assert.equal(elements.chart.textContent,"No data selected");
  assert.equal(elements.error.textContent,"CSV malformed");
});
