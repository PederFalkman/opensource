"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const {webcrypto,createHash}=require("node:crypto");
const {pathToFileURL}=require("node:url");
const path=require("node:path");
const modulePromise=import(pathToFileURL(path.resolve(__dirname,"../web09_candidate_loader.mjs")).href);
const wheel=Buffer.from("synthetic WEB11 wheel bytes, not executable");
const name="energydata_kit-0.17.0.dev0-py3-none-any.whl";
const asset={path:name,bytes:wheel.length,sha256:createHash("sha256").update(wheel).digest("hex")};
const manifest=JSON.stringify({schema_version:"1",status:"candidate-not-approved",
  purpose:"review-only-static-asset-inventory",total_bytes:wheel.length,assets:[asset]});
const pin=createHash("sha256").update(Buffer.from(manifest)).digest("hex");
function response(bytes){return new Response(bytes)}

test("review-pin loader fetches only after correctly verifying manifest and wheel",async()=>{
  const {fetchReviewPinnedCandidateWheel}=await modulePromise,calls=[];
  const result=await fetchReviewPinnedCandidateWheel({
    baseUrl:"http://127.0.0.1:8000/web09_worker_pilot.html",
    cryptoFn:webcrypto,expectedManifestSha256:pin,
    fetchFn:async(url)=>{
      calls.push(url);
      return response(url.endsWith("manifest.json")?Buffer.from(manifest):wheel);
    }
  });
  assert.equal(result.asset.sha256,asset.sha256);
  assert.equal(calls.length,2);
});

test("missing and malformed independent pins reject without network fetch",async()=>{
  const {fetchReviewPinnedCandidateWheel}=await modulePromise;
  let requests=0;
  const fetchFn=async()=>{requests++;return response(Buffer.from(manifest))};
  for(const bad of [undefined,null,"x","0".repeat(63),"A".repeat(64)]){
    await assert.rejects(fetchReviewPinnedCandidateWheel({
      baseUrl:"http://127.0.0.1:8000/web09_worker_pilot.html",
      cryptoFn:webcrypto,expectedManifestSha256:bad,fetchFn
    }),/independently reviewed manifest/);
  }
  assert.equal(requests,0);
});

test("manifest tampering prevents wheel fetch even if wheel SHA is unchanged",async()=>{
  const {fetchReviewPinnedCandidateWheel}=await modulePromise;
  const badManifest=Buffer.from(manifest.replace("candidate-not-approved","approved-but-false"));
  let requests=0;
  await assert.rejects(fetchReviewPinnedCandidateWheel({
    baseUrl:"http://127.0.0.1:8000/web09_worker_pilot.html",
    cryptoFn:webcrypto,expectedManifestSha256:pin,
    fetchFn:async(url)=>{
      requests++;
      return response(url.endsWith("manifest.json")?badManifest:wheel);
    }
  }),/Reviewed manifest SHA-256 mismatch/);
  assert.equal(requests,1,"no binary fetch after manifest mismatch");
});

test("reviewed hash rejects a different valid candidate manifest",async()=>{
  const {verifyManifestReviewPin}=await modulePromise;
  const second=Buffer.from(manifest.replace("0.17.0.dev0","0.17.1"));
  await assert.rejects(verifyManifestReviewPin(second,pin,webcrypto),/mismatch/);
});

test("cross-origin browser asset base and embedded credentials fail before network",async()=>{
  const {fetchReviewPinnedCandidateWheel}=await modulePromise;
  const original=Object.getOwnPropertyDescriptor(globalThis,"location");
  let requests=0;
  try{
    Object.defineProperty(globalThis,"location",{
      configurable:true,value:{origin:"https://workbench.example"}
    });
    const fetchFn=async()=>{requests++;return response(Buffer.from(manifest))};
    await assert.rejects(fetchReviewPinnedCandidateWheel({
      baseUrl:"https://untrusted.example/web09_worker_pilot.html",
      expectedManifestSha256:pin,cryptoFn:webcrypto,fetchFn
    }),/current page origin/);
    await assert.rejects(fetchReviewPinnedCandidateWheel({
      baseUrl:"https://user:secret@workbench.example/web09_worker_pilot.html",
      expectedManifestSha256:pin,cryptoFn:webcrypto,fetchFn
    }),/Credential-bearing asset URL/);
    assert.equal(requests,0);
  }finally{
    if(original)Object.defineProperty(globalThis,"location",original);
    else delete globalThis.location;
  }
});
