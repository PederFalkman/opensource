import test from "node:test";
import assert from "node:assert/strict";
import {createSyntheticEvidence} from "../web14_evidence.mjs";
const output={engine:"python-validated",source:"web09-synthetic-only",
 package_version:"0.17.0.dev0",privacy:"browser-worker-synthetic",interval_minutes:15,
 columns:{timestamp:"timestamp",value:"power_kw"},
 report:{schema_version:"2",n_rows:95,n_missing_intervals:2,n_duplicate_timestamps:1,
 n_expected_intervals:96,n_missing_explained:0,completeness:0.98}};
const input={scenario:"baseline",wheelSha256:"a".repeat(64),elapsedMs:1234.6,output};
test("creates explicitly unattested synthetic evidence",()=>{
 const item=createSyntheticEvidence(input);
 assert.equal(item.elapsed_ms,1235);
 assert.equal(item.scenario,"baseline");
 assert.equal(item.status,"internal-unattested-synthetic-only");
 assert.equal(item.result,output);
 assert.equal(item.wheel_sha256,"a".repeat(64));
 assert.equal(item.limitations.length,4);
});
test("rejects unsupported scenario and wrong wheel hash",()=>{
 assert.throws(()=>createSyntheticEvidence({...input,scenario:"customer.csv"}),/synthetic/);
 assert.throws(()=>createSyntheticEvidence({...input,wheelSha256:"0"}),/SHA-256/);
 assert.throws(()=>createSyntheticEvidence({...input,wheelSha256:"A".repeat(64)}),/SHA-256/);
});
test("rejects negative non-finite or extreme duration",()=>{
 for(const ms of [-1,NaN,Infinity,3_600_001])
   assert.throws(()=>createSyntheticEvidence({...input,elapsedMs:ms}),/duration/);
});
test("refuses contradictory or forged canonical quality reports",()=>{
 assert.throws(()=>createSyntheticEvidence({...input,output:{
  ...output,report:{...output.report,n_duplicate_timestamps:200}
 }}),/Inconsistent canonical/);
 assert.throws(()=>createSyntheticEvidence({...input,output:{
  ...output,source:"operational-file.csv"
 }}),/synthetic Python/);
 assert.throws(()=>createSyntheticEvidence({...input,output:{
  ...output,report:{...output.report,n_missing_intervals:999}
 }}),/Inconsistent canonical/);
});

test("rejects unknown wrapper metadata and oversized evidence",()=>{
 assert.throws(()=>createSyntheticEvidence({...input,output:{...output,customer_path:"/private/data.csv"}}),/Unexpected Python result metadata/);
 assert.throws(()=>createSyntheticEvidence({...input,output:{...output,
   report:{...output.report,fingerprint:"x".repeat(270000)}
 }}),/256 KiB/);
});
test("rejects non-synthetic provenance, interval or column selections",()=>{
 assert.throws(()=>createSyntheticEvidence({...input,output:{...output,privacy:"local-file-only"}}),/provenance/);
 assert.throws(()=>createSyntheticEvidence({...input,output:{...output,interval_minutes:60}}),/provenance/);
 assert.throws(()=>createSyntheticEvidence({...input,output:{...output,
   columns:{timestamp:"time",value:"power_kw"}}}),/provenance/);
});

test("bounded evidence accepts a compact synthetic report",()=>{
 const small=createSyntheticEvidence({...input,output:{...output,
   report:{...output.report,fingerprint:"f".repeat(128)}
 }});
 assert.equal(small.status,"internal-unattested-synthetic-only");
});
