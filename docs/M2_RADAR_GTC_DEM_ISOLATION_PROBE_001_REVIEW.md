# M2 radar GTC DEM-isolation probe-001 review

This is a **local zero-decision proposal**. Proposal SHA-256: `2cac9f72dc21bcda9e0bdff571de681ad7efe5b4c0c86ac26a0c5fd4aea9f984`. No publication, implementation, input access, ArcPy invocation, or probe is authorized by preparing it.

Recovery-005 is terminal after GTC with the approved DEM raised `ERROR 000425`. The read-only diagnostic recognized all six preserved candidates, but did not establish their GTC fitness. A public catalog audit shows incomplete DEM-box overlap for every radar scene; it does not measure valid pixels or prove a cause.

## Proposed single decision

Authorize implementation, synthetic and installed-runtime no-content validation, public CI gates, one final no-content preflight, **at most one** GTC call on the exact preserved M1-SRC-001 despeckled gamma CRF **without a DEM argument**, and sanitized terminal publication, without intermediate reconfirmation. The exact call, input, prospective output root, stop rules, and exclusions are in the proposal.

[Esri's GTC documentation](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-geometric-terrain-correction.html) describes metadata tie-point interpolation without a DEM but advises using a DEM for land scenes. Thus even a completed no-DEM output remains quarantined diagnostic material, never a map or scientific baseline. A success or failure cannot by itself prove the earlier error's historical root cause.

The decision is **approve, revise, or defer** this one bounded diagnostic. It does not approve expanded DEM coverage, source reordering, a follow-on processing attempt, change analysis, attribution, or publication of derived pixels.
