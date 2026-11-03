"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const {webcrypto,createHash}=require("node:crypto");

const html=fs.readFileSync(path.join(__dirname,"..","experimental_pyodide.html"),"utf8");
const start=html.indexOf("async function validateWheelDigest(wheelBytes, expectedHash) {");
const end=html.indexOf('\n$("run").onclick',start);
assert(start>=0&&end>start,"browser wheel verifier must exist");
const context=vm.createContext({crypto:webcrypto,ArrayBuffer,Uint8Array});
vm.runInContext(html.slice(start,end),context);
const verify=context.validateWheelDigest;
const bytes=Uint8Array.from(Buffer.from("synthetic-wheel-test-data","utf8")).buffer;
const expected=createHash("sha256").update(Buffer.from(bytes)).digest("hex");

test("valid wheel digest is accepted without loading Python", async()=>{
  assert.equal(await verify(bytes,expected.toUpperCase()),expected);
});
test("modified digest is rejected",async()=>{
  await assert.rejects(verify(bytes,"0".repeat(64)),/mismatch/);
});
test("missing and malformed digests are rejected",async()=>{
  await assert.rejects(verify(bytes,""),/64-character/);
  await assert.rejects(verify(bytes,"not-a-sha"),/64-character/);
});
test("unavailable SubtleCrypto is an explicit fail-closed condition",async()=>{
  const restricted=vm.createContext({crypto:{},ArrayBuffer,Uint8Array});
  vm.runInContext(html.slice(start,end),restricted);
  await assert.rejects(restricted.validateWheelDigest(bytes,expected),/unavailable/);
});
test("wheel digest validation precedes external runtime import",()=>{
  const script=html.match(/<script type="module">([\s\S]*?)<\/script>/)[1];
  const hashStep=script.indexOf('await validateWheelDigest(wheelBytes, $("wheelHash").value)');
  const runtimeStep=script.indexOf('await import(RUNTIME+"pyodide.mjs")');
  assert(hashStep>=0&&runtimeStep>hashStep,"digest must be checked before runtime loading");
});
