"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");

const page=fs.readFileSync(path.resolve(__dirname,"../index.html"),"utf8");
const first=page.indexOf("const MAX_CSV_BYTES =");
const last=page.indexOf("\nfunction setData(",first);
assert(first>=0&&last>first,"Expected bounded CSV parser in Workbench");
const context=vm.createContext({});
vm.runInContext(page.slice(first,last),context);
const parse=context.csvParse;

test("well-formed CSV, quoted commas and CRLF remain supported",()=>{
  assert.deepEqual(JSON.parse(JSON.stringify(parse(
    'timestamp,power_kw,comment\r\n2026-01-01T00:00:00Z,3,"good,quoted"\r\n'
  ))),[
    ["timestamp","power_kw","comment"],
    ["2026-01-01T00:00:00Z","3","good,quoted"]
  ]);
});
test("rejects oversized text and NUL controls",()=>{
  assert.throws(()=>parse("a".repeat(5*1024*1024+1)),/5 MiB/);
  assert.throws(()=>parse("timestamp,value\n2026-01-01T00:00:00Z,\0"),/NUL/);
});
test("rejects oversized CSV fields in quoted and unquoted cells",()=>{
  const field="a".repeat(16385);
  assert.throws(()=>parse("a,b\n"+field+",1"),/16,384/);
  assert.throws(()=>parse('a,b\n"'+field+'",1'),/16,384/);
});
test("rejects more than 128 columns",()=>{
  assert.throws(()=>parse(Array.from({length:129},(_,i)=>"c"+i).join(",")),/128 columns/);
});
test("accepts 50,000 data rows and rejects the next row",()=>{
  const base="time,value\n";
  const row="2026-01-01T00:00:00Z,1\n";
  const accepted=parse(base+row.repeat(50000));
  assert.equal(accepted.length,50001);
  assert.throws(()=>parse(base+row.repeat(50001)),/50,000 data rows/);
});
test("file import requires fatal UTF-8 and preserves failure reset",()=>{
  assert(page.includes('new TextDecoder("utf-8",{fatal:true})'));
  assert(page.includes("clearPreviewAfterImportFailure(err.message)"));
  assert(page.includes("MAX_CSV_BYTES"));
  assert(!page.includes("csvParse(await f.text())"));
});
