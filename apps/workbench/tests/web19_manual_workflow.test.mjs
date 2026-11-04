import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
const read=(p)=>readFileSync(fileURLToPath(new URL(p,import.meta.url)),"utf8");
const workflow=read("../../../.github/workflows/web09-worker-smoke.yml");
const page=read("../web13_synthetic_review.html");
const smoke=read("../web13_browser_smoke.py");
test("WEB-19 expensive browser workflow is manual-only",()=>{
 assert.match(workflow,/workflow_dispatch:/);
 assert.doesNotMatch(workflow,/^\s+(?:pull_request|push|schedule):/m);
 assert.match(workflow,/web13_browser_smoke\.py/);
 assert.match(workflow,/web09_worker_smoke|browser_worker_smoke\.py/);
});
test("WEB-19 has explicit browser and test target allowlists",()=>{
 for(const name of ["chromium","firefox","webkit","web13","web09"])
   assert.match(workflow,new RegExp("- "+name+"\\b"));
 assert.match(workflow,/case "\$TEST_TARGET" in/);
});
test("WEB-19 review page validates independent pin before any fetch",()=>{
 const start=page.indexOf('const reviewPin=$("reviewPin").value.trim()');
 const gate=page.indexOf('if(!/^[a-f0-9]{64}$/.test(reviewPin))');
 const fetch=page.indexOf("fetchReviewPinnedCandidateWheel(");
 assert.ok(start>=0 && gate>start && fetch>gate);
 assert.match(page,/expectedManifestSha256:reviewPin/);
});
test("WEB-19 browser smoke checks no wheel request on bad pin",()=>{
 assert.match(smoke,/Candidate asset requested before review pin supplied/);
 assert.match(smoke,/Wheel fetched after manifest pin mismatch/);
 assert.match(smoke,/hashlib\.sha256\(manifest_bytes\)\.hexdigest\(\)/);
 assert.match(smoke,/parity\.changes\(/);
 assert.match(smoke,/page\.expect_download\(/);
});
