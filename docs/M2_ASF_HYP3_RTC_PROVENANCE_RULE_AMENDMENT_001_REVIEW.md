# M2 ASF HyP3 RTC provenance rule amendment 001 — local owner review

**Decision status: not approved; zero-decision local packet.** This review and its proposal have not been published to Git or CI. They authorize no new product read, job, raster access, or map processing.

## Why the route stopped

The first exact ASF RTC job (`M1-SRC-002`, `dad53076-78fc-42e8-a58e-ad17efb88a7e`) produced a 9,574,123,274-byte ZIP in verified, no-replace non-Git custody. The one authorized README-only probe confirmed the promoted archive's SHA-256, then read a 16,540-byte README member. It found the exact approved Sentinel-1 source granule but not the full generated product base name as literal text in the README body. Under the frozen two-text-match rule, the result is **`defer_readme_source_text_review`**. That attempt is terminal and will not be retried or rewritten. [Terminal reconciliation](../records/readiness/m2-asf-hyp3-rtc-readme-first-terminal-reconciliation-001.json)

ASF's [RTC product guide](https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/) documents the generated base name in the product folder and member filenames, while describing the README as customized to the product. It does not say the README body must repeat the full base name. This suggests the literal-body requirement could be stricter than ASF's package convention. It does **not** prove this particular ZIP's source identity on its own. The project also has an exact authenticated job descriptor, ZIP name and size, archive hash and CRC, documented single-root/member-name checks, and the README's exact source-granule match. These are distinct evidence links and should be evaluated together rather than silently relabeling the old result as a pass.

The old probe's `defer` result followed its successful ZIP member-name screen and comparison of the exact ZIP filename with the product folder name; otherwise that code would have stopped with an error before writing this result. This is an **inference from the executed code path**, not a separately recorded folder-name observation. The proposed evaluator must verify the old implementation gate and exact README and package-check code hashes before relying on it. If those bindings cannot be established, the composite rule stops.

## Proposed decision

Approve a **new composite provenance rule for this exact product**. It would require every link above and retain the missing README product-base literal as a recorded warning. Any absent or conflicting source, job, product, archive, or processing metadata stops. The composite outcome would mean only *eligible for further local QA*. It would not establish valid pixels, AOI coverage, registration, map readiness, or a scientific result.

If approved, the [exact proposal](../contracts/milestone-002-asf-hyp3-rtc-provenance-rule-amendment-001-proposal.json) provides one conditional envelope for implementation and synthetic tests, sanitized public CI, a fresh no-content gate, one receipt-only composite evaluation without rereading the ZIP, then the already approved product metadata and pixel-QA path. That later path must independently verify processing, layover/shadow codes, product-specific acknowledgement and DOI, rights for the intended local map, GeoTIFF headers, usable AOI pixels, and stable-control registration. Only passing evidence could release the fixed-order after-scene job and eventually a local EPSG:32645 ArcGIS before/after panel. The prior source, date, AOI, grid, threshold, method, free-credit and one-attempt limits do not change.

The alternative is to keep the literal README base-name condition as a hard prerequisite. That would preserve the defer and stop this ASF map route unless a separately approved source or method supplied the missing literal text. Either choice leaves the original attempt and its receipts immutable.

**Decision requested:** approve, revise, or defer the exact composite identity amendment and conditional continuation envelope. No new product access or execution follows from this local review alone. Baseline admission, change analysis, attribution, derived-pixel publication, and scientific publication remain excluded.
