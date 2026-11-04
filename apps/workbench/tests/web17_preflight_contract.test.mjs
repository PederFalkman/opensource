import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
const page=readFileSync(fileURLToPath(new URL("../web17_local_csv_preflight.html",import.meta.url)),"utf8");
const controller=readFileSync(fileURLToPath(new URL("../web17_local_csv_preflight_ui.mjs",import.meta.url)),"utf8");
test("WEB-17 has only local file intake and never posts data",()=>{
 assert.match(page,/type="file"/);
 assert.match(page,/chosen\.arrayBuffer\(\)/);
 assert.match(page,/inspectCsvBytes\(bytes\)/);
 assert.doesNotMatch(page,/<form\b/i);
 assert.doesNotMatch(page,/fetch\s*\(/);
 assert.doesNotMatch(controller,/XMLHttpRequest/);
 assert.doesNotMatch(page,/new\s+Worker\s*\(/);
 assert.doesNotMatch(page,/postMessage\s*\(/);
 assert.doesNotMatch(page,/\.runPython/);
});
test("WEB-17 reports structural metadata only and supports reset",()=>{
 assert.match(page,/result\.data_rows/);
 assert.match(page,/result\.columns/);
 assert.match(page,/selection\+\+/);
 assert.match(controller,/ticket!==selection/);
 assert.match(controller,/Python execution remains disabled/);
});

test("WEB-17 CSP forbids network APIs, Workers and form submission",()=>{
 assert.match(page,/http-equiv="Content-Security-Policy"/);
 assert.match(page,/default-src 'none'/);
 assert.match(page,/connect-src 'none'/);
 assert.match(page,/worker-src 'none'/);
 assert.match(page,/form-action 'none'/);
 assert.match(page,/script-src 'self'/);
});

test("strict CSP remains effective with external same-origin module",()=>{
 assert.match(page,/<script type="module" src="\.\/web17_local_csv_preflight_ui\.mjs"><\/script>/);
 assert.doesNotMatch(page,/<script type="module">/);
 assert.match(controller,/\.\/web17_csv_preflight\.mjs/);
});
