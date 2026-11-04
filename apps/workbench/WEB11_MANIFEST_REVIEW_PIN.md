# WEB-11 — Independently review-pinned candidate manifest gate

**Internal technical experiment. No release, publication or provenance approval.**

The candidate manifest previously included the wheel hash, but an attacker or stale build replacing both manifest and wheel could leave that comparison internally consistent. WEB-11 adds an optional, separately supplied SHA-256 pin for the exact manifest bytes, checked **before parsing the manifest or fetching its wheel**. The fail-closed `fetchReviewPinnedCandidateWheel` API requires a 64-character lower-case pin and refuses network access without it.

The pin must be obtained from an independent trusted review record and packaged outside the response it authenticates. A checksum copied from the **same manifest download** is *not* independent. This is not an author signature, secure boot chain, SBOM, package audit, trusted runtime guarantee or approval to execute unknown Python.

### Integration

Reviewer code may invoke `fetchReviewPinnedCandidateWheel({baseUrl, expectedManifestSha256})`; this experimental helper still returns candidate-only bytes and does not execute the wheel. The existing WEB-09 pilot continues to use `fetchCandidateWheel` without claiming publisher authentication. Tests explicitly show missing/malformed pins cannot fetch anything and a manifest mismatch prevents the wheel request.

### Next release gates

Review a tagged source commit and reproducible wheel, establish a separately governed signed release policy/manifest, pin Pyodide and all transitive Python dependencies, conduct network/IP/privacy reviews, add worker memory and customer-data constraints and cross-browser evidence. Only then consider replacing the developer-only candidate flow.
