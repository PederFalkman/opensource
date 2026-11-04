import test from "node:test";
import assert from "node:assert/strict";
import {SCENARIOS,scenarioAllowed,safeReport,freshState,transition} from "../web13_pilot_state.mjs";
const payload={engine:"python-validated",source:"web09-synthetic-only",
  report:{schema_version:"2",n_rows:95,n_missing_intervals:2,n_duplicate_timestamps:1,completeness:0.97}};
test("only four fixed scenarios are accepted",()=>{
  assert.equal(SCENARIOS.length,4);
  for(const scenario of SCENARIOS)assert.equal(scenarioAllowed(scenario),true);
  for(const scenario of ["customer.csv","../private","",null,42])
    assert.equal(scenarioAllowed(scenario),false);
});
test("progress and validated completion",()=>{
  let s=transition(freshState(),{type:"start",id:"a-1",scenario:"baseline"});
  assert.equal(s.stage,"verifying");
  s=transition(s,{type:"loading",id:"a-1"});assert.equal(s.stage,"loading");
  s=transition(s,{type:"analyzing",id:"a-1"});assert.equal(s.stage,"analyzing");
  s=transition(s,{type:"complete",id:"a-1",result:payload});
  assert.equal(s.stage,"complete");assert.equal(s.report.n_rows,95);
});
test("cancel and retry cannot resurrect old worker response",()=>{
  let s=transition(freshState(),{type:"start",id:"one",scenario:"dst_fall"});
  s=transition(s,{type:"cancel"});
  s=transition(s,{type:"complete",id:"one",result:payload});
  assert.equal(s.stage,"cancelled");assert.equal(s.report,null);
  s=transition(s,{type:"start",id:"two",scenario:"dst_spring"});
  assert.equal(transition(s,{type:"error",id:"one",error:"late"}),s);
  assert.equal(s.stage,"verifying");
});
test("reject malformed or fabricated reports",()=>{
  assert.throws(()=>safeReport({...payload,engine:"browser-preview"}),/synthetic Python/);
  assert.throws(()=>safeReport({...payload,source:"customer.csv"}),/synthetic Python/);
  assert.throws(()=>safeReport({...payload,report:{...payload.report,n_rows:-1}}),/canonical counter/);
  assert.throws(()=>safeReport({...payload,report:{...payload.report,completeness:NaN}}),/completeness/);
  assert.throws(()=>safeReport({...payload,report:{...payload.report,schema_version:"1"}}),/Canonical v2/);
});
test("running state refuses overlapping run",()=>{
  const s=transition(freshState(),{type:"start",id:"one",scenario:"baseline"});
  assert.throws(()=>transition(s,{type:"start",id:"two",scenario:"baseline"}),/already running/);
});
