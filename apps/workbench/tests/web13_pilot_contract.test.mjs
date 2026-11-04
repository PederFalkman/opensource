import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
const path=new URL("../web13_synthetic_review.html",import.meta.url);
const page=readFileSync(fileURLToPath(path),"utf8");
const worker=readFileSync(fileURLToPath(new URL("../web09_engine_worker.mjs",import.meta.url)),"utf8");
test("WEB-13 presents no user file picker or arbitrary CSV entry",()=>{
  assert.doesNotMatch(page,/<input[^>]*type\s*=\s*["']file["']/i);
  assert.doesNotMatch(page,/<textarea\b/i);
  assert.match(page,/synthetic-only/i);
  assert.match(page,/No file upload is supported/i);
});
test("WEB-13 invokes fixed synthetic worker protocol only",()=>{
  assert.match(page,/type:"run-synthetic"/);
  assert.match(page,/scenarioAllowed\(scenario\)/);
  assert.doesNotMatch(page,/type:"run-csv"/);
  assert.doesNotMatch(page,/csvText\s*:/);
  assert.match(worker,/Only internally generated synthetic scenarios are supported/);
});
test("WEB-13 preserves cancellation, same-origin wheel loading, output validation",()=>{
  assert.match(page,/fetchCandidateWheel\(\{baseUrl:location.href,signal:abort.signal\}\)/);
  assert.match(page,/worker\?\.terminate\(\)/);
  assert.match(page,/data.id!==state.runId/);
  assert.match(page,/transition\(state,\{type:"complete",id,result:data.result\}\)/);
  assert.match(page,/energydata-synthetic-review-evidence.json/);
});

test("WEB-14 exports an explicitly unattested evidence envelope",()=>{
  assert.match(page,/createSyntheticEvidence/);
  assert.match(page,/wheelSha256:wheelDigest/);
  assert.match(page,/elapsedMs:performance.now\(\)-startMs/);
  assert.match(page,/internal and not independently attested/);
});
