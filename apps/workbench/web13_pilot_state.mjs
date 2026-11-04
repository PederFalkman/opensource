// WEB-13 internal synthetic-only run-state guards. No untrusted CSV input.
export const SCENARIOS = Object.freeze(["baseline","dst_fall","dst_spring","mixed_offsets"]);
export const STAGES = Object.freeze(["idle","verifying","loading","analyzing","complete","error","cancelled"]);
export function scenarioAllowed(value) {
  return typeof value === "string" && SCENARIOS.includes(value);
}
export function safeReport(payload) {
  const r = payload?.report;
  if(!r || r.schema_version !== "2") throw Error("Canonical v2 report required");
  for(const k of ["n_rows","n_missing_intervals","n_duplicate_timestamps"])
    if(!Number.isSafeInteger(r[k]) || r[k]<0)throw Error("Invalid canonical counter: "+k);
  if(r.completeness!==null && r.completeness!==undefined &&
      (typeof r.completeness!=="number" || !Number.isFinite(r.completeness) ||
        r.completeness<0 || r.completeness>1))
    throw Error("Invalid canonical completeness");
  if(payload.engine!=="python-validated" || payload.source!=="web09-synthetic-only")
    throw Error("Only synthetic Python pilot reports supported");
  return r;
}
export function freshState() { return {stage:"idle",runId:null,report:null,error:null}; }
export function transition(state,event) {
  if(event.type==="start"){
    if(!scenarioAllowed(event.scenario) || !/^[a-z0-9-]{1,64}$/.test(event.id))
      throw Error("Invalid synthetic pilot run");
    if(["verifying","loading","analyzing"].includes(state.stage))
      throw Error("Pilot already running");
    return {stage:"verifying",runId:event.id,report:null,error:null};
  }
  if(event.type==="cancel")
    return {stage:"cancelled",runId:null,report:null,error:null};
  // Late worker messages and stale callbacks must never resurrect a cancelled run.
  if(!state.runId || event.id!==state.runId)return state;
  if(event.type==="loading" && ["verifying","loading"].includes(state.stage))
    return {...state,stage:"loading"};
  if(event.type==="analyzing" && ["verifying","loading","analyzing"].includes(state.stage))
    return {...state,stage:"analyzing"};
  if(event.type==="complete" && ["verifying","loading","analyzing"].includes(state.stage))
    return {stage:"complete",runId:null,report:safeReport(event.result),error:null};
  if(event.type==="error")
    return {stage:"error",runId:null,report:null,error:String(event.error||"Worker failed").slice(0,300)};
  return state;
}
