import test from "node:test";
import assert from "node:assert/strict";
import {inspectCsvBytes,inspectCsvText,LIMITS} from "../web17_csv_preflight.mjs";
const enc=new TextEncoder();
test("bounded UTF-8 CSV returns metadata, not rows",()=>{
 const out=inspectCsvBytes(enc.encode('timestamp,power_kw\r\n2026-01-01T00:00:00Z,12\r\n'));
 assert.equal(out.classification,"local-csv-preflight-only");
 assert.equal(out.data_rows,1);assert.equal(out.columns,2);
 assert.deepEqual(out.headers,["timestamp","power_kw"]);
 assert.equal(out.approved_for_python,false);
 assert.equal("rows" in out,false);
});
test("quoted comma, newline and escaped quotes",()=>{
 const out=inspectCsvText('a,b\r\n"one,two","multi\nline ""quoted"""\r\nx,y\r\n');
 assert.equal(out.data_rows,2);assert.equal(out.columns,2);
});
test("rejects invalid or duplicate headers and inconsistent rows",()=>{
 for(const csv of ['a,a\n1,2','a,\n1,2','\n','a,b\n1','a,b\n1,2,3'])
 assert.throws(()=>inspectCsvText(csv));
});
test("strict UTF-8, embedded NUL, malicious quotes",()=>{
 assert.throws(()=>inspectCsvBytes(Uint8Array.from([0x61,0x2c,0xc3,0x28])),TypeError);
 assert.throws(()=>inspectCsvText('a,b\n1,\0'),/NUL/);
 assert.throws(()=>inspectCsvText('a,b\n"unterminated,2'),/Unclosed/);
 assert.throws(()=>inspectCsvText('a,b\n"ok"junk,2'),/Character after/);
 assert.throws(()=>inspectCsvText('a,b\nabc"def,2'),/Quote inside/);
});
test("hard ceilings and exact boundaries",()=>{
 assert.throws(()=>inspectCsvBytes(new Uint8Array(LIMITS.bytes+1)),/5 MiB/);
 assert.throws(()=>inspectCsvBytes(new Uint8Array()),/5 MiB/);
 assert.equal(inspectCsvText('a\n'+'x'.repeat(LIMITS.fieldCharacters)).data_rows,1);
 assert.throws(()=>inspectCsvText('a\n'+'x'.repeat(LIMITS.fieldCharacters+1)),/field too long/);
 const col=Array.from({length:LIMITS.columns},(_,i)=>'c'+i).join(',');
 assert.equal(inspectCsvText(col+'\n'+Array(LIMITS.columns).fill('1').join(',')).columns,LIMITS.columns);
 assert.throws(()=>inspectCsvText(Array.from({length:LIMITS.columns+1},(_,i)=>'c'+i).join(',')+'\n1'),/Too many/);
});
test("50,000 rows accepted and 50,001 rejected",()=>{
 const header='time,value\n',row='2026-01-01T00:00:00Z,1\n';
 assert.equal(inspectCsvText(header+row.repeat(50000)).data_rows,50000);
 assert.throws(()=>inspectCsvText(header+row.repeat(50001)),/Too many CSV data rows/);
});
test("blank lines are ignored but quoted empty values remain records",()=>{
 assert.equal(inspectCsvText('\na,b\n\n1,2\n').data_rows,1);
 assert.equal(inspectCsvText('a\n""\n').data_rows,1);
});
