import test from "node:test";
import assert from "node:assert/strict";
import {createSyntheticEvidence} from "../web14_evidence.mjs";
const output={engine:"python-validated",source:"web09-synthetic-only",
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
