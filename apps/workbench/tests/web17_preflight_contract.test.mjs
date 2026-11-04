import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
const page=readFileSync(fileURLToPath(new URL("../web17_local_csv_preflight.html",import.meta.url)),"utf8");
test("WEB-17 has only local file intake and never posts data",()=>{
 assert.match(page,/type="file"/);
 assert.match(page,/chosen\.arrayBuffer\(\)/);
 assert.match(page,/inspectCsvBytes\(bytes\)/);
 assert.doesNotMatch(page,/<form\b/i);
 assert.doesNotMatch(page,/fetch\s*\(/);
 assert.doesNotMatch(page,/XMLHttpRequest/);
 assert.doesNotMatch(page,/new\s+Worker\s*\(/);
 assert.doesNotMatch(page,/postMessage\s*\(/);
 assert.doesNotMatch(page,/\.runPython/);
});
test("WEB-17 reports structural metadata only and supports reset",()=>{
 assert.match(page,/result\.data_rows/);
 assert.match(page,/result\.columns/);
 assert.match(page,/selection\+\+/);
 assert.match(page,/ticket!==selection/);
 assert.match(page,/Python execution remains disabled/);
});
