// WEB-09 candidate-only asset loader. No package approval or execution here.
export const MAX_MANIFEST_BYTES=128*1024;
export const MAX_WHEEL_BYTES=10*1024*1024;
export const CANDIDATE_MANIFEST="candidate-assets/manifest.json";

export function selectCandidateWheel(input) {
  if(!input || typeof input!=="object" || Array.isArray(input) ||
      input.schema_version!=="1" || input.status!=="candidate-not-approved" ||
      input.purpose!=="review-only-static-asset-inventory" ||
      !Array.isArray(input.assets) || input.assets.length<1 || input.assets.length>1000)
    throw Error("Invalid candidate manifest");
  const candidates=input.assets.filter(item=>item &&
    typeof item.path==="string" &&
    /^energydata_kit-[0-9][a-zA-Z0-9_.]*-py3-none-any\.whl$/.test(item.path));
  if(candidates.length!==1)throw Error("Exactly one top-level wheel is required");
  const asset=candidates[0];
  if(!Number.isSafeInteger(asset.bytes)||asset.bytes<1||asset.bytes>MAX_WHEEL_BYTES ||
     typeof asset.sha256!=="string"||!/^[a-f0-9]{64}$/.test(asset.sha256))
    throw Error("Invalid candidate wheel metadata");
  if(!Number.isSafeInteger(input.total_bytes) || input.total_bytes<asset.bytes)
    throw Error("Invalid manifest aggregate size");
  return asset;
}

export async function boundedBytes(response,limit,label) {
  if(!response.ok)throw Error(label+" unavailable: HTTP "+response.status);
  if(response.type==="opaque" || response.redirected)throw Error(label+" must not redirect");
  const header=response.headers.get("content-length");
  if(header!==null && (!/^\d+$/.test(header) || Number(header)>limit))
    throw Error(label+" exceeds allowed size");
  if(!response.body)throw Error(label+" streaming unavailable");
  const reader=response.body.getReader(),chunks=[];
  let total=0;
  try {
    for(;;){
      const {done,value}=await reader.read();
      if(done)break;
      total+=value.byteLength;
      if(total>limit)throw Error(label+" exceeds allowed size");
      chunks.push(value);
    }
  }finally{reader.releaseLock()}
  const output=new Uint8Array(total);
  let offset=0;
  for(const chunk of chunks){output.set(chunk,offset);offset+=chunk.byteLength}
  return output;
}

export async function fetchCandidateWheel({
  baseUrl, fetchFn=fetch, cryptoFn=globalThis.crypto, signal
}={}) {
  if(!baseUrl)throw Error("Explicit same-origin base URL required");
  if(!cryptoFn?.subtle)throw Error("Secure context with SHA-256 required");
  const root=new URL(baseUrl);
  if(!["https:","http:"].includes(root.protocol))throw Error("HTTP(S) origin required");
  const manifestUrl=new URL(CANDIDATE_MANIFEST,root);
  if(manifestUrl.origin!==root.origin)throw Error("Cross-origin manifest prohibited");
  const options={cache:"no-store",credentials:"omit",redirect:"error",signal};
  const manifestResponse=await fetchFn(manifestUrl.href,options);
  const manifestText=new TextDecoder().decode(
    await boundedBytes(manifestResponse,MAX_MANIFEST_BYTES,"Manifest")
  );
  const asset=selectCandidateWheel(JSON.parse(manifestText));
  const wheelUrl=new URL(asset.path,manifestUrl);
  if(wheelUrl.origin!==root.origin || wheelUrl.pathname.includes("%"))
    throw Error("Cross-origin or encoded wheel path prohibited");
  const wheelResponse=await fetchFn(wheelUrl.href,options);
  const bytes=await boundedBytes(wheelResponse,asset.bytes,"Wheel");
  if(bytes.byteLength!==asset.bytes)throw Error("Wheel byte count mismatch");
  const actual=Array.from(new Uint8Array(await cryptoFn.subtle.digest("SHA-256",bytes)),
    x=>x.toString(16).padStart(2,"0")).join("");
  if(actual!==asset.sha256)throw Error("Wheel SHA-256 mismatch");
  return {bytes,asset,status:"candidate-not-approved",source:wheelUrl.href};
}
