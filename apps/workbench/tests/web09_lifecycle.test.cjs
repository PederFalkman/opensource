"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const pilot=fs.readFileSync(path.join(__dirname,"..","web09_worker_pilot.html"),"utf8");
const moduleSource=pilot.match(/<script type="module">([\s\S]*?)<\/script>/)?.[1];
assert(moduleSource,"WEB-09 inline pilot module must exist");
const source=moduleSource.replace(
  'import {fetchCandidateWheel} from "./web09_candidate_loader.mjs";',""
);
const digest="f".repeat(64);
const flush=()=>new Promise(resolve=>setImmediate(resolve));

function harness(fetchOverride) {
  const elements={};
  for(const id of ["run","cancel","result","status","scenario"]) {
    elements[id]={disabled:id==="cancel",textContent:"",value:"baseline",onclick:null};
  }
  elements.result.textContent="No report.";
  elements.status.textContent="Not started.";
  const workers=[];
  class FakeWorker {
    constructor() {
      this.terminated=false;
      this.sent=[];
      this.onmessage=null;
      this.onerror=null;
      workers.push(this);
    }
    postMessage(data) {this.sent.push(data)}
    terminate() {this.terminated=true}
    emit(data) {this.onmessage?.({data})}
  }
  const fetchCandidateWheel=fetchOverride??(async()=>({
    bytes:Uint8Array.from([1,2,3]),
    asset:{sha256:digest}
  }));
  const context=vm.createContext({
    document:{getElementById:id=>elements[id]},
    location:{href:"http://127.0.0.1:8000/web09_worker_pilot.html"},
    AbortController,Worker:FakeWorker,Date,Math,
    fetchCandidateWheel,URL
  });
  vm.runInContext(source,context);
  return {elements,workers,context};
}

test("cancel during pending manifest fetch aborts and rejects late candidate resolution",async()=>{
  let settle;
  let capturedSignal;
  const pending=new Promise(resolve=>{settle=resolve});
  const h=harness(({signal})=>{capturedSignal=signal;return pending});
  const running=h.elements.run.onclick();
  assert.equal(h.elements.run.disabled,true);
  h.elements.cancel.onclick();
  assert.equal(capturedSignal.aborted,true);
  assert.equal(h.elements.status.textContent.startsWith("Cancelled"),true);
  assert.equal(h.elements.result.textContent,"No report.");
  settle({bytes:Uint8Array.of(1),asset:{sha256:digest}});
  await running;
  assert.equal(h.workers.length,0,"cancelled fetch must not create worker");
  assert.equal(h.elements.result.textContent,"No report.");
  assert.equal(h.elements.run.disabled,false);
});

test("terminated worker cannot overwrite cancellation, and retry starts a new worker",async()=>{
  const h=harness();
  await h.elements.run.onclick();
  const first=h.workers[0];
  assert.equal(first.sent.length,1);
  assert.equal(first.sent[0].scenario,"baseline");
  const oldId=first.sent[0].id;
  first.emit({id:oldId,stage:"loading",detail:"Loading Python"});
  h.elements.cancel.onclick();
  assert.equal(first.terminated,true);
  const cancelled=h.elements.status.textContent;
  first.emit({id:oldId,stage:"complete",result:{report:{schema_version:"2"}}});
  first.emit({id:oldId,stage:"error",error:"obsolete error"});
  assert.equal(h.elements.status.textContent,cancelled);
  assert.equal(h.elements.result.textContent,"No report.");
  await h.elements.run.onclick();
  const second=h.workers[1];
  assert(second && second!==first);
  const nextId=second.sent[0].id;
  assert.notEqual(nextId,oldId);
  first.emit({id:oldId,stage:"complete",result:{report:{schema_version:"2"}}});
  assert.equal(h.elements.result.textContent,"No report.");
  second.emit({id:nextId,stage:"complete",result:{report:{schema_version:"2"},source:"synthetic"}});
  assert.match(h.elements.status.textContent,/canonical v2 report/);
  assert.match(h.elements.result.textContent,/"synthetic"/);
  assert.equal(h.elements.run.disabled,false);
});

test("worker runtime error cleans up and permits retry",async()=>{
  const h=harness();
  await h.elements.run.onclick();
  const failed=h.workers[0];
  failed.emit({id:failed.sent[0].id,stage:"error",error:"Python initialization failed"});
  assert.equal(failed.terminated,true);
  assert.match(h.elements.status.textContent,/Python initialization failed/);
  assert.equal(h.elements.run.disabled,false);
  await h.elements.run.onclick();
  assert.equal(h.workers.length,2);
});

test("failed candidate fetch never creates worker or runs Python",async()=>{
  const h=harness(async()=>{throw Error("Wheel checksum mismatch")});
  await h.elements.run.onclick();
  assert.equal(h.workers.length,0);
  assert.match(h.elements.status.textContent,/Wheel checksum mismatch/);
  assert.equal(h.elements.run.disabled,false);
});
