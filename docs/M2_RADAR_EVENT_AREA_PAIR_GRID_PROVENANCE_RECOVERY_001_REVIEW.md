# M2 radar event-area pair: grid provenance recovery-001

## Decision

Approve, revise, or defer one conditional recovery envelope for a **new, read-only metadata process** over the same five preserved M1-SRC-002 CRFs. A single approval would cover exact packet publication, implementation, disposable and portable tests, public CI gates, one final no-content preflight, at most one distinct real process, and sanitized terminal publication without intermediate reconfirmation. No radar processing or pixel reading is included.

## Why recovery is needed

The consumed `grid-provenance-diagnostic-001-real-001` reserved four receipts. Its started and error receipts were written, with `gtc_configuration_count_ambiguous` in the error. Its terminal and cleanup receipts remain immutable zero-byte files. The frozen code path implies that ArcPy metadata calls on all five named rasters returned before the configuration check raised, but **no actual metadata values were saved**. The process's outer status text was misleading; the [terminal reconciliation](../records/readiness/m2-radar-event-area-pair-grid-provenance-diagnostic-001-real-001-terminal-reconciliation.json) is authoritative. The actual raster grid and the trigger of the secondary receipt-persistence failure remain unknown.

A [portable synthetic postmortem](../records/readiness/m2-radar-event-area-pair-grid-provenance-diagnostic-001-local-postmortem-observation.json) replayed the configuration error and wrote all receipts. An injected terminal-write failure reproduced the written-error/empty-terminal/empty-cleanup pattern, showing that the old cleanup write was not independent. This demonstrates a structural vulnerability, **not** the real failure's cause. No ArcGIS runtime, preserved raster, or external custody was accessed for that postmortem.

## Recovery controls

The proposed new process would reserve and fsync distinct receipts and an append-only stage journal before preserved metadata access. It would write each raster's sanitized CRS, extent, dimensions, cell size, and band count to the stage journal immediately after the read. Missing or conflicting metadata stops at that source while retaining earlier stages. A bounded metadata-sidecar inventory inside the exact saved GTC CRF would report candidate counts and hashes; only a unique match to the published configuration SHA-256 could identify that historical configuration. No match or ambiguity remains unresolved, rather than being promoted into grid fitness.

Terminal and cleanup writes would be independent, with a separate fallback error identity. Synthetic interruption and injected-write-failure tests, installed ArcGIS tests using generated CRFs, public CI, and a final no-content preflight must all pass before one fresh real process. The consumed process and its four receipts cannot be altered, resumed, or retried. The existing `e1/a1` radar attempt also remains immutable. Results establish metadata observations only, not valid pixels, radar source QA, a baseline, mapped change, or attribution.

## Decision requested

Approve the exact proposal and review bundle by their SHA-256 hashes, revise the scope, or defer. This **local, zero-decision** packet grants no publication, ArcPy invocation, or external-custody access by itself.
