// WEB-14 internal evidence envelope, synthetic-only; not a signature or attestation.
import {scenarioAllowed,safeReport} from "./web13_pilot_state.mjs";
export function createSyntheticEvidence({scenario,wheelSha256,elapsedMs,output}) {
  if(!scenarioAllowed(scenario))throw Error("Only fixed synthetic scenarios permitted");
  if(typeof wheelSha256!=="string" || !/^[a-f0-9]{64}$/.test(wheelSha256))
    throw Error("Verified wheel SHA-256 required");
  if(typeof elapsedMs!=="number" || !Number.isFinite(elapsedMs) ||
      elapsedMs<0 || elapsedMs>3_600_000)
    throw Error("Invalid elapsed duration");
  safeReport(output);
  if(!output || typeof output!=="object" || Array.isArray(output))
    throw Error("Invalid Python result");
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
