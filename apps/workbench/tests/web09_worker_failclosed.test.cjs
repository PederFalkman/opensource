"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const {webcrypto}=require("node:crypto");

const source=fs.readFileSync(path.join(__dirname,"..","web09_engine_worker.mjs"),"utf8");

function isolatedWorker(){
  const messages=[];
  const self={
    crypto:webcrypto,
    postMessage(message){messages.push(message);}
  };
  const context=vm.createContext({self,ArrayBuffer,Uint8Array});
  vm.runInContext(source,context,{timeout:2000});
  return {self,messages};
}

async function send(payload){
  const worker=isolatedWorker();
  await worker.self.onmessage({data:{
    type:"run-synthetic",id:"case-1",wheelBytes:new ArrayBuffer(16),
    digest:"0".repeat(64),scenario:"baseline",...payload
  }});
  return worker.messages;
}

test("unknown scenario rejected without loading Python runtime",async()=>{
  const messages=await send({scenario:"customer"});
  assert.equal(messages.length,1);
  assert.equal(messages[0].stage,"error");
  assert.match(messages[0].error,/internally generated synthetic/);
});
test("injected CSV rejected even when scenario name is valid",async()=>{
  const messages=await send({csvText:"timestamp,power_kw\r\nsecret,123"});
  assert.equal(messages.length,1);
  assert.equal(messages[0].stage,"error");
  assert.match(messages[0].error,/internally generated synthetic/);
});
test("invalid wheel SHA-256 rejected before interpreter loading",async()=>{
  const messages=await send({});
  assert.equal(messages.length,1);
  assert.equal(messages[0].stage,"error");
  assert.match(messages[0].error,/integrity mismatch/);
});
test("oversized wheel refused before cryptography or package download",async()=>{
  const messages=await send({wheelBytes:new ArrayBuffer(10*1024*1024+1)});
  assert.equal(messages.length,1);
  assert.equal(messages[0].stage,"error");
  assert.match(messages[0].error,/Invalid wheel bytes/);
});
test("worker refuses caller-provided data for all allowed synthetic scenarios",async()=>{
  for(const scenario of ["baseline","dst_fall","dst_spring","mixed_offsets"]){
    const messages=await send({scenario,csvText:"customer data"});
    assert.equal(messages.length,1);
    assert.equal(messages[0].stage,"error");
  }
});
