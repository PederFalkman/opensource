"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const {createHash,webcrypto}=require("node:crypto");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const {pathToFileURL}=require("node:url");
const child=require("node:child_process");
const root=path.join(__dirname,"..");
const mod=import(pathToFileURL(path.join(root,"web09_candidate_loader.mjs")).href);
const bytes=Buffer.from("WEB09 synthetic candidate bytes");
const wheel="energydata_kit-0.17.0.dev0-py3-none-any.whl";
const entry={path:wheel,bytes:bytes.length,sha256:createHash("sha256").update(bytes).digest("hex")};
const manifest=()=>({schema_version:"1",status:"candidate-not-approved",
  purpose:"review-only-static-asset-inventory",total_bytes:bytes.length,assets:[entry]});
function response(body) {
  return new Response(Buffer.isBuffer(body)?body:JSON.stringify(body));
}
test("candidate loader verifies real SHA-256 and same-origin fetches",async()=>{
  const {fetchCandidateWheel}=await mod,calls=[];
  const result=await fetchCandidateWheel({
    baseUrl:"http://127.0.0.1:8000/web09_worker_pilot.html",
    cryptoFn:webcrypto,
    fetchFn:async(url,options)=>{
      calls.push({url,options});
      assert(url.startsWith("http://127.0.0.1:8000/candidate-assets/"));
      return response(url.endsWith("/manifest.json")?manifest():bytes);
    }
  });
  assert.equal(result.asset.sha256,entry.sha256);
  assert.equal(Buffer.from(result.bytes).toString(),bytes.toString());
  assert.equal(calls.length,2);
  assert(calls.every(x=>x.options.credentials==="omit"&&x.options.redirect==="error"));
});
test("candidate loader rejects mutated binaries and untrusted manifests",async()=>{
  const {fetchCandidateWheel}=await mod;
  const run=(manifestResult,body)=>fetchCandidateWheel({
    baseUrl:"http://127.0.0.1:8000/web09_worker_pilot.html",
    cryptoFn:webcrypto,
    fetchFn:async(url)=>response(url.endsWith("manifest.json")?manifestResult:body)
  });
  await assert.rejects(run(manifest(),Buffer.alloc(bytes.length,0)),/SHA-256 mismatch/);
  await assert.rejects(run({...manifest(),status:"approved"},bytes),/Invalid candidate manifest/);
  await assert.rejects(run({...manifest(),assets:[entry,entry]},bytes),/Exactly one/);
});
test("Web Worker and HTML have valid JavaScript syntax",()=>{
  const worker=path.join(root,"web09_engine_worker.mjs");
  const result=child.spawnSync(process.execPath,["--check",worker],{encoding:"utf8"});
  assert.equal(result.status,0,result.stderr);
  const html=fs.readFileSync(path.join(root,"web09_worker_pilot.html"),"utf8");
  const js=html.match(/<script type="module">([\s\S]*?)<\/script>/)?.[1];
  assert(js,"must have module script");
  assert.doesNotThrow(()=>new vm.Script(js.replace(
    'import {fetchCandidateWheel} from "./web09_candidate_loader.mjs";',""
  )));
});
test("worker demo uses same synthetic fixture as Workbench",()=>{
  const main=fs.readFileSync(path.join(root,"index.html"),"utf8");
  const pilot=fs.readFileSync(path.join(root,"web09_worker_pilot.html"),"utf8");
  const start=main.indexOf("function syntheticGrid() {");
  const end=main.indexOf("\nfunction downloadText(",start);
  const pstart=pilot.indexOf("function syntheticGrid() {");
  const pend=pilot.indexOf("\nfunction syntheticCsv()",pstart);
  assert(start>=0&&end>start&&pstart>=0&&pend>pstart);
  const a=vm.createContext({}),b=vm.createContext({});
  vm.runInContext(main.slice(start,end),a);
  vm.runInContext(pilot.slice(pstart,pend),b);
  assert.deepEqual(JSON.parse(JSON.stringify(a.syntheticGrid())),
                   JSON.parse(JSON.stringify(b.syntheticGrid())));
  assert(!pilot.includes('type="file"'));
});
test("worker uses internally generated fixture and refuses caller-supplied CSV",()=>{
  const worker=fs.readFileSync(path.join(root,"web09_engine_worker.mjs"),"utf8");
  const main=fs.readFileSync(path.join(root,"index.html"),"utf8");
  const pilot=fs.readFileSync(path.join(root,"web09_worker_pilot.html"),"utf8");
  const fromMain=main.slice(main.indexOf("function syntheticGrid() {"),
    main.indexOf("\nfunction downloadText(",main.indexOf("function syntheticGrid() {")));
  const fromWorker=worker.slice(worker.indexOf("function fixedSyntheticCsv() {"),
    worker.indexOf("\nfunction respond(",worker.indexOf("function fixedSyntheticCsv() {")));
  const vmMain=vm.createContext({}),vmWorker=vm.createContext({});
  vm.runInContext(fromMain,vmMain);
  vm.runInContext(fromWorker,vmWorker);
  const expected=JSON.parse(JSON.stringify(vmMain.syntheticGrid()));
  const actual=vmWorker.fixedSyntheticCsv().trim().split("\r\n").map(row=>row.split(","));
  assert.deepEqual(actual,expected);
  assert(worker.includes('Object.hasOwn(data,"csvText")'));
  assert(pilot.includes('scenario:"baseline"'));
  assert(!pilot.includes('csvText:syntheticCsv()'));
});

test("worker explicitly gates mismatched candidate digest before Pyodide import",()=>{
  const worker=fs.readFileSync(path.join(root,"web09_engine_worker.mjs"),"utf8");
  assert(worker.indexOf('actual !== data.digest') <
    worker.indexOf('await import(RUNTIME+"pyodide.mjs")'));
  assert(worker.includes('self.onmessage'));
  assert(worker.includes('ek.assess_quality'));
  assert(!worker.includes('fetch("customer'));
});
