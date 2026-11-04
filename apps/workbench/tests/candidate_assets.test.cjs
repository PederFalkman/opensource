"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const {webcrypto,createHash}=require("node:crypto");
const page=fs.readFileSync(path.join(__dirname,"..","verify_candidate_assets.html"),"utf8");
const script=page.match(/<script type="module">([\s\S]*?)<\/script>/)?.[1];
assert(script,"expected static verifier module");
const end=script.indexOf('$("verify").onclick');
assert(end>0,"expected user-initiated action");
const data=Buffer.from("synthetic-not-executable-wheel");
const hash=createHash("sha256").update(data).digest("hex");
const wheel="energydata_kit-0.17.0.dev0-py3-none-any.whl";
const entry={path:wheel,bytes:data.length,sha256:hash};
const base=()=>({
  schema_version:"1",status:"candidate-not-approved",
  purpose:"review-only-static-asset-inventory",
  total_bytes:data.length,assets:[entry]
});
function createContext(){
  const context=vm.createContext({
    crypto:webcrypto,URL,TextDecoder,Uint8Array,Number,
    location:{href:"http://127.0.0.1:8000/verify_candidate_assets.html",
              origin:"http://127.0.0.1:8000"}
  });
  vm.runInContext(script.slice(0,end),context);
  return context;
}
const validate=createContext().validateCandidateManifest;
function response(body,headers={}){
  const buffer=Buffer.isBuffer(body)?body:Buffer.from(JSON.stringify(body));
  return new Response(buffer,{headers});
}
test("valid candidate selects exactly one top-level wheel",()=>{
  assert.equal(validate(base()).path,wheel);
});
test("candidate manifest rejects release-like or ambiguous claims",()=>{
  for(const invalid of [
    {...base(),status:"approved"},
    {...base(),assets:[entry,entry]},
    {...base(),assets:[{...entry,path:"../"+wheel}]},
    {...base(),assets:[{...entry,bytes:0}]},
    {...base(),assets:[{...entry,sha256:"A".repeat(64)}]},
    {...base(),total_bytes:0},
  ])assert.throws(()=>validate(invalid));
});
test("end-to-end same-origin wheel digest succeeds without execution",async()=>{
  const calls=[];
  const fetchImpl=async(url,options)=>{
    calls.push({url,options});
    assert(url.startsWith("http://127.0.0.1:8000/candidate-assets/"));
    return url.endsWith("/manifest.json")?response(base()):response(data);
  };
  const result=await createContext().verifyCandidate(fetchImpl,webcrypto);
  assert.equal(result.sha256,hash);
  assert.equal(result.status,"candidate-not-approved");
  assert.equal(calls.length,2);
  assert(calls.every(call=>call.options.credentials==="omit" &&
    call.options.redirect==="error" && call.options.cache==="no-store"));
});
test("wrong wheel bytes fail closed",async()=>{
  const result=createContext().verifyCandidate(async url=>
    url.endsWith("manifest.json")?response(base()):response(Buffer.from("not the wheel")),webcrypto);
  await assert.rejects(result,/byte count|mismatch/);
});
test("streaming limit rejects larger-than-expected body before hashing",async()=>{
  const result=createContext().verifyCandidate(async url=>
    url.endsWith("manifest.json")?response(base()):
      response(Buffer.concat([data,Buffer.from("extra")])),webcrypto);
  await assert.rejects(result,/size cap|byte count/);
});
test("no remote fetch until user clicks verify",()=>{
  assert(script.indexOf('fetchImpl(manifestUrl.href')<script.indexOf('$("verify").onclick'));
  assert(!page.includes('id="csv"'));
  assert(!page.includes("unpackArchive"));
  assert(!page.includes("loadPyodide"));
});
