# M2 Landsat-9 EarthExplorer full-bundle intake — local review

**Status: zero decision.** This packet asks for one conditional owner decision; preparing and validating it authorizes no download, real archive read, public Git write, pixel processing, or map claim.

## Why this route

The existing local ASF before/after panel is a credited partial visual, but both dates remain full-area `defer`. The 24 August Sentinel-2 optical scene failed the frozen AOI usability screen. The exact same-sensor Landsat-9 scenes on **10 August (before)** and **26 August (early after)** are therefore a useful alternative to test without treating catalog coverage as usable pixels. The 26 August acquisition is shortly after the event signal, not proof that all downstream effects had ended.

The owner selected USGS EarthExplorer. In the owner-signed-in browser, both exact scenes offer **Landsat Collection 2 Level-2 Product Bundle** at a rounded **1.05 GiB each**. The separate green surface-reflectance and surface-temperature “Download All Files Now” controls are not the selected transport. The exact pre-event bundle’s Download Product control was visible during the 29 September read-only check; it was not activated. No product bytes or source pixels have been read.

| Role | Landsat Level-2 product ID | Scene ID |
| --- | --- | --- |
| Before | `LC09_L2SP_141040_20260810_20260811_02_T1` | `LC91410402026222LGN00` |
| Early after | `LC09_L2SP_141040_20260826_20260827_02_T1` | `LC91410402026238LGN00` |

## Decision requested

Approve [proposal `46401cecebde782b4449c3fb76a51f89f8cd3993f70c954181e15bb7ac0636dd`](../contracts/milestone-002-landsat9-usgs-bundle-intake-001-proposal.json) as **one conditional authority envelope**. It covers exact-source control integration, a secret-safe completed-browser-download handoff, synthetic tests, public default-branch CI, a final no-payload preflight, at most one initial full-bundle request per exact scene plus at most one tightly conditioned fresh recovery for a classified transport or local-persistence failure, TAR/MTL identity verification, no-replace non-Git promotion, and sanitized terminal publication. The before bundle must pass before the early-after request. A rights, account, source-identity, security, or unexplained content failure stops the envelope; it is not a retry trigger.

The [candidate intake contract](../contracts/m2-landsat9-usgs-bundle-intake-candidate.json) is structurally valid but deliberately remains `planned` with `PENDING-OWNER-APPROVAL-NO-REQUEST-AUTHORITY`. The [source gate](../records/source-gates/m2-landsat9-same-sensor-usgs-intake-003-local.json) has all eight required criteria passing but reports **zero authorized next actions**. The [host-specific plan](../records/readiness/m2-landsat9-usgs-earth-explorer-bundle-intake-plan-003-local.json) binds the two full bundles and replaces the older `MTL.json`/separate-asset assumption for this host.

## Verification and limits

The [local TAR verifier](../scripts/landsat_l2_bundle_integrity.py) has only been exercised on synthetic archives. It rejects unsafe paths, links, duplicate member names, missing or empty required members, wrong product/scene IDs in either `MTL.txt` or `MTL.xml`, malformed end markers, and trailing hidden payload. It computes local archive and member SHA-256 values. The [focused tests](../tests/test_landsat_l2_bundle_integrity.py) do not prove the real EarthExplorer bundle is readable. The browser runtime exposes a download-completion event and a local download-path API, but this exact control has not been clicked; the actual handoff and filename remain unverified.

USGS describes EarthExplorer as a no-cost Landsat Collection 2 distribution portal and states that Landsat Level-2 products have no use restrictions. These source-data rights do not authorize a project download by themselves, nor do they prove the owner’s account conditions are unchanged. No exact provider byte length or cryptographic digest was observed; the displayed 1.05 GiB is only for storage planning. A local SHA-256 plus matching MTL identity will establish internally consistent custody, not equivalence to an unpublished upstream digest. Relevant primary sources: [USGS Level-2 products](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products), [USGS download FAQ](https://www.usgs.gov/faqs/how-do-i-search-and-download-landsat-collection-2-data-products), and [USGS Landsat 8–9 Level-2 file specification](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1328_Landsat8-9_OLI-TIRS-C2-L2_DFCB-v7.pdf).

**Excluded:** M2M API, another host or scene, token handling, terms acceptance, paid download, unbounded retries, TIFF header or pixel read, AOI masks, registration, baseline admission, change analysis, attribution, ArcGIS raster map, derived-pixel release, and scientific publication. An intake pass would only unlock a separately reviewed Landsat pixel and map method; it would not establish that the before/after imagery is usable over the event AOIs.
