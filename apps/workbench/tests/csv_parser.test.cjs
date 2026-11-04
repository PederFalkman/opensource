"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const begin = source.indexOf("const MAX_CSV_BYTES =");
const end = source.indexOf("\nfunction setData(", begin);
assert(begin !== -1 && end > begin, "CSV parser must exist in Workbench");
const context = vm.createContext({});
vm.runInContext(source.slice(begin, end), context);
const parse = text => JSON.parse(JSON.stringify(context.csvParse(text)));

test("sample CSV, CRLF, BOM and quoted fields", () => {
  assert.deepEqual(parse("\uFEFFtimestamp,value\r\n2026-01-01T00:00:00Z,15\r\n"),
    [["timestamp", "value"], ["2026-01-01T00:00:00Z", "15"]]);
  assert.deepEqual(parse('timestamp,value\n"a,b","a ""quoted"" value"\n'),
    [["timestamp","value"],["a,b",'a "quoted" value']]);
});
test("quoted newlines are not treated as record separators", () => {
  assert.deepEqual(parse('a,b\n"line1\nline2",42\n'),
    [["a","b"],["line1\nline2","42"]]);
});
test("malformed quote placement fails instead of silently changing data", () => {
  for (const csv of [
    'a,b\nfoo"bar,2\n',
    'a,b\n"foo"x,2\n',
    'a,b\n"unclosed,2',
    'a,b\n"abc",2"\n'
  ]) {
    assert.throws(() => parse(csv), /quote|Quoted/i);
  }
});
test("trailing newline and empty cells keep expected shape", () => {
  assert.deepEqual(parse("a,b\n1,\n2,3\r\n"),
    [["a","b"],["1",""],["2","3"]]);
});
