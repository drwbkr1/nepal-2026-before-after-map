# M2 orbit offline verification recovery-001 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf`. A completed decision must bind the exact review-bundle SHA-256 and include the owner's attestation.

## Preserved terminal result

After exact implementation commit `308b6d079696a5f5973f7daa02e137e07a14eea3` passed public GitHub Actions run `34145814247`, activation and a no-content preflight passed. The fixed-order verifier then opened and evaluated `M2-ORB-001` in memory. Its final receipt write stopped with `verification_output_parent_missing` because `records/acquisition/orbit-verification` did not exist.

No durable pass or fail receipt exists, so the first evaluation is **terminal indeterminate**. It must not be reconstructed or inferred. External orbit custody was unchanged. `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004` were not read.

## Exact recovery under review

Approval would authorize only a persistence-order correction: keep the exact receipt parent in clean clones, validate it in the final no-content preflight, and reserve each append-only receipt path exclusively **before** reading or hashing an EOF. The verifier would write and `fsync` the complete result through that reserved handle. A reserved empty or partial receipt would remain terminal interruption evidence and could not be reused.

After synthetic tests and successful public default-branch CI, one new final no-content preflight could run. Then one new `M2-ORB-001` recovery verification could run. Only if it produces an exact pass could `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004` each run once in that order. Any first failure or persistence interruption stops the sequence.

## Frozen rules and prohibited scope

The exact source identities, lengths, provider checksums, safe-XML rules, mission and file type, OSV ordering and units, scene bindings and margins, and maximum one-second OSV endpoint rule remain unchanged. Approval would not authorize a second recovery, automatic retry, token or network action, reacquisition, external-custody mutation, source or date substitution, `AUX_POEORB`, orbit application, DEM work, radar pixels, baseline, change analysis, attribution, or scientific publication.
