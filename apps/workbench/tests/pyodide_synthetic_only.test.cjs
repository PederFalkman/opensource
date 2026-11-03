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
