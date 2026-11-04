// WEB-17: local-only CSV intake gate. Returns metadata, never parsed rows.
// No network, Python or customer-data execution. Separate technical review tool.
export const LIMITS=Object.freeze({
  bytes:5*1024*1024, rows:50000, columns:128, fieldCharacters:16384
});
export function inspectCsvText(text){
  if(typeof text!=="string")throw Error("Expected decoded UTF-8 text");
  if(text.length>LIMITS.bytes)throw Error("Decoded text exceeds size limit");
  if(text.includes("\0"))throw Error("NUL characters prohibited");
  const s=text.charCodeAt(0)===0xfeff?text.slice(1):text;
  let state="start",fieldLength=0,column=0,expected=null,physical=0,records=0;
  let cell="",headers=null,headerSeen=false;
  function addField(){
    if(fieldLength>LIMITS.fieldCharacters)throw Error("CSV field too long");
    column++;
    if(column>LIMITS.columns)throw Error("Too many CSV columns");
    if(!headerSeen){
      if(!headers)headers=[];
      headers.push(cell.trim());
    }
    cell="";fieldLength=0;state="start";
  }
  function finishRow(){
    // Skip only physically empty lines. Quoted empty values are still records.
    if(column===0 && cell==="" && state==="start")return;
    addField();
    if(!headerSeen){
      if(!headers?.length || headers.some(h=>!h) ||
        new Set(headers).size!==headers.length)
        throw Error("Missing or duplicate CSV column headers");
      expected=column;headerSeen=true;
    }else{
      if(column!==expected)throw Error("Inconsistent CSV row width");
      records++;
      if(records>LIMITS.rows)throw Error("Too many CSV data rows");
    }
    physical++;column=0;
  }
  for(let i=0;i<s.length;i++){
    const c=s[i];
    if(state==="quoted"){
      if(c==='"')state="after_quote";
      else {cell+=c;fieldLength++;if(fieldLength>LIMITS.fieldCharacters)throw Error("CSV field too long")}
      continue;
    }
    if(state==="after_quote"){
      if(c==='"'){cell+='"';fieldLength++;if(fieldLength>LIMITS.fieldCharacters)throw Error("CSV field too long");state="quoted";continue}
      if(![",","\n","\r"].includes(c))throw Error("Character after closing CSV quote");
    }else if(c==='"'){
      if(state!=="start")throw Error("Quote inside unquoted field");
      state="quoted";continue;
    }
    if(c===","){addField();continue}
    if(c==="\n" || c==="\r"){
      if(c==="\r" && s[i+1]==="\n")i++;
      finishRow();continue;
    }
    cell+=c;fieldLength++;
    if(fieldLength>LIMITS.fieldCharacters)throw Error("CSV field too long");
    state="plain";
  }
  if(state==="quoted")throw Error("Unclosed CSV quote");
  if(column || cell || state==="after_quote")finishRow();
  if(!headerSeen || records<1)throw Error("CSV requires a header and at least one data row");
  return Object.freeze({
    classification:"local-csv-preflight-only",
    data_rows:records,columns:expected,
    headers:Object.freeze([...headers]),
    approved_for_python:false
  });
}
export function inspectCsvBytes(input){
  if(!(input instanceof Uint8Array))throw Error("CSV bytes required");
  if(input.byteLength===0 || input.byteLength>LIMITS.bytes)
    throw Error("CSV file must be 1 byte to 5 MiB");
  const text=new TextDecoder("utf-8",{fatal:true}).decode(input);
  return inspectCsvText(text);
}
