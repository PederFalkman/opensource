"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.join(__dirname,"..");
const main=fs.readFileSync(path.join(root,"index.html"),"utf8");
const experimental=fs.readFileSync(path.join(root,"experimental_pyodide.html"),"utf8");
function extract(html, startText, endText) {
  const start=html.indexOf(startText), end=html.indexOf(endText,start);
  assert(start>=0 && end>start, "expected fixture function not found");
  return html.slice(start,end);
}
const mainSrc=extract(main,"function syntheticGrid() {","\nfunction downloadText(");
const experimentSrc=extract(experimental,"function experimentSyntheticGrid() {","\nfunction syntheticCsvText()");
const ctx=vm.createContext({});
vm.runInContext(mainSrc+"\n"+experimentSrc,ctx);
const scenarioSrc=extract(experimental,"function syntheticScenarioGrid(scenario) {","\n// Synthetic-only inspection hook");
vm.runInContext(scenarioSrc,ctx);
vm.runInContext('const $ = () => ({value:"baseline"});',ctx);
test("experimental Pyodide fixture matches default Workbench row by row",()=>{
  const a=JSON.parse(JSON.stringify(ctx.syntheticGrid()));
  const b=JSON.parse(JSON.stringify(ctx.experimentSyntheticGrid()));
  assert.deepEqual(b,a);
  assert.equal(b.length,96);
});
test("experimental Pyodide page cannot accept customer CSV uploads",()=>{
  assert(!experimental.includes('id="csv"'));
  assert(!experimental.includes('set_input_files'));
  const inputs=[...experimental.matchAll(/<input\s+[^>]*type="file"/g)];
  assert.equal(inputs.length,1,"only explicitly selected wheel may be uploaded");
});
test("synthetic CSV conversion is deterministic",()=>{
  const snippet=extract(experimental,"function syntheticCsvText() {","\nasync function validateWheelDigest(");
  vm.runInContext(snippet,ctx);
  const csv=ctx.syntheticCsvText();
  assert(csv.startsWith("timestamp,power_kw\r\n"));
  assert.equal(csv.trim().split("\r\n").length,96);
});

test("DST and mixed-offset fixture instants are explicit and distinct",()=>{
  const begin=experimental.indexOf("function syntheticScenarioGrid(scenario) {");
  const end=experimental.indexOf("\n// Synthetic-only inspection hook",begin);
  assert(begin>=0&&end>begin,"expected scenario fixture function");
  vm.runInContext(experimental.slice(begin,end),ctx);
  for(const name of ["dst_fall","dst_spring","mixed_offsets"]){
    const grid=JSON.parse(JSON.stringify(ctx.syntheticScenarioGrid(name)));
    assert.equal(grid[0][0],"timestamp");
    assert(grid.length>=5);
    const timestamps=grid.slice(1).map(row=>Date.parse(row[0]));
    assert(timestamps.every(Number.isFinite));
    assert.equal(new Set(timestamps).size,timestamps.length);
  }
  const fall=JSON.parse(JSON.stringify(ctx.syntheticScenarioGrid("dst_fall")));
  assert(fall.some(row=>row[0].includes("+02:00")));
  assert(fall.some(row=>row[0].includes("+01:00")));
  assert.throws(()=>ctx.syntheticScenarioGrid("customer"),/Unknown synthetic/);
});
