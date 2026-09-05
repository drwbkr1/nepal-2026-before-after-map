# M2 post-optical route review 001

## Decision

Choose **approve**, **revise**, or **defer** for proposal `ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77`. Approval must be an attested owner decision bound to the exact review-bundle hash generated with this package.

## Established result

`optical-pixel-readiness-recovery-001` completed once as terminal `BLOCK` under the fixed coverage, usable-pixel, and registration criteria. Real-001 remains terminal `INVALID`. Neither result can be retried or silently rescued.

All eight exact Sentinel products remain in verified materialized custody, and both full header routes passed. Radar measurement pixels have not been decoded.

## Why a control decision is required

The predeclared plan keeps optical and radar evidence independent. The current unapproved orbit-recovery packet nevertheless requires the aggregate `M2-VERIFY` unit to complete. That cannot occur while the optical branch is terminally blocked, so the old prerequisite prevents the radar branch from reaching its own DEM and orbit gates.

## What approval would release

Approval releases only a control-plane amendment: preserve and close the optical branch, represent optical and radar readiness separately, mark the old unapproved orbit-recovery packet stale, prepare a corrected zero-decision orbit review, and retain both DEM decisions as separate gates.

## What remains prohibited

No optical retry or alternate search, no threshold or source change, no credential or token action, no DEM conversion or install, no orbit request, no radar pixel decoding, no baseline or change analysis, and no scientific or emergency publication.
