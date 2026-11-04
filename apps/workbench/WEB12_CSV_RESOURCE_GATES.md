# WEB-12 — Resource limits and strict UTF-8 for browser CSV preview

**Internal development record. Preview mode is not verified Python output.**

## Functional change

The existing Workbench CSV import retains the existing 5 MiB file-byte cap and now uses a strict UTF-8 TextDecoder with `fatal:true` instead of permissive `file.text()` replacement. The RFC-4180-like local parser also rejects NUL control characters, text longer than 5 MiB, fields longer than 16,384 characters, more than 128 columns, and more than 50,000 data rows.

All checks happen in the browser. The existing error state clears stale preview data. No upload, network dependency or Python engine is introduced. The existing preview calculations remain explicitly non-authoritative and distinct from separately imported canonical Python reports.

## Test evidence

`tests/web12_csv_limits.test.cjs` verifies boundaries, quoted fields, control characters, 50,000-row acceptance, 50,001-row rejection and strict decoding wiring. Limits are product safety defaults rather than validated production maximums; real-device memory and parse time must still be measured.

## Remaining gates

True Python validation for user CSV remains blocked until approved package provenance, browser isolation, privacy and network reviews, and accessible progress/failure UX have passed. This change does not authorize customer decisions or a software release.
