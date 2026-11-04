// WEB-14 internal evidence envelope, synthetic-only; not a signature or attestation.
import {scenarioAllowed,safeReport} from "./web13_pilot_state.mjs";
export function createSyntheticEvidence({scenario,wheelSha256,elapsedMs,output}) {
  if(!scenarioAllowed(scenario))throw Error("Only fixed synthetic scenarios permitted");
  if(typeof wheelSha256!=="string" || !/^[a-f0-9]{64}$/.test(wheelSha256))
    throw Error("Verified wheel SHA-256 required");
  if(typeof elapsedMs!=="number" || !Number.isFinite(elapsedMs) ||
      elapsedMs<0 || elapsedMs>3_600_000)
    throw Error("Invalid elapsed duration");
  if(!output || typeof output!=="object" || Array.isArray(output))
    throw Error("Invalid Python result");
  safeReport(output);
  // Do not export unexpected wrapper fields returned by experimental runtime.
  const allowed=new Set(["adapter_version","engine","package_version","source",
    "columns","interval_minutes","report","privacy"]);
  if(Object.keys(output).some(key=>!allowed.has(key)))
    throw Error("Unexpected Python result metadata");
  if(output.privacy!=="browser-worker-synthetic" ||
      output.interval_minutes!==15 ||
      output.columns?.timestamp!=="timestamp" ||
      output.columns?.value!=="power_kw" ||
      typeof output.package_version!=="string" ||
      !/^[0-9][0-9A-Za-z.+_-]{0,79}$/.test(output.package_version))
    throw Error("Unexpected synthetic Python provenance metadata");
  // Enforce an upper bound on evidence size before holding it in the UI/export.
  // This is not a replacement for Worker memory/response-size management.
  if(JSON.stringify(output).length>256*1024)
    throw Error("Synthetic evidence exceeds 256 KiB");
  return {
    evidence_schema:"energydata.workbench.synthetic-review.v1",
    status:"internal-unattested-synthetic-only",
    scenario,
    wheel_sha256:wheelSha256,
    elapsed_ms:Math.round(elapsedMs),
    result:output,
    limitations:[
      "No customer data",
      "Candidate digest verifies bytes but not publisher identity",
      "Runtime dependencies and distribution not independently attested",
      "This run was not compared to an external reference"
    ]
  };
}
