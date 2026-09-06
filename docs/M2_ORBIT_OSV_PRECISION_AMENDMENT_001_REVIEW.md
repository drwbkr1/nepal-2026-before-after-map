# M2 orbit OSV precision amendment-001 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4`. A completed decision must bind the exact review-bundle hash and include the owner's attestation.

## Preserved terminal result

Recovery-003 is terminal and consumed. Its one authorized request downloaded exact `M2-ORB-001` into append-only staging. The 639,533 bytes match provider MD5 `ca7f36b1892073c883c4cff5c0517b9c` and BLAKE3 `ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b` and have local SHA-256 `a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4`. The file was not promoted.

The frozen verifier returned `osv_times_do_not_span_validity`: the header stop is `UTC=2026-08-16T14:09:56`, while the last OSV is `UTC=2026-08-16T14:09:55.968171`, a 0.031829-second shortfall. The exact scene remains more than 6,350 seconds inside the declared validity interval.

## Source evidence and proposed interpretation

The [Copernicus POD Service File Format Specification](https://sentiwiki.copernicus.eu/__attachments/1673407/GMV-CPOD3-FFS-0001%20-%20Copernicus%20POD%20Service%20File%20Format%20Specification%202023%20-%203.0.pdf) specifies whole-second formatting for header validity timestamps and microsecond formatting for OSV timestamps. It calls the values consistent but does not state a numerical tolerance or rounding rule. The proposed one-second maximum is therefore an explicit local inference from representational precision, not a quoted provider requirement.

## What approval would authorize

Approval would authorize a versioned 1.0-second endpoint-consistency rule while leaving all identity, checksum, safe-XML, OSV order, finite-value, units, and scene-margin checks unchanged. After synthetic tests and successful public CI, one final no-network preflight could bind the existing staged bytes and absent destination. One local validation could then conditionally promote only those exact bytes without replacement and run input-only offline verification.

## Still prohibited

No token, catalogue request, payload request, recovery-003 retry, tolerance above one second, other orbit file, precise-orbit substitution, orbit application, DEM action, radar-pixel decoding, baseline, change analysis, attribution, or scientific publication is authorized by this review packet.
