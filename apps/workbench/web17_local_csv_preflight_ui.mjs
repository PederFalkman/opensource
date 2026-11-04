import {inspectCsvBytes,LIMITS} from "./web17_csv_preflight.mjs";
const file=document.getElementById("file");
const status=document.getElementById("status");
const metrics=document.getElementById("metrics");
const rows=document.getElementById("rows");
const cols=document.getElementById("cols");
const headers=document.getElementById("headers");
let selection=0;
function reset(){
 metrics.hidden=true;headers.hidden=true;rows.textContent="—";cols.textContent="—";
 headers.textContent="";status.textContent="No file selected.";
}
document.getElementById("clear").onclick=()=>{selection++;file.value="";reset()};
file.onchange=async()=>{
 const ticket=++selection;reset();
 const chosen=file.files?.[0];
 if(!chosen)return;
 try{
   if(chosen.size<1||chosen.size>LIMITS.bytes)throw Error("File must be 1 byte to 5 MiB");
   const bytes=new Uint8Array(await chosen.arrayBuffer());
   if(ticket!==selection)return;
   const result=inspectCsvBytes(bytes);
   if(ticket!==selection)return;
   rows.textContent=String(result.data_rows);
   cols.textContent=String(result.columns);
   headers.textContent="Column names: "+result.headers.join(", ");
   metrics.hidden=false;headers.hidden=false;
   status.textContent="Local structure check passed. Python execution remains disabled.";
 }catch(error){
   if(ticket!==selection)return;
   reset();status.textContent="Rejected: "+String(error?.message||error);
 }
};
