# M2 radar delayed-import probe receipt recovery-001 review

**Proposal SHA-256:** `9bbe934bd1dcbe7d1b0700b83473db2ab1a130c13fa6d183d3b1a247dfe88e09`  
**Consumed probe terminal SHA-256:** `90e7b9ff1fa823f9be805e1fba843e7af9dd34c313d4e5c6c75077c8aee81892`  
**Decision state:** zero decisions; prepared locally; publication is not authorized

## Observed terminal state

The single authorized delayed-import probe is terminal and consumed. It created and fully hashed 156 disposable sparse files totaling 10,367,157,634 logical bytes, with aggregate SHA-256 `dd56f8b28a1ed1c6e2b4b1d7d8f5db4fd86dab80a910fe79c8d018d58942430b`. Its last durable stage is `arcpy_import_started`.

After the probe caught an underlying exception, ordinary terminal construction failed with `AttributeError: module 'datetime' has no attribute 'now'`. That second failure masked the original caught exception. No runner terminal or cleanup receipt was written, although postprocess reconciliation removed the disposable corpus and retained the started and stage records. ArcPy import completion and the original exception cannot be reconstructed.

No project data, external custody, network credential, radar pixel, baseline, change-analysis, interpretation, attribution, or scientific action occurred.

## Proposed bounded correction

The proposed implementation would change only receipt durability and error retention. Every timestamp would use a function-local datetime-module binding. Before any corpus creation, the fresh attempt would reserve immutable terminal and cleanup receipt identities and initialize a minimal append-only fallback journal. A caught exception would be reduced immediately to sanitized primitive fields and appended before ordinary terminal assembly. If normal terminal construction or persistence also failed, the fallback journal would retain both errors. Cleanup evidence would run from an outer `finally` path independent of normal terminal serialization.

Portable tests would cover timestamp-name rebinding, forced terminal-write failure, retention of the original error, cleanup persistence, interruption, exact stage order, one-attempt enforcement, and secret or project-path rejection. One installed ArcGIS-runtime synthetic test would exercise the timestamp and fallback behavior without project data or external custody.

## Proposed future attempt

Only after separate authorization to publish this packet, successful public default-branch CI, exact attested owner approval, bounded implementation, successful implementation CI, and a final no-content preflight would the project run at most one fresh append-only attempt: `radar-delayed-import-probe-receipt-recovery-001-real-001`.

That attempt would use the unchanged 156-file, 10,367,157,634-byte disposable corpus, the same stable-order full hash, the same stage order, two tiny disposable rasters, and one `MosaicToNewRaster` operation. It would use no source names or bytes, project data, external custody, network, credential, installation, or UAC action. The consumed `radar-delayed-import-probe-001-real-001` path would remain untouched and could not be resumed, reused, or retried.

## Claim limits

A pass would show only that the current host completed the fresh disposable diagnostic at that time. A block would identify the new attempt's durable boundary. Neither result would establish the historical failure cause, radar recovery readiness, baseline admission, change, interpretation, attribution, or a scientific claim.

## Current authority and next gate

The current owner instruction authorizes local packet preparation and validation only. It does not authorize a Git commit, push, public CI, implementation, ArcPy invocation, corpus creation, or a new attempt.

The next required decision is whether to commit and publish this exact zero-decision packet and run public default-branch CI. The later `approve`, `revise`, or `defer` proposal decision remains unavailable until that public gate passes.
