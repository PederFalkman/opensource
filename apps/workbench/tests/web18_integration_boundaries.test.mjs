import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
const source=name=>readFileSync(fileURLToPath(new URL("../"+name,import.meta.url)),"utf8");
const preview=source("index.html");
const synthetic=source("web13_synthetic_review.html");
const worker=source("web09_engine_worker.mjs");
const preflight=source("web17_local_csv_preflight.html");
const preflightUI=source("web17_local_csv_preflight_ui.mjs");
const loader=source("web09_candidate_loader.mjs");
const evidence=source("web14_evidence.mjs");
test("WEB-18: real Python worker remains synthetic-only",()=>{
  assert.match(worker,/data\.type !== "run-synthetic"/);
  assert.match(worker,/Object\.hasOwn\(data,"csvText"\)/);
  assert.match(worker,/Only internally generated synthetic scenarios are supported/);
  assert.doesNotMatch(worker,/run-user-csv|run-customer-csv/);
});
test("WEB-18: review page provides no customer-data intake",()=>{
  assert.doesNotMatch(synthetic,/<input[^>]*type=["']file["']/i);
  assert.doesNotMatch(synthetic,/<textarea\b/i);
  assert.match(synthetic,/type:"run-synthetic"/);
  assert.doesNotMatch(synthetic,/postMessage\(\{[^}]*csvText/s);
  assert.match(synthetic,/Not approved for customer data/);
});
test("WEB-18: local CSV preflight never submits bytes to Worker or server",()=>{
  assert.match(preflight,/connect-src 'none'/);
  assert.match(preflight,/worker-src 'none'/);
  assert.match(preflight,/form-action 'none'/);
  assert.match(preflightUI,/inspectCsvBytes\(bytes\)/);
  assert.doesNotMatch(preflightUI,/fetch\s*\(|XMLHttpRequest|postMessage\s*\(/);
  assert.doesNotMatch(preflightUI,/new Worker\s*\(/);
});
test("WEB-18: public preview remains explicitly non-authoritative",()=>{
  assert.match(preview,/browser-preview/);
  assert.match(preview,/non-authoritative|not the authoritative/i);
  assert.match(preview,/Import Python JSON/);
  assert.doesNotMatch(preview,/type:"run-csv"/);
});
test("WEB-18: candidate checks and synthetic evidence do not claim publisher approval",()=>{
  assert.match(loader,/candidate-not-approved/);
  assert.match(loader,/fetchReviewPinnedCandidateWheel/);
  assert.match(evidence,/internal-unattested-synthetic-only/);
  assert.match(evidence,/not publisher identity/);
});
