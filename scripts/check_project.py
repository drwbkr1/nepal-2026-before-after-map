#!/usr/bin/env python3
"""Validate the lightweight public project repository."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path

from arcgis_final_delivery_core import validate_contract as validate_arcgis_final_delivery_contract
from arcgis_package_portability_core import validate_contract as validate_arcgis_package_portability_contract
from change_evidence_core import validate_contract as validate_change_evidence_contract
from derive_m2_acquisition_checkpoint import current_container_verification_complete, derive_checkpoint
from record_m2_sentinel_continuation_001_implementation_readiness import IMPLEMENTATION_FILES as CONTINUATION_001_IMPLEMENTATION_FILES
from record_m2_sentinel_recovery_002_implementation_readiness import IMPLEMENTATION_FILES as RECOVERY_002_IMPLEMENTATION_FILES
from validate_m2_acquisition_progress import (
    INITIAL_ACTIVE_INTAKE_SHA256,
    validate_progress as validate_acquisition_progress,
)

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    ".gitattributes",
    "AGENTS.md",
    "docs/PROJECT_CHARTER.md",
    "docs/ROADMAP.md",
    "docs/DATA_AND_METHODS_PLAN.md",
    "docs/SOURCES.md",
    "docs/ARCGIS_DELIVERY_PLAN.md",
    "docs/ARCGIS_EVIDENCE_MODEL.md",
    "docs/PIXEL_QA_PROTOCOL.md",
    "docs/OPTICAL_BASELINE_PROCESSING_PROTOCOL.md",
    "docs/M2_SAFE_MATERIALIZATION.md",
    "docs/OPTICAL_INPUT_READINESS_PROTOCOL.md",
    "docs/VALIDATION.md",
    "docs/STATUS.md",
    "docs/DECISIONS.md",
    "contracts/milestone-001.json",
    "contracts/milestone-002-proposal.json",
    "contracts/m2-intake-candidate.json",
    "contracts/milestone-002.json",
    "contracts/m2-intake.json",
    "contracts/milestone-002-sentinel-recovery-proposal.json",
    "contracts/milestone-002-sentinel-recovery-002-proposal.json",
    "contracts/milestone-002-sentinel-continuation-001-proposal.json",
    "contracts/m2-sentinel-continuation-001.json",
    "records/source-gates/m2-sentinel-continuation-001-approval.json",
    "records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json",
    "records/source-gates/m2-sentinel-recovery-002-approval.json",
    "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json",
    "contracts/m2-sentinel-recovery.json",
    "contracts/milestone-002-orbit-recovery-proposal.json",
    "contracts/m2-offline-verification.json",
    "contracts/m2-materialization.json",
    "contracts/milestone-002-dem-amendment-proposal.json",
    "contracts/m2-dem-intake-candidate.json",
    "contracts/m2-dem-intake.json",
    "contracts/m2-dem-offline-verification-candidate.json",
    "contracts/m2-dem-offline-verification.json",
    "contracts/milestone-002-orbit-amendment-proposal.json",
    "contracts/m2-orbit-intake-candidate.json",
    "contracts/m2-orbit-offline-verification-candidate.json",
    "contracts/m2-orbit-intake.json",
    "contracts/m2-orbit-offline-verification.json",
    "records/project-control-profile.json",
    "records/long-term-goal.json",
    "records/evidence-ledger.jsonl",
    "config/aoi/approved-study-areas.geojson",
    "config/aoi/approved-study-areas-epsg32645.json",
    "records/source-gates/aoi-approval.json",
    "records/source-gates/aoi-review-reconciliation.json",
    "records/surface-receipts/m1-approved-aoi-arcgis-validation.json",
    "records/source-manifest.json",
    "records/acquisition-plan.json",
    "records/acquisition/m2-intake-static-dry-run.json",
    "records/acquisition/preflight.json",
    "records/acquisition/preflight-refresh.json",
    "records/acquisition/sentinel-preflight-refresh-readiness.json",
    "records/acquisition/custody-initialization.json",
    "records/acquisition/active-intake-initial-snapshot.json",
    "records/acquisition/transfer-runner-readiness.json",
    "records/acquisition/transfer-runner-attempt-id-correction.json",
    "records/acquisition/acquisition-progress-readiness.json",
    "records/acquisition/acquisition-progress-windows-path-portability-correction.json",
    "records/acquisition/acquisition-checkpoint-readiness.json",
    "records/acquisition/acquisition-checkpoint-portability-correction.json",
    "records/acquisition/sentinel-acquisition-reconciliation-001.json",
    "records/acquisition/sentinel-recovery-publication-gate.json",
    "records/acquisition/sentinel-recovery-activation.json",
    "records/acquisition/recovery-attempts/m1-src-004-recovery-001-20260904t201220z-e4388c64.json",
    "records/acquisition/sentinel-recovery-interruption-reconciliation-001.json",
    "records/acquisition/sentinel-recovery-002-implementation-readiness.json",
    "records/acquisition/sentinel-recovery-002-publication-attempt-001-failure.json",
    "records/acquisition/sentinel-recovery-002-publication-gate.json",
    "records/acquisition/sentinel-continuation-001-publication-attempt-001-failure.json",
    "records/acquisition/sentinel-continuation-001-implementation-readiness-attempt-001-superseded.json",
    "records/acquisition/sentinel-continuation-001-implementation-readiness-attempt-002-superseded.json",
    "records/acquisition/sentinel-continuation-001-implementation-readiness.json",
    "records/acquisition/sentinel-continuation-001-implementation-publication-attempt-001-failure.json",
    "records/acquisition/sentinel-continuation-001-publication-gate.json",
    "records/acquisition/sentinel-continuation-001-activation.json",
    "records/acquisition/sentinel-continuation-001-final-preflight.json",
    "records/acquisition/attempts/m1-src-005-20260905t041205z-f34254c7.json",
    "records/acquisition/attempts/m1-src-006-20260905t041726z-da401f11.json",
    "records/acquisition/attempts/m1-src-008-20260905t042500z-a5fff82c.json",
    "records/acquisition/attempts/m1-src-010-20260905t042938z-e6ca9230.json",
    "records/acquisition/container-verification/m1-src-005-m1-src-005-20260905t041205z-f34254c7.json",
    "records/acquisition/container-verification/m1-src-006-m1-src-006-20260905t041726z-da401f11.json",
    "records/acquisition/container-verification/m1-src-008-m1-src-008-20260905t042500z-a5fff82c.json",
    "records/acquisition/container-verification/m1-src-010-m1-src-010-20260905t042938z-e6ca9230.json",
    "records/acquisition/sentinel-continuation-001-success-reconciliation.json",
    "records/acquisition/sentinel-continuation-001-postsuccess-validation-attempt-001-failure.json",
    "records/acquisition/sentinel-continuation-001-postsuccess-validation-attempt-002-failure.json",
    "records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json",
    "records/acquisition/sentinel-recovery-002-activation.json",
    "records/acquisition/sentinel-recovery-002-final-preflight.json",
    "records/acquisition/recovery-attempts/m1-src-004-recovery-002-20260905t002925z-cc1fe1e9.json",
    "records/acquisition/container-verification/m1-src-004-m1-src-004-recovery-002-20260905t002925z-cc1fe1e9.json",
    "records/acquisition/sentinel-recovery-002-supervisor-reconciliation-001.json",
    "records/acquisition/materialization-test-boundary-reconciliation-001.json",
    "records/acquisition/sentinel-materialization-reconciliation-001.json",
    "records/acquisition/orbit-test-boundary-reconciliation-001.json",
    "records/acquisition/orbit-runner-production-boundary-correction-001.json",
    "records/acquisition/attempts/m1-src-001-20260904t041621z-fe412d8d.json",
    "records/acquisition/attempts/m1-src-002-20260904t042408z-b31b162b.json",
    "records/acquisition/attempts/m1-src-003-20260904t043000z-d1b78c08.json",
    "records/acquisition/attempts/m1-src-004-20260904t043930z-ac125c11.json",
    "records/acquisition/container-verification/m1-src-001-m1-src-001-20260904t041621z-fe412d8d.json",
    "records/acquisition/container-verification/m1-src-002-m1-src-002-20260904t042408z-b31b162b.json",
    "records/acquisition/container-verification/m1-src-003-m1-src-003-20260904t043000z-d1b78c08.json",
    "records/acquisition/materialization/m1-src-001-fixture-must-not-run.json",
    "records/acquisition/materialization/m1-src-002-m1-src-002-materialization-001.json",
    "records/acquisition/materialization/m1-src-003-m1-src-003-materialization-001.json",
    "records/acquisition/orbit-attempts/m2-orb-001-20260904t050937z-8ed21d05.json",
    "records/acquisition/dem-amendment-activation.json",
    "records/acquisition/dem-preflight.json",
    "records/acquisition/dem-custody-initialization.json",
    "records/acquisition/dem-transfer-runner-readiness.json",
    "records/acquisition/dem-acquisition-summary.json",
    "records/acquisition/dem-acquisition-portability-correction.json",
    "records/acquisition/dem-geotiff-verifier-readiness.json",
    "records/acquisition/dem-verification/m2-dem-001.json",
    "records/acquisition/dem-geotiff-verifier-correction-001.json",
    "records/acquisition/dem-verification/m2-dem-001-attempt-002.json",
    "records/acquisition/dem-geotiff-verifier-correction-002.json",
    "records/acquisition/dem-verification/m2-dem-001-attempt-003.json",
    "records/acquisition/dem-verification/m2-dem-002-attempt-001.json",
    "records/acquisition/dem-verification/m2-dem-003-attempt-001.json",
    "records/acquisition/dem-verification/m2-dem-004-attempt-001.json",
    "records/acquisition/dem-verification-completion-readiness.json",
    "records/acquisition/dem-verification-summary.json",
    "records/source-gates/source-manifest-approval.json",
    "records/source-gates/source-manifest-review-reconciliation.json",
    "records/source-gates/m2-activation-approval.json",
    "records/source-gates/m2-activation-review-reconciliation.json",
    "records/source-gates/m2-live-source-gate.json",
    "records/source-gates/m2-live-source-gate-refresh.json",
    "records/source-gates/m2-terms-page-reconciliation.json",
    "records/source-gates/m2-sentinel-recovery-approval.json",
    "records/source-gates/m2-sentinel-recovery-review-reconciliation.json",
    "records/source-gates/m2-dem-metadata-receipt.json",
    "records/source-gates/m2-dem-candidate-manifest.json",
    "records/source-gates/m2-dem-source-gate.json",
    "records/source-gates/m2-dem-amendment-approval.json",
    "records/source-gates/m2-dem-amendment-review-reconciliation.json",
    "records/source-gates/m2-dem-live-source-gate.json",
    "records/source-gates/m2-orbit-metadata-receipt.json",
    "records/source-gates/m2-orbit-candidate-manifest.json",
    "records/source-gates/m2-orbit-source-gate.json",
    "records/source-gates/m2-orbit-amendment-review-reconciliation.json",
    "records/source-gates/m2-orbit-amendment-approval.json",
    "records/source-gates/m2-orbit-live-source-gate.json",
    "records/acquisition/orbit-amendment-activation.json",
    "records/acquisition/orbit-preflight.json",
    "records/acquisition/orbit-custody-initialization-attempt-001-failure.json",
    "records/acquisition/orbit-custody-initialization-attempt-002-readiness.json",
    "records/acquisition/orbit-custody-initialization.json",
    "records/acquisition/orbit-runner-readiness.json",
    "records/acquisition/orbit-intake-schema-validation-failure.json",
    "records/acquisition/orbit-intake-schema-correction.json",
    "records/acquisition/orbit-intake-activation-label-inconsistency.json",
    "records/acquisition/orbit-intake-activation-label-correction.json",
    "docs/M1_SOURCE_MANIFEST_REVIEW.md",
    "docs/assets/m1-source-manifest-review.png",
    "records/surface-receipts/m1-source-manifest-review.json",
    "records/surface-receipts/m1-control-reproducibility.json",
    "records/surface-receipts/arcgis-evidence-workspace.json",
    "records/surface-receipts/pixel-qa-synthetic-arcgis.json",
    "reviews/m1-manifest/review-bundle.json",
    "reviews/m1-manifest/review-contract.json",
    "reviews/m1-manifest/blank-response.json",
    "docs/M2_CONTROLLED_ACQUISITION_REVIEW.md",
    "docs/M2_EXECUTION_RUNBOOK.md",
    "docs/M2_SENTINEL_RECOVERY_REVIEW.md",
    "docs/M2_SENTINEL_RECOVERY_002_REVIEW.md",
    "docs/M2_SENTINEL_CONTINUATION_001_REVIEW.md",
    "docs/M2_ORBIT_RECOVERY_REVIEW.md",
    "docs/M2_OFFLINE_VERIFICATION.md",
    "docs/M2_DEM_AMENDMENT_REVIEW.md",
    "docs/M2_DEM_OFFLINE_VERIFICATION.md",
    "docs/M2_DEM_VERTICAL_DATUM_REVIEW.md",
    "docs/M2_DEM_TERRAIN_RESULT_REVIEW.md",
    "docs/M2_ORBIT_AMENDMENT_REVIEW.md",
    "docs/DEM_TERRAIN_QUALITY_PROTOCOL.md",
    "docs/RADAR_BASELINE_PROCESSING_PROTOCOL.md",
    "docs/assets/m2-dem-amendment-review.png",
    "docs/assets/m2-dem-vertical-datum-review.png",
    "docs/assets/m2-dem-terrain-result-review.png",
    "docs/assets/m2-controlled-acquisition-review.png",
    "docs/assets/m2-orbit-amendment-review.png",
    "docs/assets/m2-sentinel-recovery-review.png",
    "docs/assets/m2-sentinel-recovery-002-review.png",
    "docs/assets/m2-sentinel-continuation-001-review.png",
    "docs/assets/m2-orbit-recovery-review.png",
    "scripts/render_m2_activation_review.py",
    "scripts/prepare_m2_intake.py",
    "scripts/prepare_m2_verification.py",
    "scripts/build_arcgis_evidence_workspace.py",
    "scripts/validate_arcgis_evidence_workspace.py",
    "scripts/pixel_qa_core.py",
    "scripts/validate_pixel_qa_arcgis.py",
    "config/arcgis/evidence-workspace-schema.json",
    "config/qa/pixel-readiness-contract.json",
    "config/qa/candidate-pair-plan.json",
    "config/qa/radar-baseline-processing-contract.json",
    "config/qa/dem-terrain-quality-contract.json",
    "config/qa/dem-terrain-quality-contract-attempt-002.json",
    "config/qa/dem-terrain-quality-contract-attempt-003.json",
    "config/qa/optical-baseline-processing-contract.json",
    "config/qa/optical-input-readiness-contract.json",
    "docs/assets/arcgis-evidence-workspace-preview.png",
    "records/surface-receipts/m2-activation-review.json",
    "records/surface-receipts/arcgis-sar-processing-capability.json",
    "records/surface-receipts/m2-dem-amendment-review.json",
    "records/surface-receipts/m2-dem-radar-control-readiness.json",
    "records/surface-receipts/m2-dem-vertical-datum-capability.json",
    "records/surface-receipts/m2-dem-vertical-datum-review.json",
    "records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json",
    "records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json",
    "records/surface-receipts/m2-dem-terrain-quality.json",
    "records/surface-receipts/m2-dem-terrain-result-review.json",
    "records/surface-receipts/m2-orbit-amendment-review.json",
    "records/surface-receipts/m2-sentinel-recovery-review.json",
    "records/surface-receipts/m2-sentinel-recovery-002-review.json",
    "records/surface-receipts/m2-sentinel-continuation-001-review.json",
    "records/surface-receipts/m2-orbit-recovery-review.json",
    "records/surface-receipts/optical-processing-synthetic-arcgis.json",
    "records/surface-receipts/optical-baseline-control-readiness.json",
    "records/surface-receipts/m2-materialization-readiness.json",
    "records/surface-receipts/optical-input-readiness-synthetic-arcgis.json",
    "records/surface-receipts/optical-input-readiness-control.json",
    "contracts/m2-offline-verification-candidate.json",
    "records/readiness/m2-readiness-audit-input.json",
    "records/readiness/m2-readiness-decision.json",
    "records/readiness/m2-dem-terrain-quality-readiness.json",
    "records/readiness/m2-dem-terrain-quality-ci-correction.json",
    "records/readiness/m2-dem-terrain-quality-attempt-002-readiness.json",
    "records/readiness/m2-dem-terrain-quality-attempt-003-readiness.json",
    "records/readiness/m2-dem-terrain-readiness-input.json",
    "records/readiness/m2-dem-terrain-readiness-decision.json",
    "reviews/m2-activation/review-bundle.json",
    "reviews/m2-activation/review-contract.json",
    "reviews/m2-activation/blank-response.json",
    "reviews/m2-dem-amendment/review-bundle.json",
    "reviews/m2-dem-amendment/review-contract.json",
    "reviews/m2-dem-amendment/blank-response.json",
    "reviews/m2-dem-vertical-datum/review-bundle.json",
    "reviews/m2-dem-vertical-datum/review-contract.json",
    "reviews/m2-dem-vertical-datum/blank-response.json",
    "reviews/m2-dem-terrain-result/review-bundle.json",
    "reviews/m2-dem-terrain-result/review-contract.json",
    "reviews/m2-dem-terrain-result/blank-response.json",
    "reviews/m2-orbit-amendment/review-bundle.json",
    "reviews/m2-orbit-amendment/review-contract.json",
    "reviews/m2-orbit-amendment/blank-response.json",
    "reviews/m2-sentinel-recovery/review-bundle.json",
    "reviews/m2-sentinel-recovery/review-contract.json",
    "reviews/m2-sentinel-recovery/blank-response.json",
    "reviews/m2-sentinel-recovery-002/review-bundle.json",
    "reviews/m2-sentinel-recovery-002/review-contract.json",
    "reviews/m2-sentinel-recovery-002/blank-response.json",
    "reviews/m2-sentinel-continuation-001/review-bundle.json",
    "reviews/m2-sentinel-continuation-001/review-contract.json",
    "reviews/m2-sentinel-continuation-001/blank-response.json",
    "reviews/m2-orbit-recovery/review-bundle.json",
    "reviews/m2-orbit-recovery/review-contract.json",
    "reviews/m2-orbit-recovery/blank-response.json",
    "tests/test_m2_intake.py",
    "tests/test_m2_verification.py",
    "tests/test_arcgis_evidence_schema.py",
    "tests/test_pixel_qa_core.py",
    "tests/test_pair_plan.py",
    "scripts/activate_m2.py",
    "scripts/run_m2_preflight.py",
    "scripts/refresh_m2_preflight.py",
    "scripts/m2_page_identity.py",
    "scripts/complete_m2_preflight.py",
    "scripts/initialize_m2_custody.py",
    "scripts/record_m2_custody_checkpoint.py",
    "scripts/m2_transfer_core.py",
    "scripts/acquire_m2_product.py",
    "scripts/m2_sentinel_recovery_core.py",
    "scripts/render_m2_sentinel_recovery_002_review.py",
    "scripts/render_m2_sentinel_continuation_001_review.py",
    "scripts/m2_sentinel_recovery_002_core.py",
    "scripts/m2_sentinel_recovery_002_broker.py",
    "scripts/m2_sentinel_recovery_002_supervisor.py",
    "scripts/acquire_m2_sentinel_recovery_002.py",
    "scripts/acquire_m2_product_pipe.py",
    "scripts/verify_m2_sentinel_recovery_002_container.py",
    "scripts/reconcile_m2_sentinel_recovery_002_supervisor.py",
    "scripts/reconcile_m2_sentinel_recovery_002_success.py",
    "scripts/reconcile_m2_sentinel_recovery_002_outcome.py",
    "scripts/activate_m2_sentinel_recovery_002.py",
    "scripts/preflight_m2_sentinel_recovery_002.py",
    "scripts/record_m2_sentinel_recovery_002_publication_gate.py",
    "scripts/record_m2_sentinel_recovery_002_implementation_readiness.py",
    "scripts/m2_sentinel_continuation_001_core.py",
    "scripts/m2_sentinel_continuation_001_broker.py",
    "scripts/m2_sentinel_continuation_001_supervisor.py",
    "scripts/acquire_m2_sentinel_continuation_001.py",
    "scripts/reconcile_m2_sentinel_continuation_001_success.py",
    "scripts/reconcile_m2_sentinel_continuation_001_postsuccess.py",
    "scripts/activate_m2_sentinel_continuation_001.py",
    "scripts/preflight_m2_sentinel_continuation_001.py",
    "scripts/record_m2_sentinel_continuation_001_publication_gate.py",
    "scripts/record_m2_sentinel_continuation_001_implementation_readiness.py",
    "scripts/acquire_m2_sentinel_recovery.py",
    "scripts/verify_m2_sentinel_recovery_container.py",
    "scripts/activate_m2_sentinel_recovery.py",
    "scripts/record_m2_sentinel_recovery_publication_gate.py",
    "scripts/record_m2_transfer_readiness.py",
    "scripts/validate_m2_acquisition_progress.py",
    "scripts/derive_m2_acquisition_checkpoint.py",
    "scripts/validate_pair_plan.py",
    "tests/test_m2_transfer_core.py",
    "tests/test_m2_page_identity.py",
    "tests/test_m2_acquisition_progress.py",
    "tests/test_m2_checkpoint_reconciliation.py",
    "tests/test_m2_sentinel_recovery.py",
    "tests/test_m2_sentinel_recovery_002.py",
    "tests/test_m2_sentinel_continuation_001.py",
    "tests/test_m2_active_verification.py",
    "tests/test_m2_dem_amendment.py",
    "tests/test_m2_dem_controls.py",
    "tests/test_m2_dem_activation.py",
    "tests/test_m2_dem_preflight.py",
    "tests/test_m2_dem_transfer.py",
    "tests/test_m2_dem_acquisition_progress.py",
    "tests/test_m2_dem_verification_completion.py",
    "tests/test_m2_dem_active_geotiff.py",
    "tests/test_m2_dem_vertical_datum_review.py",
    "tests/test_m2_orbit_amendment.py",
    "tests/test_m2_orbit_activation.py",
    "tests/test_m2_orbit_preflight.py",
    "tests/test_m2_orbit_io.py",
    "tests/test_dem_terrain_quality_core.py",
    "tests/test_radar_processing_contract.py",
    "tests/test_optical_processing_core.py",
    "tests/test_m2_materialization.py",
    "tests/test_optical_input_readiness.py",
    "tests/test_radar_input_readiness.py",
    "scripts/activate_m2_verification.py",
    "scripts/verify_m2_product_container.py",
    "scripts/inspect_arcgis_sar_capability.py",
    "scripts/prepare_m2_dem_amendment.py",
    "scripts/prepare_m2_dem_controls.py",
    "scripts/activate_m2_dem_amendment.py",
    "scripts/run_m2_dem_preflight.py",
    "scripts/complete_m2_dem_preflight.py",
    "scripts/acquire_m2_dem_tile.py",
    "scripts/reconcile_m2_dem_acquisition.py",
    "scripts/verify_m2_dem_geotiff.py",
    "scripts/complete_m2_dem_verification.py",
    "scripts/inspect_m2_dem_vertical_datum_arcgis.py",
    "scripts/render_m2_dem_vertical_datum_review.py",
    "scripts/render_m2_dem_terrain_result_review.py",
    "scripts/prepare_m2_orbit_amendment.py",
    "scripts/prepare_m2_orbit_controls.py",
    "scripts/render_m2_orbit_amendment_review.py",
    "scripts/render_m2_sentinel_recovery_review.py",
    "scripts/render_m2_orbit_recovery_review.py",
    "scripts/activate_m2_orbit_amendment.py",
    "scripts/run_m2_orbit_preflight.py",
    "scripts/initialize_m2_orbit_custody.py",
    "scripts/m2_orbit_io_core.py",
    "scripts/acquire_m2_orbit_file.py",
    "scripts/verify_m2_orbit_eof.py",
    "scripts/dem_terrain_quality_core.py",
    "scripts/inspect_m2_dem_terrain_quality_arcgis.py",
    "scripts/inspect_m2_dem_terrain_quality_arcgis_attempt_003.py",
    "scripts/prepare_radar_processing_contract.py",
    "scripts/optical_processing_core.py",
    "scripts/prepare_optical_processing_contract.py",
    "scripts/validate_optical_processing_arcgis.py",
    "scripts/m2_materialization_core.py",
    "scripts/prepare_m2_materialization.py",
    "scripts/materialize_m2_product.py",
    "scripts/optical_input_readiness_core.py",
    "scripts/prepare_optical_input_readiness_contract.py",
    "scripts/inspect_optical_inputs_arcgis.py",
    "scripts/validate_optical_input_readiness_arcgis.py",
    "scripts/radar_input_readiness_core.py",
    "scripts/prepare_radar_input_readiness_contract.py",
    "scripts/inspect_radar_inputs_arcgis.py",
    "scripts/validate_radar_input_readiness_arcgis.py",
    "config/qa/radar-input-readiness-contract.json",
    "docs/RADAR_INPUT_READINESS_PROTOCOL.md",
    "records/surface-receipts/radar-input-readiness-control.json",
    "records/surface-receipts/radar-input-readiness-synthetic-arcgis.json",
    "records/readiness/radar-input/m2-s1-input-readiness-real-001.json",
    "records/surface-receipts/radar-input-readiness-real-reconciliation.json",
    "records/source-gates/m2-radar-input-label-specification-source-gate.json",
    "contracts/milestone-002-radar-input-readiness-amendment-proposal.json",
    "docs/M2_RADAR_INPUT_READINESS_AMENDMENT_REVIEW.md",
    "docs/assets/m2-radar-input-readiness-amendment-review.png",
    "scripts/render_m2_radar_input_readiness_amendment_review.py",
    "records/surface-receipts/m2-radar-input-readiness-amendment-review.json",
    "reviews/m2-radar-input-readiness-amendment/review-bundle.json",
    "reviews/m2-radar-input-readiness-amendment/review-contract.json",
    "reviews/m2-radar-input-readiness-amendment/blank-response.json",
    "records/source-gates/m2-radar-input-readiness-amendment-review-reconciliation.json",
    "records/source-gates/m2-radar-input-readiness-amendment-approval.json",
    "scripts/activate_m2_radar_input_readiness_amendment.py",
    "scripts/radar_input_readiness_core_amendment_001.py",
    "scripts/inspect_radar_inputs_arcgis_amendment_001.py",
    "scripts/validate_radar_input_readiness_arcgis_amendment_001.py",
    "tests/test_radar_input_readiness_amendment_001.py",
    "config/qa/radar-input-readiness-contract-amendment-001.json",
    "records/readiness/radar-input/m2-radar-input-readiness-amendment-activation.json",
    "records/surface-receipts/radar-input-readiness-synthetic-arcgis-amendment-001.json",
    "scripts/reconcile_radar_input_readiness_amendment_001.py",
    "scripts/complete_radar_input_readiness_amendment_001.py",
    "records/readiness/radar-input/m2-s1-input-readiness-real-002.json",
    "records/surface-receipts/radar-input-readiness-amendment-real-002-reconciliation.json",
    "records/surface-receipts/radar-input-readiness-synthetic-arcgis-prepublication-001.json",
    "records/surface-receipts/radar-input-readiness-synthetic-arcgis-attempt-002-failure.json",
    "records/surface-receipts/radar-input-readiness-synthetic-arcgis-prepublication-003.json",
    "records/surface-receipts/radar-input-readiness-synthetic-arcgis-prepublication-004.json",
    "records/surface-receipts/radar-input-readiness-synthetic-arcgis-prepublication-005.json",
    "records/surface-receipts/radar-input-readiness-synthetic-arcgis-prepublication-006.json",
    "records/readiness/radar-input/prepublication-contract-001.json",
    "records/readiness/radar-input/prepublication-contract-002.json",
    "records/readiness/radar-input/prepublication-contract-003.json",
    "records/readiness/radar-input/prepublication-contract-004.json",
    "records/readiness/radar-input/prepublication-contract-005.json",
    "records/readiness/radar-input/prepublication-contract-006.json",
    "config/qa/arcgis-package-portability-contract.json",
    "docs/ARCGIS_PACKAGE_PORTABILITY_PROTOCOL.md",
    "scripts/arcgis_package_portability_core.py",
    "scripts/run_arcgis_package_portability_arcgis.py",
    "tests/test_arcgis_package_portability.py",
    "records/readiness/arcgis-package-portability-control.json",
    "records/surface-receipts/arcgis-package-portability-postrun-boundary-deviation.json",
    "records/surface-receipts/arcgis-package-portability.json",
    "config/qa/arcgis-final-delivery-contract.json",
    "docs/ARCGIS_FINAL_DELIVERY_ACCEPTANCE.md",
    "scripts/arcgis_final_delivery_core.py",
    "tests/test_arcgis_final_delivery.py",
    "records/readiness/m6-arcgis-final-delivery-control-readiness.json",
    "config/qa/change-evidence-contract.json",
    "docs/CHANGE_EVIDENCE_PROTOCOL.md",
    "scripts/change_evidence_core.py",
    "tests/test_change_evidence_core.py",
    "records/readiness/m4-change-evidence-control-readiness.json",
    "scripts/render_m2_dem_amendment_review.py",
    "contracts/m2-dem-vertical-datum-proposal.json",
    "contracts/m2-dem-terrain-result-review-proposal.json",
    "records/source-gates/m2-dem-vertical-datum-source-review.json",
    ".github/workflows/validate.yml",
]

FORBIDDEN_SUFFIXES = {
    ".tif", ".tiff", ".jp2", ".img", ".nc", ".hdf", ".h5",
    ".zip", ".7z", ".gpkg", ".shp", ".ppkx", ".mpkx", ".lpkx", ".slpk",
}

FORBIDDEN_NAME_PARTS = (
    "credential", "secret", "access_token", "refresh_token", "private_key",
)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def validate_review_bundle(
    bundle_relative: str,
    contract_relative: str,
    *,
    verify_current_artifacts: bool = True,
) -> None:
    bundle = json.loads((ROOT / bundle_relative).read_text(encoding="utf-8"))
    review_contract = json.loads((ROOT / contract_relative).read_text(encoding="utf-8"))
    if review_contract["review_bundle"]["manifest_sha256"] != sha256(bundle_relative):
        fail(f"review contract does not bind exact bundle bytes: {bundle_relative}")
    if review_contract["review_bundle"]["candidate_identity"] != bundle["candidate_identity"]:
        fail(f"review contract candidate differs from bundle: {bundle_relative}")
    if verify_current_artifacts:
        for artifact in bundle["artifacts"]:
            if artifact["sha256"] != sha256(artifact["path"]):
                fail(f"review bundle artifact hash differs: {artifact['path']}")
            for receipt in artifact["render_receipts"]:
                if receipt["sha256"] != sha256(receipt["path"]):
                    fail(f"review bundle render receipt hash differs: {receipt['path']}")


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    profile = json.loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "contracts/milestone-001.json").read_text(encoding="utf-8"))
    m2_proposal = json.loads((ROOT / "contracts/milestone-002-proposal.json").read_text(encoding="utf-8"))
    active_m2 = json.loads((ROOT / "contracts/milestone-002.json").read_text(encoding="utf-8"))
    dem_proposal = json.loads((ROOT / "contracts/milestone-002-dem-amendment-proposal.json").read_text(encoding="utf-8"))
    dem_receipt = json.loads((ROOT / "records/source-gates/m2-dem-metadata-receipt.json").read_text(encoding="utf-8"))
    dem_manifest = json.loads((ROOT / "records/source-gates/m2-dem-candidate-manifest.json").read_text(encoding="utf-8"))
    dem_gate = json.loads((ROOT / "records/source-gates/m2-dem-source-gate.json").read_text(encoding="utf-8"))
    dem_bundle = json.loads((ROOT / "reviews/m2-dem-amendment/review-bundle.json").read_text(encoding="utf-8"))
    dem_contract = json.loads((ROOT / "reviews/m2-dem-amendment/review-contract.json").read_text(encoding="utf-8"))
    dem_blank = json.loads((ROOT / "reviews/m2-dem-amendment/blank-response.json").read_text(encoding="utf-8"))
    dem_reconciliation = json.loads((ROOT / "records/source-gates/m2-dem-amendment-review-reconciliation.json").read_text(encoding="utf-8"))
    dem_approval = json.loads((ROOT / "records/source-gates/m2-dem-amendment-approval.json").read_text(encoding="utf-8"))
    sar_capability = json.loads((ROOT / "records/surface-receipts/arcgis-sar-processing-capability.json").read_text(encoding="utf-8"))
    dem_intake_candidate = json.loads((ROOT / "contracts/m2-dem-intake-candidate.json").read_text(encoding="utf-8"))
    dem_intake_active = json.loads((ROOT / "contracts/m2-dem-intake.json").read_text(encoding="utf-8"))
    dem_verification_candidate = json.loads((ROOT / "contracts/m2-dem-offline-verification-candidate.json").read_text(encoding="utf-8"))
    dem_verification_active = json.loads((ROOT / "contracts/m2-dem-offline-verification.json").read_text(encoding="utf-8"))
    dem_activation_receipt = json.loads((ROOT / "records/acquisition/dem-amendment-activation.json").read_text(encoding="utf-8"))
    dem_live_source_gate = json.loads((ROOT / "records/source-gates/m2-dem-live-source-gate.json").read_text(encoding="utf-8"))
    dem_preflight = json.loads((ROOT / "records/acquisition/dem-preflight.json").read_text(encoding="utf-8"))
    dem_custody_receipt = json.loads((ROOT / "records/acquisition/dem-custody-initialization.json").read_text(encoding="utf-8"))
    dem_transfer_readiness = json.loads((ROOT / "records/acquisition/dem-transfer-runner-readiness.json").read_text(encoding="utf-8"))
    dem_acquisition_summary = json.loads((ROOT / "records/acquisition/dem-acquisition-summary.json").read_text(encoding="utf-8"))
    dem_acquisition_portability = json.loads((ROOT / "records/acquisition/dem-acquisition-portability-correction.json").read_text(encoding="utf-8"))
    dem_vertical_proposal = json.loads((ROOT / "contracts/m2-dem-vertical-datum-proposal.json").read_text(encoding="utf-8"))
    dem_vertical_sources = json.loads((ROOT / "records/source-gates/m2-dem-vertical-datum-source-review.json").read_text(encoding="utf-8"))
    dem_vertical_capability = json.loads((ROOT / "records/surface-receipts/m2-dem-vertical-datum-capability.json").read_text(encoding="utf-8"))
    dem_vertical_bundle = json.loads((ROOT / "reviews/m2-dem-vertical-datum/review-bundle.json").read_text(encoding="utf-8"))
    dem_vertical_contract = json.loads((ROOT / "reviews/m2-dem-vertical-datum/review-contract.json").read_text(encoding="utf-8"))
    dem_vertical_blank = json.loads((ROOT / "reviews/m2-dem-vertical-datum/blank-response.json").read_text(encoding="utf-8"))
    dem_terrain_contract = json.loads((ROOT / "config/qa/dem-terrain-quality-contract.json").read_text(encoding="utf-8"))
    dem_terrain_readiness = json.loads((ROOT / "records/readiness/m2-dem-terrain-quality-readiness.json").read_text(encoding="utf-8"))
    dem_terrain_ci_correction = json.loads((ROOT / "records/readiness/m2-dem-terrain-quality-ci-correction.json").read_text(encoding="utf-8"))
    dem_terrain_attempt_001_failure = json.loads((ROOT / "records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json").read_text(encoding="utf-8"))
    dem_terrain_attempt_002_contract = json.loads((ROOT / "config/qa/dem-terrain-quality-contract-attempt-002.json").read_text(encoding="utf-8"))
    dem_terrain_attempt_002_readiness = json.loads((ROOT / "records/readiness/m2-dem-terrain-quality-attempt-002-readiness.json").read_text(encoding="utf-8"))
    dem_terrain_attempt_002_failure = json.loads((ROOT / "records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json").read_text(encoding="utf-8"))
    dem_terrain_attempt_003_contract = json.loads((ROOT / "config/qa/dem-terrain-quality-contract-attempt-003.json").read_text(encoding="utf-8"))
    dem_terrain_attempt_003_readiness = json.loads((ROOT / "records/readiness/m2-dem-terrain-quality-attempt-003-readiness.json").read_text(encoding="utf-8"))
    dem_terrain_result = json.loads((ROOT / "records/surface-receipts/m2-dem-terrain-quality.json").read_text(encoding="utf-8"))
    dem_terrain_audit_input = json.loads((ROOT / "records/readiness/m2-dem-terrain-readiness-input.json").read_text(encoding="utf-8"))
    dem_terrain_audit_decision = json.loads((ROOT / "records/readiness/m2-dem-terrain-readiness-decision.json").read_text(encoding="utf-8"))
    dem_terrain_review_proposal = json.loads((ROOT / "contracts/m2-dem-terrain-result-review-proposal.json").read_text(encoding="utf-8"))
    dem_terrain_review_surface = json.loads((ROOT / "records/surface-receipts/m2-dem-terrain-result-review.json").read_text(encoding="utf-8"))
    dem_terrain_review_bundle = json.loads((ROOT / "reviews/m2-dem-terrain-result/review-bundle.json").read_text(encoding="utf-8"))
    dem_terrain_review_contract = json.loads((ROOT / "reviews/m2-dem-terrain-result/review-contract.json").read_text(encoding="utf-8"))
    dem_terrain_review_blank = json.loads((ROOT / "reviews/m2-dem-terrain-result/blank-response.json").read_text(encoding="utf-8"))
    orbit_proposal = json.loads((ROOT / "contracts/milestone-002-orbit-amendment-proposal.json").read_text(encoding="utf-8"))
    orbit_receipt = json.loads((ROOT / "records/source-gates/m2-orbit-metadata-receipt.json").read_text(encoding="utf-8"))
    orbit_manifest = json.loads((ROOT / "records/source-gates/m2-orbit-candidate-manifest.json").read_text(encoding="utf-8"))
    orbit_gate = json.loads((ROOT / "records/source-gates/m2-orbit-source-gate.json").read_text(encoding="utf-8"))
    orbit_intake = json.loads((ROOT / "contracts/m2-orbit-intake-candidate.json").read_text(encoding="utf-8"))
    orbit_verification = json.loads((ROOT / "contracts/m2-orbit-offline-verification-candidate.json").read_text(encoding="utf-8"))
    orbit_surface = json.loads((ROOT / "records/surface-receipts/m2-orbit-amendment-review.json").read_text(encoding="utf-8"))
    orbit_bundle = json.loads((ROOT / "reviews/m2-orbit-amendment/review-bundle.json").read_text(encoding="utf-8"))
    orbit_contract = json.loads((ROOT / "reviews/m2-orbit-amendment/review-contract.json").read_text(encoding="utf-8"))
    orbit_blank = json.loads((ROOT / "reviews/m2-orbit-amendment/blank-response.json").read_text(encoding="utf-8"))
    orbit_reconciliation = json.loads((ROOT / "records/source-gates/m2-orbit-amendment-review-reconciliation.json").read_text(encoding="utf-8"))
    orbit_approval = json.loads((ROOT / "records/source-gates/m2-orbit-amendment-approval.json").read_text(encoding="utf-8"))
    orbit_active_intake = json.loads((ROOT / "contracts/m2-orbit-intake.json").read_text(encoding="utf-8"))
    orbit_active_verification = json.loads((ROOT / "contracts/m2-orbit-offline-verification.json").read_text(encoding="utf-8"))
    orbit_activation = json.loads((ROOT / "records/acquisition/orbit-amendment-activation.json").read_text(encoding="utf-8"))
    orbit_live_gate = json.loads((ROOT / "records/source-gates/m2-orbit-live-source-gate.json").read_text(encoding="utf-8"))
    orbit_preflight = json.loads((ROOT / "records/acquisition/orbit-preflight.json").read_text(encoding="utf-8"))
    orbit_custody_failure = json.loads((ROOT / "records/acquisition/orbit-custody-initialization-attempt-001-failure.json").read_text(encoding="utf-8"))
    orbit_custody_readiness = json.loads((ROOT / "records/acquisition/orbit-custody-initialization-attempt-002-readiness.json").read_text(encoding="utf-8"))
    orbit_custody = json.loads((ROOT / "records/acquisition/orbit-custody-initialization.json").read_text(encoding="utf-8"))
    orbit_runner_readiness = json.loads((ROOT / "records/acquisition/orbit-runner-readiness.json").read_text(encoding="utf-8"))
    orbit_intake_schema_failure = json.loads((ROOT / "records/acquisition/orbit-intake-schema-validation-failure.json").read_text(encoding="utf-8"))
    orbit_intake_schema_correction = json.loads((ROOT / "records/acquisition/orbit-intake-schema-correction.json").read_text(encoding="utf-8"))
    orbit_intake_label_inconsistency = json.loads((ROOT / "records/acquisition/orbit-intake-activation-label-inconsistency.json").read_text(encoding="utf-8"))
    orbit_intake_label_correction = json.loads((ROOT / "records/acquisition/orbit-intake-activation-label-correction.json").read_text(encoding="utf-8"))
    sentinel_recovery_proposal = json.loads((ROOT / "contracts/milestone-002-sentinel-recovery-proposal.json").read_text(encoding="utf-8"))
    sentinel_acquisition_reconciliation = json.loads((ROOT / "records/acquisition/sentinel-acquisition-reconciliation-001.json").read_text(encoding="utf-8"))
    sentinel_recovery_surface = json.loads((ROOT / "records/surface-receipts/m2-sentinel-recovery-review.json").read_text(encoding="utf-8"))
    sentinel_recovery_bundle = json.loads((ROOT / "reviews/m2-sentinel-recovery/review-bundle.json").read_text(encoding="utf-8"))
    sentinel_recovery_contract = json.loads((ROOT / "reviews/m2-sentinel-recovery/review-contract.json").read_text(encoding="utf-8"))
    sentinel_recovery_blank = json.loads((ROOT / "reviews/m2-sentinel-recovery/blank-response.json").read_text(encoding="utf-8"))
    sentinel_recovery_approval = json.loads((ROOT / "records/source-gates/m2-sentinel-recovery-approval.json").read_text(encoding="utf-8"))
    sentinel_recovery_review_reconciliation = json.loads((ROOT / "records/source-gates/m2-sentinel-recovery-review-reconciliation.json").read_text(encoding="utf-8"))
    sentinel_recovery_active_contract = json.loads((ROOT / "contracts/m2-sentinel-recovery.json").read_text(encoding="utf-8"))
    sentinel_recovery_publication_gate = json.loads((ROOT / "records/acquisition/sentinel-recovery-publication-gate.json").read_text(encoding="utf-8"))
    sentinel_recovery_activation = json.loads((ROOT / "records/acquisition/sentinel-recovery-activation.json").read_text(encoding="utf-8"))
    sentinel_recovery_attempt = json.loads((ROOT / "records/acquisition/recovery-attempts/m1-src-004-recovery-001-20260904t201220z-e4388c64.json").read_text(encoding="utf-8"))
    sentinel_recovery_interruption = json.loads((ROOT / "records/acquisition/sentinel-recovery-interruption-reconciliation-001.json").read_text(encoding="utf-8"))
    sentinel_recovery_002_proposal = json.loads((ROOT / "contracts/milestone-002-sentinel-recovery-002-proposal.json").read_text(encoding="utf-8"))
    sentinel_recovery_002_surface = json.loads((ROOT / "records/surface-receipts/m2-sentinel-recovery-002-review.json").read_text(encoding="utf-8"))
    sentinel_recovery_002_bundle = json.loads((ROOT / "reviews/m2-sentinel-recovery-002/review-bundle.json").read_text(encoding="utf-8"))
    sentinel_recovery_002_contract = json.loads((ROOT / "reviews/m2-sentinel-recovery-002/review-contract.json").read_text(encoding="utf-8"))
    sentinel_recovery_002_blank = json.loads((ROOT / "reviews/m2-sentinel-recovery-002/blank-response.json").read_text(encoding="utf-8"))
    sentinel_recovery_002_approval = json.loads((ROOT / "records/source-gates/m2-sentinel-recovery-002-approval.json").read_text(encoding="utf-8"))
    sentinel_recovery_002_reconciliation = json.loads((ROOT / "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json").read_text(encoding="utf-8"))
    sentinel_recovery_002_readiness = json.loads((ROOT / "records/acquisition/sentinel-recovery-002-implementation-readiness.json").read_text(encoding="utf-8"))
    materialization_boundary_reconciliation = json.loads((ROOT / "records/acquisition/materialization-test-boundary-reconciliation-001.json").read_text(encoding="utf-8"))
    materialization_receipt = json.loads((ROOT / "records/acquisition/materialization/m1-src-001-fixture-must-not-run.json").read_text(encoding="utf-8"))
    sentinel_materialization_reconciliation = json.loads((ROOT / "records/acquisition/sentinel-materialization-reconciliation-001.json").read_text(encoding="utf-8"))
    sentinel_materialization_receipts = {
        "M1-SRC-001": materialization_receipt,
        "M1-SRC-002": json.loads((ROOT / "records/acquisition/materialization/m1-src-002-m1-src-002-materialization-001.json").read_text(encoding="utf-8")),
        "M1-SRC-003": json.loads((ROOT / "records/acquisition/materialization/m1-src-003-m1-src-003-materialization-001.json").read_text(encoding="utf-8")),
    }
    orbit_boundary_reconciliation = json.loads((ROOT / "records/acquisition/orbit-test-boundary-reconciliation-001.json").read_text(encoding="utf-8"))
    orbit_boundary_correction = json.loads((ROOT / "records/acquisition/orbit-runner-production-boundary-correction-001.json").read_text(encoding="utf-8"))
    orbit_failed_attempt = json.loads((ROOT / "records/acquisition/orbit-attempts/m2-orb-001-20260904t050937z-8ed21d05.json").read_text(encoding="utf-8"))
    orbit_recovery_proposal = json.loads((ROOT / "contracts/milestone-002-orbit-recovery-proposal.json").read_text(encoding="utf-8"))
    orbit_recovery_surface = json.loads((ROOT / "records/surface-receipts/m2-orbit-recovery-review.json").read_text(encoding="utf-8"))
    orbit_recovery_bundle = json.loads((ROOT / "reviews/m2-orbit-recovery/review-bundle.json").read_text(encoding="utf-8"))
    orbit_recovery_contract = json.loads((ROOT / "reviews/m2-orbit-recovery/review-contract.json").read_text(encoding="utf-8"))
    orbit_recovery_blank = json.loads((ROOT / "reviews/m2-orbit-recovery/blank-response.json").read_text(encoding="utf-8"))
    expected_dem_source_order = ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"]
    dem_current_assets = dem_intake_active.get("assets", [])
    if [asset.get("extensions", {}).get("source_id") for asset in dem_current_assets] != expected_dem_source_order:
        fail("active M2 DEM intake source order or identity differs")
    dem_current_states = [asset.get("state") for asset in dem_current_assets]
    if len(dem_current_assets) != 4 or any(state not in {"authorized", "promoted", "failed"} for state in dem_current_states):
        fail("active M2 DEM intake has an unsupported or unreconciled state")
    dem_state_counts = {state: dem_current_states.count(state) for state in ("authorized", "promoted", "failed")}
    dem_all_geotiff_verified = all(
        asset.get("extensions", {}).get("geotiff_verification_status") == "pass_structural_and_full_tile_finite"
        for asset in dem_current_assets
    )
    if dem_state_counts["failed"]:
        expected_dem_transfer_checkpoint = "M2-DEM-ACQUISITION-REVIEW"
        expected_dem_checkpoint = expected_dem_transfer_checkpoint
        expected_dem_intake_status = "active_acquisition_review_required"
        expected_dem_verification_status = "active_gate_blocked_acquisition_review"
        expected_dem_next_action = "Review the retained DEM transfer failure; do not retry or advance to GeoTIFF verification without a new bounded decision."
    elif dem_state_counts["promoted"] == 4:
        expected_dem_transfer_checkpoint = "M2-DEM-GEOTIFF-VERIFICATION"
        if dem_all_geotiff_verified:
            expected_dem_checkpoint = "M2-DEM-VERTICAL-DATUM-REVIEW"
            expected_dem_intake_status = "active_geotiff_verified_vertical_datum_deferred"
            expected_dem_verification_status = "complete_structural_and_valid_coverage_vertical_datum_deferred"
            expected_dem_next_action = "Review and explicitly resolve the EGM2008-to-ArcGIS-EGM96 vertical-datum route before any Sentinel-1 terrain correction; do not silently select GEOID or NONE."
        else:
            expected_dem_checkpoint = expected_dem_transfer_checkpoint
            expected_dem_intake_status = "active_all_promoted_pending_geotiff_verification"
            expected_dem_verification_status = "active_gate_ready_for_geotiff_verification"
            expected_dem_next_action = "Run the active offline ArcGIS GeoTIFF verifier for each of the four promoted DEM tiles; do not infer pixel or vertical-datum fitness from transfer success."
    elif dem_state_counts["promoted"]:
        expected_dem_transfer_checkpoint = "M2-DEM-ACQUISITION"
        expected_dem_checkpoint = expected_dem_transfer_checkpoint
        expected_dem_intake_status = "active_acquisition_in_progress"
        expected_dem_verification_status = "active_gate_deferred_incomplete_acquisition"
        next_dem_source = next(asset["extensions"]["source_id"] for asset in dem_current_assets if asset["state"] == "authorized")
        expected_dem_next_action = f"Acquire {next_dem_source} only through append-only staging, exact size and local SHA-256, and no-replace promotion."
    else:
        expected_dem_transfer_checkpoint = "M2-DEM-ACQUISITION"
        expected_dem_checkpoint = expected_dem_transfer_checkpoint
        expected_dem_intake_status = "active_authorized_preflight_passed_custody_initialized"
        expected_dem_verification_status = "active_gate_deferred_no_promoted_rasters"
        expected_dem_next_action = "Acquire M2-DEM-001 only through append-only staging, verify its exact length and local SHA-256, and promote without replacement; stop on any route or identity drift."
    radar_processing_contract = json.loads((ROOT / "config/qa/radar-baseline-processing-contract.json").read_text(encoding="utf-8"))
    dem_radar_readiness = json.loads((ROOT / "records/surface-receipts/m2-dem-radar-control-readiness.json").read_text(encoding="utf-8"))
    optical_processing_contract = json.loads((ROOT / "config/qa/optical-baseline-processing-contract.json").read_text(encoding="utf-8"))
    optical_arcgis_receipt = json.loads((ROOT / "records/surface-receipts/optical-processing-synthetic-arcgis.json").read_text(encoding="utf-8"))
    optical_readiness = json.loads((ROOT / "records/surface-receipts/optical-baseline-control-readiness.json").read_text(encoding="utf-8"))
    materialization_contract = json.loads((ROOT / "contracts/m2-materialization.json").read_text(encoding="utf-8"))
    materialization_readiness = json.loads((ROOT / "records/surface-receipts/m2-materialization-readiness.json").read_text(encoding="utf-8"))
    optical_input_contract = json.loads((ROOT / "config/qa/optical-input-readiness-contract.json").read_text(encoding="utf-8"))
    optical_input_arcgis = json.loads((ROOT / "records/surface-receipts/optical-input-readiness-synthetic-arcgis.json").read_text(encoding="utf-8"))
    optical_input_readiness = json.loads((ROOT / "records/surface-receipts/optical-input-readiness-control.json").read_text(encoding="utf-8"))
    radar_input_contract = json.loads((ROOT / "config/qa/radar-input-readiness-contract.json").read_text(encoding="utf-8"))
    radar_input_arcgis = json.loads((ROOT / "records/surface-receipts/radar-input-readiness-synthetic-arcgis.json").read_text(encoding="utf-8"))
    radar_input_readiness = json.loads((ROOT / "records/surface-receipts/radar-input-readiness-control.json").read_text(encoding="utf-8"))
    radar_input_failure = json.loads((ROOT / "records/surface-receipts/radar-input-readiness-synthetic-arcgis-attempt-002-failure.json").read_text(encoding="utf-8"))
    radar_input_real = json.loads((ROOT / "records/readiness/radar-input/m2-s1-input-readiness-real-001.json").read_text(encoding="utf-8"))
    radar_input_real_reconciliation = json.loads((ROOT / "records/surface-receipts/radar-input-readiness-real-reconciliation.json").read_text(encoding="utf-8"))
    radar_label_source_gate = json.loads((ROOT / "records/source-gates/m2-radar-input-label-specification-source-gate.json").read_text(encoding="utf-8"))
    radar_label_amendment = json.loads((ROOT / "contracts/milestone-002-radar-input-readiness-amendment-proposal.json").read_text(encoding="utf-8"))
    radar_label_review_surface = json.loads((ROOT / "records/surface-receipts/m2-radar-input-readiness-amendment-review.json").read_text(encoding="utf-8"))
    radar_label_review_bundle = json.loads((ROOT / "reviews/m2-radar-input-readiness-amendment/review-bundle.json").read_text(encoding="utf-8"))
    radar_label_review_contract = json.loads((ROOT / "reviews/m2-radar-input-readiness-amendment/review-contract.json").read_text(encoding="utf-8"))
    radar_label_blank_response = json.loads((ROOT / "reviews/m2-radar-input-readiness-amendment/blank-response.json").read_text(encoding="utf-8"))
    radar_label_review_reconciliation = json.loads((ROOT / "records/source-gates/m2-radar-input-readiness-amendment-review-reconciliation.json").read_text(encoding="utf-8"))
    radar_label_approval = json.loads((ROOT / "records/source-gates/m2-radar-input-readiness-amendment-approval.json").read_text(encoding="utf-8"))
    radar_label_contract = json.loads((ROOT / "config/qa/radar-input-readiness-contract-amendment-001.json").read_text(encoding="utf-8"))
    radar_label_activation = json.loads((ROOT / "records/readiness/radar-input/m2-radar-input-readiness-amendment-activation.json").read_text(encoding="utf-8"))
    radar_label_synthetic = json.loads((ROOT / "records/surface-receipts/radar-input-readiness-synthetic-arcgis-amendment-001.json").read_text(encoding="utf-8"))
    radar_label_real_002 = json.loads((ROOT / "records/readiness/radar-input/m2-s1-input-readiness-real-002.json").read_text(encoding="utf-8"))
    radar_label_real_002_reconciliation = json.loads((ROOT / "records/surface-receipts/radar-input-readiness-amendment-real-002-reconciliation.json").read_text(encoding="utf-8"))
    goal = json.loads((ROOT / "records/long-term-goal.json").read_text(encoding="utf-8"))
    continuation_success = json.loads((ROOT / "records/acquisition/sentinel-continuation-001-success-reconciliation.json").read_text(encoding="utf-8"))
    continuation_postsuccess_failure = json.loads((ROOT / "records/acquisition/sentinel-continuation-001-postsuccess-validation-attempt-001-failure.json").read_text(encoding="utf-8"))
    continuation_postsuccess_failure_002 = json.loads((ROOT / "records/acquisition/sentinel-continuation-001-postsuccess-validation-attempt-002-failure.json").read_text(encoding="utf-8"))
    continuation_postsuccess = json.loads((ROOT / "records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json").read_text(encoding="utf-8"))

    expected_remote = profile["project"]["repository_identity"]["expected_remote"]
    remote_project_name = expected_remote.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    if profile["project"]["name"] != remote_project_name:
        fail("project name does not match canonical repository identity")
    if profile["project"]["repository_identity"]["default_branch"] != "main":
        fail("expected default branch must be main")
    if profile.get("control_surfaces", {}).get("proposed_amendments") != []:
        fail("project profile must clear the approved Sentinel recovery-002 proposal")
    if profile.get("control_surfaces", {}).get("activated_amendments") != [
        "records/source-gates/m2-dem-amendment-approval.json",
        "records/source-gates/m2-orbit-amendment-approval.json",
        "records/source-gates/m2-radar-input-readiness-amendment-approval.json",
        "records/source-gates/m2-sentinel-recovery-002-approval.json",
        "records/source-gates/m2-sentinel-continuation-001-approval.json",
    ]:
        fail("project profile must expose the exact active DEM, orbit, radar-label, recovery-002, and continuation-001 amendments")
    if not (ROOT / "AGENTS.md").read_text(encoding="utf-8").strip():
        fail("AGENTS.md must contain controlling project instructions")
    if goal["status"] != "active":
        fail("long-term goal record must be active")
    workflow_text = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    if "actions/checkout@v6" not in workflow_text or "actions/setup-python@v7" not in workflow_text:
        fail("GitHub Actions must use the confirmed Node.js 24 action majors")
    if contract["project_profile_ref"] != "records/project-control-profile.json":
        fail("milestone must reference the project control profile")
    if contract["status"] != "complete":
        fail("M1 must be complete after exact source-manifest approval")
    if contract["authority"]["mode"] != "inherited":
        fail("completed M1 must preserve the exact user authority")
    if profile["authority"]["authority_ref"] != active_m2["authority"]["authority_ref"]:
        fail("profile and active M2 authority references must agree")
    expected_dem_amendment_binding = {
        "approval_ref": "records/source-gates/m2-dem-amendment-approval.json",
        "approval_sha256": sha256("records/source-gates/m2-dem-amendment-approval.json"),
        "proposal_ref": "contracts/milestone-002-dem-amendment-proposal.json",
        "proposal_sha256": "92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69",
        "review_bundle_sha256": "caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e",
        "license_document_sha256": "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd",
    }
    expected_orbit_amendment_binding = {
        "approval_ref": "records/source-gates/m2-orbit-amendment-approval.json",
        "approval_sha256": sha256("records/source-gates/m2-orbit-amendment-approval.json"),
        "proposal_ref": "contracts/milestone-002-orbit-amendment-proposal.json",
        "proposal_sha256": "b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292",
        "review_bundle_sha256": "ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1",
        "authorized_orbit_type": "AUX_RESORB",
        "authorized_source_count": 4,
        "precise_substitution_authorized": False,
    }
    expected_radar_label_amendment_binding = {
        "approval_ref": "records/source-gates/m2-radar-input-readiness-amendment-approval.json",
        "approval_sha256": sha256("records/source-gates/m2-radar-input-readiness-amendment-approval.json"),
        "proposal_ref": "contracts/milestone-002-radar-input-readiness-amendment-proposal.json",
        "proposal_sha256": "ebdcb763afd99ea23090c9bd83fd9e9cb6cb8dfbb2b5fed60edb80f1fa61c731",
        "review_bundle_sha256": "831df5d5aae06862514667ad861c815154085fa3c546039e60f517d38ee442ff",
        "amended_contract_ref": "config/qa/radar-input-readiness-contract-amendment-001.json",
        "amended_contract_sha256": sha256("config/qa/radar-input-readiness-contract-amendment-001.json"),
        "real_002_receipt_ref": "records/readiness/radar-input/m2-s1-input-readiness-real-002.json",
        "real_002_receipt_sha256": sha256("records/readiness/radar-input/m2-s1-input-readiness-real-002.json"),
        "reconciliation_ref": "records/surface-receipts/radar-input-readiness-amendment-real-002-reconciliation.json",
        "reconciliation_sha256": sha256("records/surface-receipts/radar-input-readiness-amendment-real-002-reconciliation.json"),
        "post_observation": True,
        "baseline_processing_released": False,
    }
    expected_recovery_002_amendment_binding = {
        "approval_ref": "records/source-gates/m2-sentinel-recovery-002-approval.json",
        "approval_sha256": sha256("records/source-gates/m2-sentinel-recovery-002-approval.json"),
        "proposal_ref": "contracts/milestone-002-sentinel-recovery-002-proposal.json",
        "proposal_sha256": "1ec77963e1171f60c2a4571306797077eb65206f5a4aacff6dd9cae33b0c0f6e",
        "review_bundle_sha256": "30d0f72c4c62b3c5450a08459a1c6024d442b8f718fa11f0fb650719437e9a30",
        "review_reconciliation_ref": "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json",
        "review_reconciliation_sha256": sha256("records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json"),
        "maximum_real_transfer_attempts": 1,
        "secret_transport": "anonymous_pipe_single_use_memory_only",
        "automatic_retry_authorized": False,
        "post_success_continuation_source_ids": ["M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010"],
        "pixel_processing_released": False,
    }
    expected_continuation_001_amendment_binding = {
        "approval_ref": "records/source-gates/m2-sentinel-continuation-001-approval.json",
        "approval_sha256": sha256("records/source-gates/m2-sentinel-continuation-001-approval.json"),
        "proposal_ref": "contracts/milestone-002-sentinel-continuation-001-proposal.json",
        "proposal_sha256": "d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1",
        "review_bundle_sha256": "382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b",
        "review_reconciliation_ref": "records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json",
        "review_reconciliation_sha256": sha256("records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json"),
        "source_ids_in_exact_order": ["M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010"],
        "maximum_real_attempts_per_source": 1,
        "stop_on_first_failure": True,
        "m1_src_004_request_permitted": False,
        "secret_transport": "anonymous_pipe_single_use_memory_only",
        "pixel_processing_released": False,
    }
    expected_amendments = [
        expected_dem_amendment_binding,
        expected_orbit_amendment_binding,
        expected_radar_label_amendment_binding,
        expected_recovery_002_amendment_binding,
        expected_continuation_001_amendment_binding,
    ]
    if profile["authority"].get("amendments") != expected_amendments:
        fail("profile authority does not bind the exact active amendments")
    if active_m2["authority"].get("amendments") != expected_amendments:
        fail("active M2 authority does not bind the exact active amendments")
    if active_m2.get("scope", {}).get("active_amendments") != [
        "records/source-gates/m2-dem-amendment-approval.json",
        "records/source-gates/m2-orbit-amendment-approval.json",
        "records/source-gates/m2-radar-input-readiness-amendment-approval.json",
        "records/source-gates/m2-sentinel-recovery-002-approval.json",
        "records/source-gates/m2-sentinel-continuation-001-approval.json",
    ]:
        fail("active M2 scope does not expose the five exact amendment approvals")
    profile_gates = {
        item.get("unit_id"): item
        for item in profile.get("gate_policy", {}).get("explicit_human_gates", [])
        if isinstance(item, dict)
    }
    for approved_unit in ("M2-CUSTODY-PREFLIGHT", "M2-ACQUIRE"):
        if profile_gates.get(approved_unit, {}).get("authority_ref") != "records/source-gates/m2-activation-approval.json":
            fail(f"project profile must bind {approved_unit} to the exact M2 activation approval")
    for approved_unit in ("M2-DEM-AMEND", "M2-DEM-PREFLIGHT", "M2-DEM-ACQUIRE"):
        if profile_gates.get(approved_unit, {}).get("authority_ref") != "records/source-gates/m2-dem-amendment-approval.json":
            fail(f"project profile must bind {approved_unit} to the exact DEM amendment approval")
    if profile_gates.get("M2-DEM-TERRAIN-RESULT-REVIEW", {}).get("authority_ref") != "reviews/m2-dem-terrain-result/review-contract.json":
        fail("project profile must expose the exact terrain-result human-review gate")
    sentinel_recovery_gate = profile_gates.get("M2-SENTINEL-RECOVERY", {})
    if (
        sentinel_recovery_gate.get("authority_ref") != "records/source-gates/m2-sentinel-recovery-002-approval.json"
        or "bounded recovery-002" not in sentinel_recovery_gate.get("reason", "")
    ):
        fail("project profile must bind Sentinel recovery-002 to the exact approval")
    continuation_gate = profile_gates.get("M2-SENTINEL-CONTINUATION-001-IMPLEMENTATION", {})
    if (
        continuation_gate.get("authority_ref") != "records/source-gates/m2-sentinel-continuation-001-approval.json"
        or "fixed-order one-attempt sequence" not in continuation_gate.get("reason", "")
    ):
        fail("project profile must bind Sentinel continuation-001 to the exact approval")
    if profile.get("control_surfaces", {}).get("proposed_amendments") != []:
        fail("project profile must not retain the approved recovery-002 proposal as pending")
    if profile_gates.get("M2-ORBIT-RECOVERY", {}).get("authority_ref") != "reviews/m2-orbit-recovery/review-contract.json":
        fail("project profile must expose the exact orbit recovery human-review gate")
    for approved_unit in ("M2-ORBIT-AMEND", "M2-ORBIT-PREFLIGHT", "M2-ORBIT-ACQUIRE", "M2-ORBIT-VERIFY", "M2-ORBIT-APPLY"):
        if profile_gates.get(approved_unit, {}).get("authority_ref") != "records/source-gates/m2-orbit-amendment-approval.json":
            fail(f"project profile must bind {approved_unit} to the exact orbit amendment approval")
    if profile_gates.get("M2-RADAR-INPUT-LABEL-AMEND", {}).get("authority_ref") != "records/source-gates/m2-radar-input-readiness-amendment-approval.json":
        fail("project profile must bind the exact radar input label amendment approval")
    if profile.get("parallel_checkpoints") != [
        {
            "checkpoint_id": expected_dem_checkpoint,
            "authority_ref": "records/source-gates/m2-dem-amendment-approval.json",
            "next_action": expected_dem_next_action,
        },
        {
            "checkpoint_id": "M2-DEM-TERRAIN-RESULT-REVIEW",
            "authority_ref": "reviews/m2-dem-terrain-result/review-contract.json",
            "next_action": "Review bundle SHA-256 834ad354fc134b2017afdd3b238c1a6271276e8b1a95776e434180c7283a26d5 and approve, revise, or defer the terrain-only result; approval releases no vertical, radar, or scientific action.",
        },
        {
            "checkpoint_id": "M2-ORBIT-ACQUISITION-REVIEW",
            "authority_ref": "reviews/m2-orbit-recovery/review-contract.json",
            "next_action": "Review M2 orbit recovery bundle SHA-256 df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b and proposal SHA-256 ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a; approve, revise, or defer one fresh M2-ORB-001 recovery that remains blocked until the full M2-VERIFY unit is complete.",
        },
    ]:
        fail("project profile DEM parallel checkpoint differs")
    if goal.get("active_amendments") != [
        "records/source-gates/m2-dem-amendment-approval.json",
        "records/source-gates/m2-orbit-amendment-approval.json",
        "records/source-gates/m2-radar-input-readiness-amendment-approval.json",
        "records/source-gates/m2-sentinel-recovery-002-approval.json",
        "records/source-gates/m2-sentinel-continuation-001-approval.json",
    ] or goal.get("parallel_checkpoints") != [expected_dem_checkpoint, "M2-DEM-TERRAIN-RESULT-REVIEW", "M2-ORBIT-ACQUISITION-REVIEW"]:
        fail("long-term goal does not expose the active amendments and pending checkpoints")
    prohibited = set(contract["scope"]["forbidden_work"])
    if "download full satellite products" not in prohibited:
        fail("full satellite-product acquisition must remain prohibited in M1")
    if profile["control_surfaces"].get("active_contract") != "contracts/milestone-002.json":
        fail("project profile must identify the active M2 contract")
    if profile["control_surfaces"].get("last_completed_contract") != "contracts/milestone-001.json":
        fail("project profile must identify M1 as the last completed contract")
    if profile["control_surfaces"].get("proposed_contract") is not None:
        fail("project profile must clear the proposed-contract pointer after activation")
    if profile["control_surfaces"].get("activated_from_contract") != "contracts/milestone-002-proposal.json":
        fail("project profile must retain the exact proposal lineage")
    if goal.get("active_milestone") != "contracts/milestone-002.json" or goal.get("proposed_milestone") is not None:
        fail("long-term goal must identify active M2 and no pending proposal")
    approval = json.loads((ROOT / "records/source-gates/aoi-approval.json").read_text(encoding="utf-8"))
    projected_aoi = json.loads((ROOT / "config/aoi/approved-study-areas-epsg32645.json").read_text(encoding="utf-8"))
    arcgis_receipt = json.loads((ROOT / "records/surface-receipts/m1-approved-aoi-arcgis-validation.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "records/source-manifest.json").read_text(encoding="utf-8"))
    manifest_bundle = json.loads((ROOT / "reviews/m1-manifest/review-bundle.json").read_text(encoding="utf-8"))
    manifest_contract = json.loads((ROOT / "reviews/m1-manifest/review-contract.json").read_text(encoding="utf-8"))
    manifest_response = json.loads((ROOT / "reviews/m1-manifest/blank-response.json").read_text(encoding="utf-8"))
    manifest_approval = json.loads((ROOT / "records/source-gates/source-manifest-approval.json").read_text(encoding="utf-8"))
    manifest_reconciliation = json.loads((ROOT / "records/source-gates/source-manifest-review-reconciliation.json").read_text(encoding="utf-8"))
    acquisition_plan = json.loads((ROOT / "records/acquisition-plan.json").read_text(encoding="utf-8"))
    m2_bundle = json.loads((ROOT / "reviews/m2-activation/review-bundle.json").read_text(encoding="utf-8"))
    m2_contract = json.loads((ROOT / "reviews/m2-activation/review-contract.json").read_text(encoding="utf-8"))
    m2_response = json.loads((ROOT / "reviews/m2-activation/blank-response.json").read_text(encoding="utf-8"))
    m2_surface_receipt = json.loads((ROOT / "records/surface-receipts/m2-activation-review.json").read_text(encoding="utf-8"))
    intake_contract = json.loads((ROOT / "contracts/m2-intake-candidate.json").read_text(encoding="utf-8"))
    active_intake = json.loads((ROOT / "contracts/m2-intake.json").read_text(encoding="utf-8"))
    initial_active_intake = json.loads((ROOT / "records/acquisition/active-intake-initial-snapshot.json").read_text(encoding="utf-8"))
    intake_dry_run = json.loads((ROOT / "records/acquisition/m2-intake-static-dry-run.json").read_text(encoding="utf-8"))
    m2_activation = json.loads((ROOT / "records/source-gates/m2-activation-approval.json").read_text(encoding="utf-8"))
    m2_reconciliation = json.loads((ROOT / "records/source-gates/m2-activation-review-reconciliation.json").read_text(encoding="utf-8"))
    m2_source_gate = json.loads((ROOT / "records/source-gates/m2-live-source-gate.json").read_text(encoding="utf-8"))
    m2_preflight = json.loads((ROOT / "records/acquisition/preflight.json").read_text(encoding="utf-8"))
    m2_source_gate_refresh = json.loads((ROOT / "records/source-gates/m2-live-source-gate-refresh.json").read_text(encoding="utf-8"))
    m2_terms_reconciliation = json.loads((ROOT / "records/source-gates/m2-terms-page-reconciliation.json").read_text(encoding="utf-8"))
    m2_preflight_refresh = json.loads((ROOT / "records/acquisition/preflight-refresh.json").read_text(encoding="utf-8"))
    sentinel_refresh_readiness = json.loads((ROOT / "records/acquisition/sentinel-preflight-refresh-readiness.json").read_text(encoding="utf-8"))
    custody_receipt = json.loads((ROOT / "records/acquisition/custody-initialization.json").read_text(encoding="utf-8"))
    transfer_readiness = json.loads((ROOT / "records/acquisition/transfer-runner-readiness.json").read_text(encoding="utf-8"))
    transfer_runner_correction = json.loads((ROOT / "records/acquisition/transfer-runner-attempt-id-correction.json").read_text(encoding="utf-8"))
    acquisition_progress_readiness = json.loads((ROOT / "records/acquisition/acquisition-progress-readiness.json").read_text(encoding="utf-8"))
    acquisition_progress_portability = json.loads((ROOT / "records/acquisition/acquisition-progress-windows-path-portability-correction.json").read_text(encoding="utf-8"))
    acquisition_checkpoint_readiness = json.loads((ROOT / "records/acquisition/acquisition-checkpoint-readiness.json").read_text(encoding="utf-8"))
    acquisition_checkpoint_portability = json.loads((ROOT / "records/acquisition/acquisition-checkpoint-portability-correction.json").read_text(encoding="utf-8"))
    pair_plan = json.loads((ROOT / "config/qa/candidate-pair-plan.json").read_text(encoding="utf-8"))
    offline_verification = json.loads((ROOT / "contracts/m2-offline-verification-candidate.json").read_text(encoding="utf-8"))
    active_offline_verification = json.loads((ROOT / "contracts/m2-offline-verification.json").read_text(encoding="utf-8"))
    readiness_input = json.loads((ROOT / "records/readiness/m2-readiness-audit-input.json").read_text(encoding="utf-8"))
    readiness_decision = json.loads((ROOT / "records/readiness/m2-readiness-decision.json").read_text(encoding="utf-8"))
    reproducibility = json.loads((ROOT / "records/surface-receipts/m1-control-reproducibility.json").read_text(encoding="utf-8"))
    evidence_schema = json.loads((ROOT / "config/arcgis/evidence-workspace-schema.json").read_text(encoding="utf-8"))
    evidence_workspace = json.loads((ROOT / "records/surface-receipts/arcgis-evidence-workspace.json").read_text(encoding="utf-8"))
    pixel_contract = json.loads((ROOT / "config/qa/pixel-readiness-contract.json").read_text(encoding="utf-8"))
    pixel_receipt = json.loads((ROOT / "records/surface-receipts/pixel-qa-synthetic-arcgis.json").read_text(encoding="utf-8"))
    aoi_reconciliation = json.loads((ROOT / "records/source-gates/aoi-review-reconciliation.json").read_text(encoding="utf-8"))
    units = {unit["id"]: unit for unit in contract["units"]}
    active_m2_units = {unit["id"]: unit for unit in active_m2["units"]}
    validate_review_bundle("reviews/m1-aoi/review-bundle.json", "reviews/m1-aoi/review-contract.json")
    validate_review_bundle("reviews/m1-manifest/review-bundle.json", "reviews/m1-manifest/review-contract.json")
    validate_review_bundle("reviews/m2-activation/review-bundle.json", "reviews/m2-activation/review-contract.json")
    validate_review_bundle("reviews/m2-dem-amendment/review-bundle.json", "reviews/m2-dem-amendment/review-contract.json")
    validate_review_bundle("reviews/m2-dem-vertical-datum/review-bundle.json", "reviews/m2-dem-vertical-datum/review-contract.json")
    validate_review_bundle(
        "reviews/m2-orbit-amendment/review-bundle.json",
        "reviews/m2-orbit-amendment/review-contract.json",
        verify_current_artifacts=False,
    )
    validate_review_bundle(
        "reviews/m2-sentinel-recovery/review-bundle.json",
        "reviews/m2-sentinel-recovery/review-contract.json",
        verify_current_artifacts=False,
    )
    validate_review_bundle(
        "reviews/m2-sentinel-recovery-002/review-bundle.json",
        "reviews/m2-sentinel-recovery-002/review-contract.json",
        verify_current_artifacts=False,
    )
    validate_review_bundle(
        "reviews/m2-sentinel-continuation-001/review-bundle.json",
        "reviews/m2-sentinel-continuation-001/review-contract.json",
        verify_current_artifacts=False,
    )

    expected_recovery_proposal_sha = "7b8b5e83265b37962f879ca7dad85ab5f5c04ceb28ee0f15fa774a79df7fd013"
    expected_recovery_bundle_sha = "dffa194cc91636a35b5f55af6ece32bb6eb90d77b65ea3d9865413f912d146e7"
    expected_recovery_surface_sha = "9d643d42aaa9d279cfa5690363ade3e3f065411231239ae51bf77a4b4bc30307"
    failed_attempt_ref = "records/acquisition/attempts/m1-src-004-20260904t043930z-ac125c11.json"
    failed_attempt_sha = "8cbaf911e5a3329c5aa00a7288e237fa71987a2d4f03cea8c630c7dd28b9e7e9"
    if (
        sentinel_recovery_proposal.get("status") != "proposed_not_authorized"
        or sha256("contracts/milestone-002-sentinel-recovery-proposal.json") != expected_recovery_proposal_sha
        or sentinel_recovery_proposal.get("trigger") != {
            "checkpoint": "M2-ACQUISITION-REVIEW",
            "reconciliation_ref": "records/acquisition/sentinel-acquisition-reconciliation-001.json",
            "failed_source_id": "M1-SRC-004",
            "failed_attempt_id": "m1-src-004-20260904t043930z-ac125c11",
            "failure_code": "transferred_size_mismatch",
            "expected_size_bytes": 1732332897,
            "partial_bytes_preserved": 561593598,
            "partial_sha256": "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66",
        }
    ):
        fail("M2 Sentinel recovery proposal identity or retained-failure trigger differs")
    recovery = sentinel_recovery_proposal.get("proposed_recovery", {})
    if (
        recovery.get("mode") != "fresh_full_restart_distinct_attempt"
        or recovery.get("source_id") != "M1-SRC-004"
        or recovery.get("restart_offset_bytes") != 0
        or recovery.get("resume_partial") is not False
        or recovery.get("delete_or_modify_failed_partial") is not False
        or recovery.get("reuse_failed_staging_path") is not False
        or recovery.get("required_new_asset_or_attempt_namespace") != "m1-src-004-recovery-001"
        or recovery.get("failure_policy") != "Any recovery failure is terminal for that recovery identity and requires another explicit review; no automatic retry is authorized."
    ):
        fail("M2 Sentinel recovery proposal weakens fresh-attempt or retained-evidence controls")
    if sentinel_recovery_proposal.get("human_gate") != {
        "review_required": True,
        "item_id": "M2-SENTINEL-RECOVERY-001",
        "allowed_decisions": ["approve", "revise", "defer"],
        "required_attestation": True,
    }:
        fail("M2 Sentinel recovery proposal human gate differs")

    if (
        sentinel_acquisition_reconciliation.get("status") != "review_required_retained_failure"
        or sentinel_acquisition_reconciliation.get("state_counts") != {"authorized": 4, "failed": 1, "promoted": 3}
        or sentinel_acquisition_reconciliation.get("bindings", {}).get("active_intake_sha256") != "734455b7c0e772aa22253a81f944dc685e4c73cf73490ca2f821d12d7e2b5ca0"
        or sentinel_acquisition_reconciliation.get("retained_failure", {}).get("transfer_receipt_ref") != failed_attempt_ref
        or sentinel_acquisition_reconciliation.get("retained_failure", {}).get("transfer_receipt_sha256") != failed_attempt_sha
        or sentinel_acquisition_reconciliation.get("retained_failure", {}).get("partial_sha256") != "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
        or sentinel_acquisition_reconciliation.get("retained_failure", {}).get("resume_evidence_sufficient") is not False
        or sentinel_acquisition_reconciliation.get("retained_failure", {}).get("retry_automatically_authorized") is not False
        or sentinel_acquisition_reconciliation.get("validation", {}).get("pixel_usability_established") is not False
        or sentinel_acquisition_reconciliation.get("validation", {}).get("scientific_fitness_established") is not False
    ):
        fail("M2 Sentinel acquisition reconciliation differs")
    successful_reconciliation = sentinel_acquisition_reconciliation.get("successful_products", [])
    if [item.get("source_id") for item in successful_reconciliation] != ["M1-SRC-001", "M1-SRC-002", "M1-SRC-003"]:
        fail("M2 Sentinel acquisition reconciliation successful-product order differs")
    for item in successful_reconciliation:
        if (
            item.get("transfer_receipt_sha256") != sha256(item.get("transfer_receipt_ref", ""))
            or item.get("container_receipt_sha256") != sha256(item.get("container_receipt_ref", ""))
            or item.get("provider_md5_verified") is not True
            or item.get("container_status") != "pass_container_only"
            or item.get("pixel_usability_established") is not False
        ):
            fail(f"M2 Sentinel acquisition reconciliation success binding differs for {item.get('source_id')}")
    if sha256(failed_attempt_ref) != failed_attempt_sha:
        fail("M2 Sentinel retained failure receipt identity differs")

    if (
        sentinel_recovery_surface.get("status") != "pass_blank_review_surface"
        or sentinel_recovery_surface.get("artifact", {}).get("sha256") != expected_recovery_surface_sha
        or sentinel_recovery_surface.get("artifact", {}).get("sha256") != sha256("docs/assets/m2-sentinel-recovery-review.png")
        or sentinel_recovery_surface.get("bindings", {}).get("proposal_sha256") != expected_recovery_proposal_sha
        or sentinel_recovery_surface.get("bindings", {}).get("render_script_sha256") != sha256("scripts/render_m2_sentinel_recovery_review.py")
        or sentinel_recovery_surface.get("validation", {}).get("blank_state_verified") is not True
        or sentinel_recovery_surface.get("validation", {}).get("human_decision_count") != 0
    ):
        fail("M2 Sentinel recovery review surface or blank-state receipt differs")
    expected_recovery_candidate = "M2-SENTINEL-RECOVERY-PROPOSAL-SHA256:" + expected_recovery_proposal_sha
    if (
        sentinel_recovery_bundle.get("bundle_id") != "m2-sentinel-recovery-review-bundle-001"
        or sentinel_recovery_bundle.get("review_id") != "m2-sentinel-recovery-review-001"
        or sentinel_recovery_bundle.get("candidate_identity") != expected_recovery_candidate
        or sha256("reviews/m2-sentinel-recovery/review-bundle.json") != expected_recovery_bundle_sha
    ):
        fail("M2 Sentinel recovery review bundle identity differs")
    recovery_authority = sentinel_recovery_contract.get("workflow_authority", {})
    if (
        sentinel_recovery_contract.get("review_bundle", {}).get("manifest_sha256") != expected_recovery_bundle_sha
        or sentinel_recovery_contract.get("review_bundle", {}).get("candidate_identity") != expected_recovery_candidate
        or sentinel_recovery_contract.get("review_bundle", {}).get("rendered_surface_verified") is not True
        or sentinel_recovery_contract.get("allowed_decisions") != ["approve", "revise", "defer"]
        or sentinel_recovery_contract.get("required_attestation") is not True
        or recovery_authority.get("review_required") is not True
        or recovery_authority.get("lock_authorized") is not True
        or recovery_authority.get("reconcile_authorized") is not True
        or "data_acquisition" in recovery_authority.get("authorized_action_classes", [])
        or sentinel_recovery_contract.get("items") != [{"item_id": "M2-SENTINEL-RECOVERY-001", "evidence_sha256": expected_recovery_bundle_sha}]
    ):
        fail("M2 Sentinel recovery review contract authority or exact-bundle binding differs")
    if sentinel_recovery_blank != {
        "response_schema_version": "nepal-m2-sentinel-recovery-response-v1",
        "review_id": "m2-sentinel-recovery-review-001",
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{
            "item_id": "M2-SENTINEL-RECOVERY-001",
            "evidence_sha256": expected_recovery_bundle_sha,
            "decision": None,
            "notes": "",
        }],
    }:
        fail("M2 Sentinel recovery blank response differs or contains a human decision")

    expected_recovery_002_proposal_sha = "1ec77963e1171f60c2a4571306797077eb65206f5a4aacff6dd9cae33b0c0f6e"
    expected_recovery_002_bundle_sha = "30d0f72c4c62b3c5450a08459a1c6024d442b8f718fa11f0fb650719437e9a30"
    expected_recovery_002_surface_sha = "3561bc50e90adaba31248c1ddbc02d83669697fb6ad64f2883fb7a740dbdbe5a"
    recovery_002 = sentinel_recovery_002_proposal.get("proposed_recovery", {})
    recovery_002_boundary = recovery_002.get("broker_worker_boundary", {})
    recovery_002_trigger = sentinel_recovery_002_proposal.get("trigger", {})
    if (
        sentinel_recovery_002_proposal.get("status") != "proposed_not_authorized"
        or sha256("contracts/milestone-002-sentinel-recovery-002-proposal.json") != expected_recovery_002_proposal_sha
        or recovery_002_trigger.get("source_id") != "M1-SRC-004"
        or recovery_002_trigger.get("destination_promoted") is not False
        or recovery_002_trigger.get("automatic_retry_authorized") is not False
        or recovery_002_trigger.get("original_failed_attempt", {}).get("partial_sha256") != "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
        or recovery_002_trigger.get("approved_recovery_failed_attempt", {}).get("partial_sha256") != "c2d3a878f98615ddaa5e0bf21df5eb5f65c591719cb26b5f43b361aa4eac4cac"
        or recovery_002_trigger.get("approved_recovery_failed_attempt", {}).get("failure_cause_established") is not False
        or recovery_002_trigger.get("approved_recovery_failed_attempt", {}).get("approved_attempt_consumed") is not True
        or recovery_002.get("mode") != "fresh_full_restart_detached_supervised_worker"
        or recovery_002.get("restart_offset_bytes") != 0
        or recovery_002.get("resume_any_partial") is not False
        or recovery_002.get("delete_or_modify_any_partial") is not False
        or recovery_002.get("reuse_any_prior_staging_path") is not False
        or recovery_002.get("required_new_asset_or_attempt_namespace") != "m1-src-004-recovery-002"
        or recovery_002.get("required_new_intake_namespace") != "nepal-m2-sentinel-recovery-002"
        or recovery_002.get("maximum_real_transfer_attempts") != 1
        or recovery_002_boundary.get("transfer_owner") != "separate_detached_supervisor_process"
        or recovery_002_boundary.get("console_exit_must_not_end_worker") is not True
        or recovery_002_boundary.get("worker_must_close_secret_channel_after_read") is not True
        or recovery_002_boundary.get("secret_forbidden_locations") != [
            "command_line", "environment_variable", "disk_file", "repository_record",
            "stdout_or_stderr", "event_or_heartbeat_record",
        ]
    ):
        fail("M2 Sentinel recovery-002 proposal weakens retained-evidence, one-attempt, or secret-safe detached-worker controls")
    if sentinel_recovery_002_proposal.get("human_gate") != {
        "review_required": True,
        "item_id": "M2-SENTINEL-RECOVERY-002",
        "allowed_decisions": ["approve", "revise", "defer"],
        "required_attestation": True,
    }:
        fail("M2 Sentinel recovery-002 proposal human gate differs")
    if (
        sentinel_recovery_002_surface.get("status") != "pass_blank_review_surface"
        or sentinel_recovery_002_surface.get("artifact", {}).get("sha256") != expected_recovery_002_surface_sha
        or sentinel_recovery_002_surface.get("artifact", {}).get("sha256") != sha256("docs/assets/m2-sentinel-recovery-002-review.png")
        or sentinel_recovery_002_surface.get("bindings", {}).get("proposal_sha256") != expected_recovery_002_proposal_sha
        or sentinel_recovery_002_surface.get("bindings", {}).get("render_script_sha256") != sha256("scripts/render_m2_sentinel_recovery_002_review.py")
        or sentinel_recovery_002_surface.get("validation", {}).get("blank_state_verified") is not True
        or sentinel_recovery_002_surface.get("validation", {}).get("human_decision_count") != 0
    ):
        fail("M2 Sentinel recovery-002 review surface or blank-state receipt differs")
    expected_recovery_002_candidate = "M2-SENTINEL-RECOVERY-002-PROPOSAL-SHA256:" + expected_recovery_002_proposal_sha
    if (
        sentinel_recovery_002_bundle.get("bundle_id") != "m2-sentinel-recovery-002-review-bundle-001"
        or sentinel_recovery_002_bundle.get("review_id") != "m2-sentinel-recovery-002-review-001"
        or sentinel_recovery_002_bundle.get("candidate_identity") != expected_recovery_002_candidate
        or sha256("reviews/m2-sentinel-recovery-002/review-bundle.json") != expected_recovery_002_bundle_sha
    ):
        fail("M2 Sentinel recovery-002 review bundle identity differs")
    recovery_002_authority = sentinel_recovery_002_contract.get("workflow_authority", {})
    if (
        sentinel_recovery_002_contract.get("review_bundle", {}).get("manifest_sha256") != expected_recovery_002_bundle_sha
        or sentinel_recovery_002_contract.get("review_bundle", {}).get("candidate_identity") != expected_recovery_002_candidate
        or sentinel_recovery_002_contract.get("review_bundle", {}).get("rendered_surface_verified") is not True
        or sentinel_recovery_002_contract.get("allowed_decisions") != ["approve", "revise", "defer"]
        or sentinel_recovery_002_contract.get("required_attestation") is not True
        or recovery_002_authority.get("review_required") is not True
        or recovery_002_authority.get("lock_authorized") is not True
        or recovery_002_authority.get("reconcile_authorized") is not True
        or "data_acquisition" in recovery_002_authority.get("authorized_action_classes", [])
        or "credential_or_identity" in recovery_002_authority.get("authorized_action_classes", [])
        or sentinel_recovery_002_contract.get("items") != [{"item_id": "M2-SENTINEL-RECOVERY-002", "evidence_sha256": expected_recovery_002_bundle_sha}]
    ):
        fail("M2 Sentinel recovery-002 review contract authority or exact-bundle binding differs")
    if sentinel_recovery_002_blank != {
        "response_schema_version": "nepal-m2-sentinel-recovery-002-response-v1",
        "review_id": "m2-sentinel-recovery-002-review-001",
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{
            "item_id": "M2-SENTINEL-RECOVERY-002",
            "evidence_sha256": expected_recovery_002_bundle_sha,
            "decision": None,
            "notes": "",
        }],
    }:
        fail("M2 Sentinel recovery-002 blank response differs or contains a human decision")

    if (
        sentinel_recovery_approval.get("status") != "approved_exact_bounded_fresh_byte_zero_recovery"
        or sentinel_recovery_approval.get("review_bundle_manifest_sha256") != expected_recovery_bundle_sha
        or sentinel_recovery_approval.get("recovery_proposal_sha256") != expected_recovery_proposal_sha
        or sentinel_recovery_approval.get("human_decision_count") != 1
        or sentinel_recovery_approval.get("recovery_identity", {}).get("source_id") != "M1-SRC-004"
    ):
        fail("M2 Sentinel recovery approval identity or scope differs")
    if (
        sentinel_recovery_review_reconciliation.get("status") != "reconciled_exact_human_response"
        or sentinel_recovery_review_reconciliation.get("response_sha256") != sentinel_recovery_approval.get("locked_response_sha256")
        or sentinel_recovery_review_reconciliation.get("human_decision_count") != 1
        or sentinel_recovery_review_reconciliation.get("decision_counts", {}).get("approve") != 1
    ):
        fail("M2 Sentinel recovery completed review reconciliation differs")
    if (
        sentinel_recovery_publication_gate.get("status") != "pass_public_controls_verified_before_real_recovery"
        or sentinel_recovery_publication_gate.get("github_actions", {}).get("run_id") != 33912826977
        or sentinel_recovery_publication_gate.get("github_actions", {}).get("conclusion") != "success"
        or sentinel_recovery_publication_gate.get("assertions", {}).get("real_recovery_started") is not False
    ):
        fail("M2 Sentinel recovery publication gate differs")
    if (
        sentinel_recovery_activation.get("status") != "pass_exact_recovery_authorized_publication_gate_pending"
        or sentinel_recovery_activation.get("bindings", {}).get("approval_sha256") != sha256("records/source-gates/m2-sentinel-recovery-approval.json")
        or sentinel_recovery_activation.get("assertions", {}).get("automatic_second_recovery_authorized") is not False
    ):
        fail("M2 Sentinel recovery activation evidence differs")

    recovery_assets = sentinel_recovery_active_contract.get("assets", [])
    recovery_attempts = recovery_assets[0].get("attempts", []) if len(recovery_assets) == 1 else []
    recovery_attempt_id = "m1-src-004-recovery-001-20260904t201220z-e4388c64"
    recovery_failure_code = "external_process_terminated_before_terminal_event"
    recovery_partial_sha256 = "c2d3a878f98615ddaa5e0bf21df5eb5f65c591719cb26b5f43b361aa4eac4cac"
    if (
        sentinel_recovery_active_contract.get("intake_id") != "nepal-m2-sentinel-recovery-001"
        or sentinel_recovery_active_contract.get("extensions", {}).get("status") != "terminal_recovery_failure_new_review_required"
        or len(recovery_assets) != 1
        or recovery_assets[0].get("asset_id") != "m1-src-004-recovery-001"
        or recovery_assets[0].get("state") != "failed"
        or recovery_assets[0].get("failure", {}).get("code") != recovery_failure_code
        or len(recovery_attempts) != 1
        or recovery_attempts[0].get("attempt_id") != recovery_attempt_id
        or recovery_attempts[0].get("outcome") != "failed"
        or not recovery_attempts[0].get("completed_at")
        or recovery_attempts[0].get("extensions", {}).get("partial_size_bytes") != 1333788672
        or recovery_attempts[0].get("extensions", {}).get("partial_sha256") != recovery_partial_sha256
    ):
        fail("M2 Sentinel recovery active contract is not the exact terminal failed attempt")
    if (
        sentinel_recovery_attempt.get("event") != "recovery_transfer_failed"
        or sentinel_recovery_attempt.get("attempt_id") != recovery_attempt_id
        or sentinel_recovery_attempt.get("failure_code") != recovery_failure_code
        or sentinel_recovery_attempt.get("failure_cause_established") is not False
        or sentinel_recovery_attempt.get("partial_bytes_preserved") != 1333788672
        or sentinel_recovery_attempt.get("partial_sha256") != recovery_partial_sha256
        or sentinel_recovery_attempt.get("original_failed_partial_sha256") != "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
        or sentinel_recovery_attempt.get("destination_exists") is not False
        or sentinel_recovery_attempt.get("credential_value_recorded") is not False
        or sentinel_recovery_attempt.get("retry_automatically_authorized") is not False
    ):
        fail("M2 Sentinel recovery terminal failure receipt differs")
    recovery_receipt_ref = "records/acquisition/recovery-attempts/" + recovery_attempt_id + ".json"
    if (
        sentinel_recovery_interruption.get("status") != "reconciled_terminal_failure_no_retry_authorized"
        or sentinel_recovery_interruption.get("attempt_id") != recovery_attempt_id
        or sentinel_recovery_interruption.get("failure_code") != recovery_failure_code
        or sentinel_recovery_interruption.get("failure_cause_established") is not False
        or sentinel_recovery_interruption.get("bindings", {}).get("recovery_contract_sha256_after_reconciliation") != sha256("contracts/m2-sentinel-recovery.json")
        or sentinel_recovery_interruption.get("bindings", {}).get("public_receipt_ref") != recovery_receipt_ref
        or sentinel_recovery_interruption.get("bindings", {}).get("public_receipt_sha256") != sha256(recovery_receipt_ref)
        or sentinel_recovery_interruption.get("authority_and_disposition", {}).get("approved_attempt_consumed") is not True
        or sentinel_recovery_interruption.get("authority_and_disposition", {}).get("automatic_retry_authorized") is not False
        or sentinel_recovery_interruption.get("authority_and_disposition", {}).get("further_sentinel_transfer_authorized_now") is not False
    ):
        fail("M2 Sentinel recovery interruption reconciliation differs")

    validate_review_bundle(
        "reviews/m2-orbit-recovery/review-bundle.json",
        "reviews/m2-orbit-recovery/review-contract.json",
        verify_current_artifacts=False,
    )
    expected_orbit_recovery_proposal_sha = "ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a"
    expected_orbit_recovery_bundle_sha = "df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b"
    expected_orbit_recovery_surface_sha = "63dc1df8aff522a9ffdf8a77f24b600d4efcfaf0342aed8ec914d5372821edd8"
    if (
        orbit_recovery_proposal.get("status") != "proposed_not_authorized"
        or sha256("contracts/milestone-002-orbit-recovery-proposal.json") != expected_orbit_recovery_proposal_sha
        or orbit_recovery_proposal.get("trigger", {}).get("checkpoint") != "M2-ORBIT-ACQUISITION-REVIEW"
        or orbit_recovery_proposal.get("trigger", {}).get("failed_source_id") != "M2-ORB-001"
        or orbit_recovery_proposal.get("trigger", {}).get("failed_attempt_id") != "m2-orb-001-20260904t050937z-8ed21d05"
        or orbit_recovery_proposal.get("trigger", {}).get("failure_code") != "orbit_redirect_or_http_status_rejected"
        or orbit_recovery_proposal.get("trigger", {}).get("partial_bytes_preserved") != 0
        or orbit_recovery_proposal.get("current_verified_state", {}).get("orbit_state_counts") != {"authorized": 3, "failed": 1, "promoted": 0}
        or orbit_recovery_proposal.get("current_verified_state", {}).get("sentinel_state_counts") != {"authorized": 4, "failed": 1, "promoted": 3}
        or orbit_recovery_proposal.get("current_verified_state", {}).get("m2_verify_status") != "blocked_retained_failure_review"
        or orbit_recovery_proposal.get("current_verified_state", {}).get("orbit_payload_bytes_in_custody") != 0
    ):
        fail("M2 orbit recovery proposal trigger or current-state boundary differs")
    orbit_recovery = orbit_recovery_proposal.get("proposed_recovery", {})
    if (
        orbit_recovery.get("mode") != "fresh_full_restart_distinct_attempt"
        or orbit_recovery.get("source_id") != "M2-ORB-001"
        or orbit_recovery.get("restart_offset_bytes") != 0
        or orbit_recovery.get("resume_partial") is not False
        or orbit_recovery.get("delete_or_modify_failed_events") is not False
        or orbit_recovery.get("reuse_failed_attempt_id") is not False
        or orbit_recovery.get("required_new_attempt_namespace") != "m2-orb-001-recovery-001"
        or not any("full M2-VERIFY unit is complete" in item for item in orbit_recovery.get("prerequisites", []))
        or orbit_recovery.get("failure_policy") != "Any recovery failure is terminal for the new recovery identity and requires another explicit review; no automatic retry is authorized."
        or orbit_recovery_proposal.get("human_gate") != {
            "review_required": True,
            "item_id": "M2-ORBIT-RECOVERY-001",
            "allowed_decisions": ["approve", "revise", "defer"],
            "required_attestation": True,
        }
    ):
        fail("M2 orbit recovery proposal weakens dependency, fresh-attempt, or retained-evidence controls")

    if (
        materialization_receipt.get("status") != "pass_materialization_only"
        or materialization_receipt.get("source_id") != "M1-SRC-001"
        or materialization_receipt.get("attempt_id") != "fixture-must-not-run"
        or materialization_receipt.get("file_count") != 26
        or materialization_receipt.get("total_extracted_bytes") != 1732324248
        or materialization_receipt.get("raster_readability_established") is not False
        or materialization_receipt.get("pixel_usability_established") is not False
        or materialization_receipt.get("scientific_admission_authorized") is not False
    ):
        fail("retained test-induced materialization receipt differs or overclaims")
    if (
        materialization_boundary_reconciliation.get("status") != "retained_pass_materialization_only_unintended_test_execution"
        or materialization_boundary_reconciliation.get("trigger", {}).get("corrected_test_sha256") != sha256("tests/test_m2_materialization.py")
        or materialization_boundary_reconciliation.get("outcome", {}).get("materialization_receipt_sha256") != sha256("records/acquisition/materialization/m1-src-001-fixture-must-not-run.json")
        or materialization_boundary_reconciliation.get("outcome", {}).get("full_manifest_file_hash_verification") != "pass"
        or materialization_boundary_reconciliation.get("outcome", {}).get("verified_file_count") != 26
        or materialization_boundary_reconciliation.get("disposition", {}).get("preserve_external_attempt") is not True
        or materialization_boundary_reconciliation.get("disposition", {}).get("repeat_automatically_authorized") is not False
        or materialization_boundary_reconciliation.get("disposition", {}).get("next_processing_released") is not False
    ):
        fail("test-induced materialization reconciliation differs")

    materialization_records = sentinel_materialization_reconciliation.get("materializations", [])
    materialization_expected = {
        "M1-SRC-001": {
            "attempt_id": "fixture-must-not-run",
            "exact_product_id": "S1D_IW_GRDH_1SDV_20260816T122116_20260816T122141_004151_007980_B057.SAFE",
            "container_receipt_ref": "records/acquisition/container-verification/m1-src-001-m1-src-001-20260904t041621z-fe412d8d.json",
            "archive_sha256": "55b19242652e79887f00bb312d7fab1d7f8879f4e9eb996ca15be1268de1e79a",
            "archive_size_bytes": 1732333216,
        },
        "M1-SRC-002": {
            "attempt_id": "m1-src-002-materialization-001",
            "exact_product_id": "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB.SAFE",
            "container_receipt_ref": "records/acquisition/container-verification/m1-src-002-m1-src-002-20260904t042408z-b31b162b.json",
            "archive_sha256": "4df9ecdd0ad7f562bdf743b70b9061b9af3885dcbdcaf7f45c1875f2cd838790",
            "archive_size_bytes": 1732874277,
        },
        "M1-SRC-003": {
            "attempt_id": "m1-src-003-materialization-001",
            "exact_product_id": "S1D_IW_GRDH_1SDV_20260819T001036_20260819T001101_004187_007ABD_DC16.SAFE",
            "container_receipt_ref": "records/acquisition/container-verification/m1-src-003-m1-src-003-20260904t043000z-d1b78c08.json",
            "archive_sha256": "fa9250c3433065c7f3045352bee938b31d140771320e875f1088156094eedf01",
            "archive_size_bytes": 1718369620,
        },
    }
    if (
        sentinel_materialization_reconciliation.get("status") != "pass_three_materialized_all_file_hashes_verified_mixed_provenance"
        or sentinel_materialization_reconciliation.get("authority", {}).get("contract_sha256") != sha256("contracts/m2-materialization.json")
        or sentinel_materialization_reconciliation.get("authority", {}).get("authority_sha256") != sha256("records/source-gates/m2-activation-approval.json")
        or [item.get("source_id") for item in materialization_records] != ["M1-SRC-001", "M1-SRC-002", "M1-SRC-003"]
        or [item.get("provenance") for item in materialization_records] != [
            "retained_unintended_test_execution",
            "planned_authorized_offline_materialization",
            "planned_authorized_offline_materialization",
        ]
        or sentinel_materialization_reconciliation.get("summary") != {
            "materialized_source_count": 3,
            "planned_materialization_count": 2,
            "retained_unintended_test_materialization_count": 1,
            "verified_file_count": 78,
            "total_extracted_bytes": 5183550209,
            "promoted_container_verified_sources_not_materialized": [],
            "failed_or_unattempted_sources_not_materialized": [
                "M1-SRC-004", "M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010"
            ],
        }
        or sentinel_materialization_reconciliation.get("activity") != {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "source_archives_mutated": False,
        }
        or sentinel_materialization_reconciliation.get("claim_boundary", {}).get("materialization_only") is not True
        or any(sentinel_materialization_reconciliation.get("claim_boundary", {}).get(key) is not False for key in (
            "raster_readability_established",
            "pixel_usability_established",
            "baseline_established",
            "change_established",
            "scientific_admission_authorized",
            "current_checkpoint_changed",
            "recovery_authority_created",
        ))
    ):
        fail("three-source Sentinel materialization reconciliation differs or overclaims")
    for item in materialization_records:
        source_id = item["source_id"]
        receipt = sentinel_materialization_receipts[source_id]
        expected = materialization_expected[source_id]
        bindings = receipt.get("bindings", {})
        if (
            item.get("receipt_sha256") != sha256(item.get("receipt_ref", ""))
            or item.get("receipt_sha256") != hashlib.sha256((ROOT / item["receipt_ref"]).read_bytes()).hexdigest()
            or item.get("external_manifest_sha256") != receipt.get("bindings", {}).get("external_manifest_sha256")
            or item.get("file_count") != receipt.get("file_count")
            or item.get("total_extracted_bytes") != receipt.get("total_extracted_bytes")
            or item.get("independent_file_hash_verification") != "pass"
            or receipt.get("status") != "pass_materialization_only"
            or receipt.get("source_id") != source_id
            or receipt.get("attempt_id") != expected["attempt_id"]
            or receipt.get("exact_product_id") != expected["exact_product_id"]
            or bindings.get("contract_ref") != "contracts/m2-materialization.json"
            or bindings.get("contract_sha256") != sha256("contracts/m2-materialization.json")
            or bindings.get("active_intake_ref") != "contracts/m2-intake.json"
            or bindings.get("container_receipt_ref") != expected["container_receipt_ref"]
            or bindings.get("container_receipt_sha256") != sha256(expected["container_receipt_ref"])
            or bindings.get("archive_sha256") != expected["archive_sha256"]
            or bindings.get("archive_size_bytes") != expected["archive_size_bytes"]
            or receipt.get("activity", {}).get("network_requests_performed") is not False
            or receipt.get("activity", {}).get("authentication_performed") is not False
            or receipt.get("activity", {}).get("source_archive_mutated") is not False
            or receipt.get("raster_readability_established") is not False
            or receipt.get("pixel_usability_established") is not False
            or receipt.get("baseline_established") is not False
            or receipt.get("change_established") is not False
            or receipt.get("scientific_admission_authorized") is not False
        ):
            fail(f"Sentinel materialization receipt or reconciliation differs for {source_id}")

    if (
        orbit_failed_attempt.get("event") != "orbit_transfer_failed"
        or orbit_failed_attempt.get("source_id") != "M2-ORB-001"
        or orbit_failed_attempt.get("attempt_id") != "m2-orb-001-20260904t050937z-8ed21d05"
        or orbit_failed_attempt.get("failure_code") != "orbit_redirect_or_http_status_rejected"
        or orbit_failed_attempt.get("partial_bytes_preserved") != 0
        or orbit_failed_attempt.get("credential_value_recorded") is not False
        or orbit_failed_attempt.get("retry_automatically_authorized") is not False
    ):
        fail("retained test-induced orbit attempt differs")
    if (
        orbit_boundary_reconciliation.get("status") != "review_required_retained_zero_byte_failed_test_execution"
        or orbit_boundary_reconciliation.get("trigger", {}).get("corrected_test_sha256") != sha256("tests/test_m2_orbit_io.py")
        or orbit_boundary_reconciliation.get("outcome", {}).get("repository_receipt_sha256") != sha256("records/acquisition/orbit-attempts/m2-orb-001-20260904t050937z-8ed21d05.json")
        or orbit_boundary_reconciliation.get("outcome", {}).get("partial_bytes_preserved") != 0
        or orbit_boundary_reconciliation.get("outcome", {}).get("staging_payload_exists") is not False
        or orbit_boundary_reconciliation.get("outcome", {}).get("destination_payload_exists") is not False
        or orbit_boundary_reconciliation.get("authority_assessment", {}).get("active_milestone_dependency_satisfied") is not False
        or orbit_boundary_reconciliation.get("disposition", {}).get("retry_automatically_authorized") is not False
        or orbit_boundary_reconciliation.get("assertions", {}).get("orbit_payload_bytes_received") != 0
    ):
        fail("test-induced orbit attempt reconciliation differs")
    if (
        orbit_boundary_correction.get("status") != "pass_full_m2_verify_guard_before_catalogue_token_or_mutation"
        or orbit_boundary_correction.get("finding_sha256") != sha256("records/acquisition/orbit-test-boundary-reconciliation-001.json")
        or orbit_boundary_correction.get("correction", {}).get("runner_sha256") != sha256("scripts/acquire_m2_orbit_file.py")
        or orbit_boundary_correction.get("correction", {}).get("test_refs", {}).get("tests/test_m2_orbit_io.py") != sha256("tests/test_m2_orbit_io.py")
        or orbit_boundary_correction.get("validation", {}).get("focused_orbit_test_count") != 29
        or orbit_boundary_correction.get("validation", {}).get("focused_orbit_tests") != "pass"
        or orbit_boundary_correction.get("validation", {}).get("production_guard_probe_stop_code") != "sentinel_verification_unit_not_complete"
        or orbit_boundary_correction.get("assertions", {}).get("runner_requires_full_m2_verify_dependency") is not True
        or orbit_boundary_correction.get("assertions", {}).get("network_requests_performed_by_correction_or_guard_probe") is not False
        or orbit_boundary_correction.get("assertions", {}).get("orbit_payload_bytes_requested_by_correction_or_guard_probe") != 0
    ):
        fail("orbit runner production-boundary correction differs")

    if (
        orbit_recovery_surface.get("status") != "pass_blank_review_surface"
        or orbit_recovery_surface.get("artifact", {}).get("sha256") != expected_orbit_recovery_surface_sha
        or orbit_recovery_surface.get("artifact", {}).get("sha256") != sha256("docs/assets/m2-orbit-recovery-review.png")
        or orbit_recovery_surface.get("bindings", {}).get("proposal_sha256") != expected_orbit_recovery_proposal_sha
        or orbit_recovery_surface.get("bindings", {}).get("render_script_sha256") != sha256("scripts/render_m2_orbit_recovery_review.py")
        or orbit_recovery_surface.get("validation", {}).get("blank_state_verified") is not True
        or orbit_recovery_surface.get("validation", {}).get("human_decision_count") != 0
    ):
        fail("M2 orbit recovery review surface or blank-state receipt differs")
    expected_orbit_recovery_candidate = "M2-ORBIT-RECOVERY-PROPOSAL-SHA256:" + expected_orbit_recovery_proposal_sha
    if (
        orbit_recovery_bundle.get("bundle_id") != "m2-orbit-recovery-review-bundle-001"
        or orbit_recovery_bundle.get("review_id") != "m2-orbit-recovery-review-001"
        or orbit_recovery_bundle.get("candidate_identity") != expected_orbit_recovery_candidate
        or sha256("reviews/m2-orbit-recovery/review-bundle.json") != expected_orbit_recovery_bundle_sha
        or orbit_recovery_contract.get("review_bundle", {}).get("manifest_sha256") != expected_orbit_recovery_bundle_sha
        or orbit_recovery_contract.get("review_bundle", {}).get("candidate_identity") != expected_orbit_recovery_candidate
        or orbit_recovery_contract.get("allowed_decisions") != ["approve", "revise", "defer"]
        or orbit_recovery_contract.get("required_attestation") is not True
        or orbit_recovery_contract.get("workflow_authority", {}).get("review_required") is not True
        or orbit_recovery_contract.get("workflow_authority", {}).get("lock_authorized") is not True
        or orbit_recovery_contract.get("workflow_authority", {}).get("reconcile_authorized") is not True
        or "data_acquisition" in orbit_recovery_contract.get("workflow_authority", {}).get("authorized_action_classes", [])
        or orbit_recovery_contract.get("items") != [{"item_id": "M2-ORBIT-RECOVERY-001", "evidence_sha256": expected_orbit_recovery_bundle_sha}]
    ):
        fail("M2 orbit recovery review bundle or contract differs")
    if orbit_recovery_blank != {
        "response_schema_version": "nepal-m2-orbit-recovery-response-v1",
        "review_id": "m2-orbit-recovery-review-001",
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{
            "item_id": "M2-ORBIT-RECOVERY-001",
            "evidence_sha256": expected_orbit_recovery_bundle_sha,
            "decision": None,
            "notes": "",
        }],
    }:
        fail("M2 orbit recovery blank response differs or contains a human decision")

    expected_orbit_proposal_sha = "b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292"
    expected_orbit_bundle_sha = "ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1"
    if (
        orbit_proposal.get("status") != "proposed_not_active"
        or sha256("contracts/milestone-002-orbit-amendment-proposal.json") != expected_orbit_proposal_sha
        or orbit_proposal.get("parent_contract_sha256") != "fb85eb26d3143cd23cf96598a0447b9d5e6f3a3b70e8bdc35693bf52f7b1cbca"
        or orbit_proposal.get("parent_approval_sha256") != sha256("records/source-gates/m2-activation-approval.json")
        or orbit_proposal.get("candidate_manifest_sha256") != sha256("records/source-gates/m2-orbit-candidate-manifest.json")
        or orbit_proposal.get("metadata_receipt_sha256") != sha256("records/source-gates/m2-orbit-metadata-receipt.json")
        or orbit_proposal.get("source_gate_sha256") != sha256("records/source-gates/m2-orbit-source-gate.json")
        or orbit_proposal.get("authority", {}).get("mode") != "not_granted"
    ):
        fail("M2 orbit amendment proposal identity or non-authorizing boundary differs")
    orbit_records = orbit_manifest.get("records", [])
    orbit_source_ids = {item.get("source_id") for item in orbit_records}
    orbit_bound_sentinel_ids = {
        source_id for item in orbit_records for source_id in item.get("sentinel_source_ids", [])
    }
    if (
        orbit_source_ids != {"M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"}
        or orbit_bound_sentinel_ids != {f"M1-SRC-{index:03d}" for index in range(1, 7)}
        or orbit_manifest.get("summary", {}).get("combined_content_length_bytes") != 2539715
        or orbit_manifest.get("summary", {}).get("precise_covering_file_count_at_assessment") != 0
        or any(item.get("orbit_type") != "AUX_RESORB" for item in orbit_records)
    ):
        fail("M2 orbit candidate manifest exact four-file boundary differs")
    orbit_assertions = orbit_receipt.get("assertions", {})
    if (
        orbit_assertions.get("payload_bytes_requested") is not False
        or orbit_assertions.get("authentication_used") is not False
        or orbit_assertions.get("credential_values_read_or_recorded") is not False
        or orbit_assertions.get("authority_created") is not False
    ):
        fail("M2 orbit metadata capture crossed its no-payload or no-authority boundary")
    if orbit_gate.get("decision", {}).get("status") != "blocked" or any(
        {criterion.get("id"): criterion.get("status") for criterion in source.get("criteria", [])}.get("scope-authority") != "unknown"
        for source in orbit_gate.get("sources", [])
    ):
        fail("M2 orbit source gate must remain blocked only on exact scope authority")
    if (
        orbit_intake.get("status") != "candidate_not_active"
        or orbit_intake.get("extensions", {}).get("scope_authority") != "not_granted"
        or any(asset.get("state") != "not_authorized" for asset in orbit_intake.get("assets", []))
        or orbit_verification.get("status") != "candidate_not_active"
        or orbit_verification.get("authority", {}).get("mode") != "not_granted"
        or orbit_verification.get("application_boundary", {}).get("arcgis_tool") != "ApplyOrbitCorrection"
        or orbit_verification.get("application_boundary", {}).get("radar_pixel_processing_authorized_by_this_contract") is not False
    ):
        fail("M2 orbit candidate intake or verification controls are not safely gate-deferred")
    expected_orbit_surface_bindings = {
        "surface_sha256": sha256("docs/assets/m2-orbit-amendment-review.png"),
        "candidate_manifest_sha256": sha256("records/source-gates/m2-orbit-candidate-manifest.json"),
        "metadata_receipt_sha256": sha256("records/source-gates/m2-orbit-metadata-receipt.json"),
        "source_gate_sha256": sha256("records/source-gates/m2-orbit-source-gate.json"),
        "amendment_proposal_sha256": expected_orbit_proposal_sha,
        "candidate_intake_sha256": sha256("contracts/m2-orbit-intake-candidate.json"),
        "candidate_offline_verification_sha256": sha256("contracts/m2-orbit-offline-verification-candidate.json"),
        "instructions_sha256": sha256("docs/M2_ORBIT_AMENDMENT_REVIEW.md"),
        "renderer_sha256": sha256("scripts/render_m2_orbit_amendment_review.py"),
    }
    if (
        orbit_surface.get("status") != "pass"
        or orbit_surface.get("human_decision_count") != 0
        or orbit_surface.get("dimensions_pixels") != {"width": 1800, "height": 2100}
        or any(orbit_surface.get(key) != value for key, value in expected_orbit_surface_bindings.items())
        or sha256("reviews/m2-orbit-amendment/review-bundle.json") != expected_orbit_bundle_sha
        or orbit_bundle.get("candidate_identity") != "M2-ORBIT-AMENDMENT-PROPOSAL-SHA256:" + expected_orbit_proposal_sha
        or orbit_contract.get("review_bundle", {}).get("manifest_sha256") != expected_orbit_bundle_sha
        or orbit_blank.get("completed") is not False
        or orbit_blank.get("reviewer") != {"attestation": False}
        or len(orbit_blank.get("responses", [])) != 1
        or orbit_blank["responses"][0] != {
            "item_id": "M2-ORBIT-AMENDMENT-001",
            "evidence_sha256": expected_orbit_bundle_sha,
            "decision": None,
            "notes": "",
        }
    ):
        fail("M2 orbit review surface, bundle, contract, or blank response differs")

    if (
        orbit_reconciliation.get("status") != "reconciled_exact_human_response"
        or orbit_reconciliation.get("review_id") != "m2-orbit-amendment-review-001"
        or orbit_reconciliation.get("contract_sha256") != sha256("reviews/m2-orbit-amendment/review-contract.json")
        or orbit_reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or orbit_reconciliation.get("human_decisions_fabricated") is not False
        or orbit_reconciliation.get("downstream_authorization_created") is not False
    ):
        fail("M2 orbit amendment human response is not exactly reconciled")
    if (
        orbit_approval.get("status") != "approved"
        or orbit_approval.get("review_bundle_manifest_sha256") != expected_orbit_bundle_sha
        or orbit_approval.get("amendment_proposal_sha256") != expected_orbit_proposal_sha
        or orbit_approval.get("review_reconciliation_sha256") != sha256("records/source-gates/m2-orbit-amendment-review-reconciliation.json")
        or orbit_approval.get("locked_response_sha256") != orbit_reconciliation.get("response_sha256")
        or orbit_approval.get("lock_receipt_sha256") != orbit_reconciliation.get("receipt_sha256")
        or orbit_approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or orbit_approval.get("authorized_source_ids") != [f"M2-ORB-{index:03d}" for index in range(1, 5)]
        or orbit_approval.get("authorized_sentinel_source_ids") != [f"M1-SRC-{index:03d}" for index in range(1, 7)]
        or orbit_approval.get("authorized_orbit_type") != "AUX_RESORB"
        or orbit_approval.get("orbit_quality", {}).get("selected_type") != "restituted"
        or orbit_approval.get("orbit_quality", {}).get("later_precise_substitution_status") != "separately_gated_not_authorized"
        or orbit_approval.get("credential_policy", {}).get("value_recorded") is not False
        or orbit_approval.get("human_decisions_fabricated") is not False
    ):
        fail("M2 orbit amendment approval identity or bounded scope differs")
    active_orbit_assets = orbit_active_intake.get("assets", [])
    if (
        orbit_active_intake.get("status") != "active"
        or orbit_active_intake.get("extensions", {}).get("status") != "active_acquisition_review_required"
        or orbit_active_intake.get("extensions", {}).get("scope_authority") != "granted_exact_four_resorb_files"
        or orbit_active_intake.get("extensions", {}).get("amendment_approval_sha256") != sha256("records/source-gates/m2-orbit-amendment-approval.json")
        or orbit_active_intake.get("extensions", {}).get("preflight_sha256") != sha256("records/acquisition/orbit-preflight.json")
        or orbit_active_intake.get("extensions", {}).get("source_gate_sha256") != sha256("records/source-gates/m2-orbit-live-source-gate.json")
        or orbit_active_intake.get("extensions", {}).get("custody_initialization_sha256") != sha256("records/acquisition/orbit-custody-initialization.json")
        or orbit_active_intake.get("extensions", {}).get("sentinel_custody_prerequisite_status") != "partial_three_of_six_promoted_and_verified_one_failed_two_unattempted"
        or orbit_active_intake.get("extensions", {}).get("current_orbit_state_counts") != {"authorized": 3, "failed": 1, "promoted": 0}
        or orbit_active_intake.get("extensions", {}).get("current_sentinel_state_counts") != {"authorized": 4, "failed": 1, "promoted": 3}
        or [asset.get("extensions", {}).get("source_id") for asset in active_orbit_assets] != [f"M2-ORB-{index:03d}" for index in range(1, 5)]
        or active_orbit_assets[0].get("state") != "failed"
        or len(active_orbit_assets[0].get("attempts", [])) != 1
        or active_orbit_assets[0].get("attempts", [{}])[0].get("attempt_id") != "m2-orb-001-20260904t050937z-8ed21d05"
        or active_orbit_assets[0].get("attempts", [{}])[0].get("outcome") != "failed"
        or active_orbit_assets[0].get("failure", {}).get("code") != "orbit_redirect_or_http_status_rejected"
        or any(asset.get("state") != "authorized" or asset.get("attempts") != [] for asset in active_orbit_assets[1:])
    ):
        fail("active M2 orbit intake identity, custody, or pending-prerequisite state differs")
    if (
        orbit_active_verification.get("status") != "active_gate_deferred_no_promoted_orbits"
        or orbit_active_verification.get("authority", {}).get("orbit_payload_acquisition_authorized") is not True
        or orbit_active_verification.get("authority", {}).get("orbit_input_verification_authorized") is not True
        or orbit_active_verification.get("authority", {}).get("exact_source_orbit_application_authorized") is not True
        or orbit_active_verification.get("authority", {}).get("radar_pixel_processing_authorized_by_this_contract") is not False
        or orbit_active_verification.get("authority", {}).get("precise_orbit_substitution_authorized") is not False
        or orbit_active_verification.get("bindings", {}).get("amendment_approval_sha256") != sha256("records/source-gates/m2-orbit-amendment-approval.json")
        or orbit_active_verification.get("application_boundary", {}).get("overwrite_safe_source") is not False
    ):
        fail("active M2 orbit offline-verification boundary differs")
    if (
        orbit_activation.get("status") != "pass_exact_orbit_amendment_activated_preflight_and_sentinel_custody_pending"
        or orbit_activation.get("bindings", {}).get("approval_sha256") != sha256("records/source-gates/m2-orbit-amendment-approval.json")
        or orbit_activation.get("bindings", {}).get("reconciliation_sha256") != sha256("records/source-gates/m2-orbit-amendment-review-reconciliation.json")
        or orbit_activation.get("bindings", {}).get("active_verification_sha256") != sha256("contracts/m2-orbit-offline-verification.json")
        or orbit_activation.get("bindings", {}).get("activation_script_sha256") != sha256("scripts/activate_m2_orbit_amendment.py")
        or orbit_activation.get("assertions", {}).get("orbit_payload_bytes_requested") != 0
        or orbit_activation.get("assertions", {}).get("matching_sentinel_sources_promoted_at_activation") != 0
        or orbit_activation.get("assertions", {}).get("precise_substitution_authorized") is not False
    ):
        fail("M2 orbit activation receipt or claim boundary differs")
    if (
        orbit_live_gate.get("decision", {}).get("status") != "ready"
        or orbit_live_gate.get("decision", {}).get("downstream_prerequisite_status") != "blocked_on_matching_verified_sentinel_custody"
        or [source.get("source_id") for source in orbit_live_gate.get("sources", [])] != [f"M2-ORB-{index:03d}" for index in range(1, 5)]
        or any(criterion.get("status") != "pass" for source in orbit_live_gate.get("sources", []) for criterion in source.get("criteria", []))
    ):
        fail("M2 orbit live source gate differs")
    orbit_preflight_assertions = orbit_preflight.get("assertions", {})
    if (
        orbit_preflight.get("status") != "pass_no_payload_no_external_mutation_sentinel_custody_pending"
        or orbit_preflight.get("approval_sha256") != sha256("records/source-gates/m2-orbit-amendment-approval.json")
        or orbit_preflight.get("source_gate_sha256") != sha256("records/source-gates/m2-orbit-live-source-gate.json")
        or len(orbit_preflight.get("live_products", [])) != 4
        or any(item.get("status") != "pass_exact_identity_online_unchanged" for item in orbit_preflight.get("live_products", []))
        or len(orbit_preflight.get("live_rights_pages", [])) != 2
        or any(item.get("status") != "pass_exact_reviewed_bytes" for item in orbit_preflight.get("live_rights_pages", []))
        or orbit_preflight.get("sentinel_custody_prerequisite", {}).get("promoted_and_verified_count") != 0
        or orbit_preflight_assertions.get("authentication_performed") is not False
        or orbit_preflight_assertions.get("credential_values_read_or_recorded") is not False
        or orbit_preflight_assertions.get("orbit_payload_bytes_requested") != 0
        or orbit_preflight_assertions.get("precise_substitution_authorized") is not False
    ):
        fail("M2 orbit fresh preflight or no-payload boundary differs")
    if (
        orbit_custody_failure.get("status") != "failed_missing_attempt_events_parent_after_partial_empty_directory_creation"
        or len(orbit_custody_failure.get("observed_partial_directories", [])) != 7
        or orbit_custody_failure.get("observed_files") != []
        or orbit_custody_failure.get("assertions", {}).get("retry_in_attempt_001_authorized") is not False
        or orbit_custody_readiness.get("status") != "pass_exact_empty_partial_inventory_continuation_predeclared"
        or orbit_custody_readiness.get("failure_sha256") != sha256("records/acquisition/orbit-custody-initialization-attempt-001-failure.json")
        or orbit_custody_readiness.get("implementation_sha256") != sha256("scripts/initialize_m2_orbit_custody.py")
        or orbit_custody.get("status") != "created_and_verified_empty"
        or orbit_custody.get("attempt_001_failure_sha256") != sha256("records/acquisition/orbit-custody-initialization-attempt-001-failure.json")
        or orbit_custody.get("attempt_002_readiness_sha256") != sha256("records/acquisition/orbit-custody-initialization-attempt-002-readiness.json")
        or orbit_custody.get("verification", {}).get("preserved_partial_directory_count") != 7
        or orbit_custody.get("verification", {}).get("created_directory_count_attempt_002") != 10
        or orbit_custody.get("verification", {}).get("files_downloaded") != 0
        or orbit_custody.get("verification", {}).get("authentication_performed") is not False
        or orbit_custody.get("credential_values_read_or_recorded") is not False
    ):
        fail("M2 orbit custody failure, correction, or empty-success evidence differs")
    expected_orbit_runner_bindings = {
        "approval_ref": "records/source-gates/m2-orbit-amendment-approval.json",
        "approval_sha256": sha256("records/source-gates/m2-orbit-amendment-approval.json"),
        "active_intake_ref": "contracts/m2-orbit-intake.json",
        "active_intake_sha256": "d82f062a59c256a53c658dfe3c138fa2ea7de01c076339d111413e0bd99a4c9c",
        "active_verification_ref": "contracts/m2-orbit-offline-verification.json",
        "active_verification_sha256": sha256("contracts/m2-orbit-offline-verification.json"),
        "preflight_ref": "records/acquisition/orbit-preflight.json",
        "preflight_sha256": sha256("records/acquisition/orbit-preflight.json"),
        "custody_initialization_ref": "records/acquisition/orbit-custody-initialization.json",
        "custody_initialization_sha256": sha256("records/acquisition/orbit-custody-initialization.json"),
        "scripts_m2_orbit_io_core_py_sha256": "09a2c3579a89b223e8ed1d74a120bf74f1ff7c79d4be979eb30fc0d679e9596d",
        "scripts_acquire_m2_orbit_file_py_sha256": "eaa21a82a6eb38a471e05b1fa9df2f5aa6378d087b6da0dfe5377abfab3b7248",
        "scripts_verify_m2_orbit_eof_py_sha256": "f043ffacdad9f0cc135f91a0a46e4a19e92303bf9bc48b04ca96968a641ec30c",
        "tests_test_m2_orbit_activation_py_sha256": "da1e9e82aa38e10b0ba9fb6d3e68548d8ea80f2b3a6c91c0de54615c886728fe",
        "tests_test_m2_orbit_preflight_py_sha256": "888c73e84c665c2318739ed95d0e65799d51a67181c67b57eb6660635c8344f0",
        "tests_test_m2_orbit_io_py_sha256": "607e48fb0ad36d1f150c843add471aa6b0991a57e9933184eec18d05cd167937",
        "_github_workflows_validate_yml_sha256": "885df3ee211dc31b2ea96b81a1df25ca7f474a09f73beeef73cd72b969f73bd1",
    }
    if (
        orbit_runner_readiness.get("status") != "pass_static_synthetic_and_guard_probe_transfer_blocked_on_sentinel_custody"
        or orbit_runner_readiness.get("bindings") != expected_orbit_runner_bindings
        or orbit_runner_readiness.get("dependency", {}).get("required_version") != "1.0.9"
        or orbit_runner_readiness.get("dependency", {}).get("observed_version") != "1.0.9"
        or orbit_runner_readiness.get("dependency", {}).get("known_abc_digest") != "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85"
        or orbit_runner_readiness.get("dependency", {}).get("ci_install_pinned") is not True
        or orbit_runner_readiness.get("verification", {}).get("full_repository_test_count") != 219
        or orbit_runner_readiness.get("verification", {}).get("full_repository_tests") != "pass"
        or orbit_runner_readiness.get("verification", {}).get("focused_orbit_test_count") != 29
        or orbit_runner_readiness.get("verification", {}).get("focused_orbit_tests") != "pass"
        or orbit_runner_readiness.get("verification", {}).get("guard_probe_exit_code") != 12
        or orbit_runner_readiness.get("verification", {}).get("guard_probe_stop_code") != "bound_sentinel_source_not_promoted"
        or orbit_runner_readiness.get("verification", {}).get("active_control_hashes_unchanged") is not True
        or orbit_runner_readiness.get("verification", {}).get("orbit_payload_file_count") != 0
        or orbit_runner_readiness.get("assertions", {}).get("sentinel_promoted_and_verified_count") != 0
        or orbit_runner_readiness.get("assertions", {}).get("runner_checks_sentinel_custody_before_catalogue_and_token_read") is not True
        or orbit_runner_readiness.get("assertions", {}).get("network_requests_performed_by_readiness") is not False
        or orbit_runner_readiness.get("assertions", {}).get("authentication_performed_by_readiness") is not False
        or orbit_runner_readiness.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or orbit_runner_readiness.get("assertions", {}).get("orbit_payload_bytes_requested") != 0
        or orbit_runner_readiness.get("assertions", {}).get("precise_substitution_authorized") is not False
        or orbit_runner_readiness.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("M2 orbit runner readiness or custody guard differs")
    expected_orbit_unavailable_reason = (
        "CDSE catalogue metadata records exact content length plus provider MD5 and BLAKE3, but no upstream SHA-256. "
        "Revalidate the catalogue identity and compute SHA-256 locally before promotion."
    )
    if (
        orbit_intake_schema_failure.get("status") != "failed_missing_unavailable_reason_for_unknown_pretransfer_sha256"
        or orbit_intake_schema_failure.get("intake_sha256_at_failure") != expected_orbit_runner_bindings["active_intake_sha256"]
        or orbit_intake_schema_failure.get("errors") != [
            f"assets[{index}].expected.unavailable_reason: required when expected identity is incomplete"
            for index in range(4)
        ]
        or orbit_intake_schema_failure.get("assertions", {}).get("orbit_payload_bytes_requested") != 0
        or orbit_intake_schema_failure.get("assertions", {}).get("silent_correction_authorized") is not False
    ):
        fail("M2 orbit intake generic-schema validation failure differs")
    if (
        any(asset.get("expected", {}).get("unavailable_reason") != expected_orbit_unavailable_reason for asset in active_orbit_assets)
        or orbit_intake_schema_correction.get("status") != "pass_required_unavailable_reason_added_active_intake_valid_transfer_still_blocked"
        or orbit_intake_schema_correction.get("failure_sha256") != sha256("records/acquisition/orbit-intake-schema-validation-failure.json")
        or orbit_intake_schema_correction.get("intake_sha256_before_correction") != expected_orbit_runner_bindings["active_intake_sha256"]
        or orbit_intake_schema_correction.get("intake_sha256_after_correction") != "b52512ecf86a7d85f99f5cff932219bc29620f08871e3b3242b76b645b0e2604"
        or orbit_intake_schema_correction.get("correction", {}).get("asset_ids") != [f"M2-ORB-{index:03d}" for index in range(1, 5)]
        or orbit_intake_schema_correction.get("correction", {}).get("field") != "expected.unavailable_reason"
        or orbit_intake_schema_correction.get("correction", {}).get("value") != expected_orbit_unavailable_reason
        or orbit_intake_schema_correction.get("correction", {}).get("fields_added") != 4
        or orbit_intake_schema_correction.get("correction", {}).get("other_fields_changed") != 0
        or orbit_intake_schema_correction.get("validator", {}).get("status") != "pass"
        or orbit_intake_schema_correction.get("validator", {}).get("errors") != []
        or orbit_intake_schema_correction.get("historical_runner_readiness_sha256") != sha256("records/acquisition/orbit-runner-readiness.json")
        or orbit_intake_schema_correction.get("verification", {}).get("guard_probe_exit_code") != 12
        or orbit_intake_schema_correction.get("verification", {}).get("guard_probe_stop_code") != "bound_sentinel_source_not_promoted"
        or orbit_intake_schema_correction.get("verification", {}).get("orbit_payload_file_count") != 0
        or orbit_intake_schema_correction.get("assertions", {}).get("authorization_changed") is not False
        or orbit_intake_schema_correction.get("assertions", {}).get("network_requests_performed_by_correction") is not False
        or orbit_intake_schema_correction.get("assertions", {}).get("authentication_performed_by_correction") is not False
        or orbit_intake_schema_correction.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or orbit_intake_schema_correction.get("assertions", {}).get("orbit_payload_bytes_requested") != 0
        or orbit_intake_schema_correction.get("assertions", {}).get("precise_substitution_authorized") is not False
        or orbit_intake_schema_correction.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("M2 orbit active-intake schema correction differs")
    if (
        orbit_intake_label_inconsistency.get("status") != "failed_stale_candidate_status_on_activated_intake"
        or orbit_intake_label_inconsistency.get("intake_sha256_at_finding") != "b52512ecf86a7d85f99f5cff932219bc29620f08871e3b3242b76b645b0e2604"
        or orbit_intake_label_inconsistency.get("observed_root_status") != "candidate_not_active"
        or orbit_intake_label_inconsistency.get("expected_root_status") != "active"
        or orbit_intake_label_inconsistency.get("assertions", {}).get("asset_attempt_count") != 0
        or orbit_intake_label_inconsistency.get("assertions", {}).get("orbit_payload_bytes_requested") != 0
        or orbit_intake_label_inconsistency.get("assertions", {}).get("silent_correction_authorized") is not False
    ):
        fail("M2 orbit active-intake stale activation label finding differs")
    if (
        orbit_intake_label_correction.get("status") != "pass_root_status_corrected_active_transfer_still_blocked"
        or orbit_intake_label_correction.get("finding_sha256") != sha256("records/acquisition/orbit-intake-activation-label-inconsistency.json")
        or orbit_intake_label_correction.get("intake_sha256_before_correction") != "b52512ecf86a7d85f99f5cff932219bc29620f08871e3b3242b76b645b0e2604"
        or orbit_intake_label_correction.get("intake_sha256_after_correction") != "9e1c2675b4716ec78fbca8c3c2e9cf0bd3df20cf6362b5bba0db4de582a27539"
        or orbit_intake_label_correction.get("correction") != {
            "field": "status",
            "before": "candidate_not_active",
            "after": "active",
            "other_fields_changed": 0,
        }
        or orbit_intake_label_correction.get("validation", {}).get("generic_intake_validator_status") != "pass"
        or orbit_intake_label_correction.get("validation", {}).get("generic_intake_validator_errors") != []
        or orbit_intake_label_correction.get("validation", {}).get("guard_probe_exit_code") != 12
        or orbit_intake_label_correction.get("validation", {}).get("guard_probe_stop_code") != "bound_sentinel_source_not_promoted"
        or orbit_intake_label_correction.get("validation", {}).get("orbit_payload_file_count") != 0
        or orbit_intake_label_correction.get("assertions", {}).get("authorization_changed") is not False
        or orbit_intake_label_correction.get("assertions", {}).get("network_requests_performed_by_correction") is not False
        or orbit_intake_label_correction.get("assertions", {}).get("authentication_performed_by_correction") is not False
        or orbit_intake_label_correction.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or orbit_intake_label_correction.get("assertions", {}).get("orbit_payload_bytes_requested") != 0
        or orbit_intake_label_correction.get("assertions", {}).get("precise_substitution_authorized") is not False
        or orbit_intake_label_correction.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("M2 orbit active-intake activation label correction differs")

    expected_vertical_candidate = "M2-DEM-VERTICAL-DATUM-PROPOSAL-SHA256:" + sha256("contracts/m2-dem-vertical-datum-proposal.json")
    if (
        dem_vertical_proposal.get("status") != "proposed_not_active"
        or dem_vertical_bundle.get("candidate_identity") != expected_vertical_candidate
        or dem_vertical_contract.get("review_bundle", {}).get("candidate_identity") != expected_vertical_candidate
        or dem_vertical_contract.get("review_bundle", {}).get("manifest_sha256") != sha256("reviews/m2-dem-vertical-datum/review-bundle.json")
    ):
        fail("M2 DEM vertical-datum proposal or review-bundle identity differs")
    expected_vertical_proposal_bindings = {
        "dem_approval_sha256": sha256("records/source-gates/m2-dem-amendment-approval.json"),
        "dem_verification_summary_sha256": sha256("records/acquisition/dem-verification-summary.json"),
        "radar_processing_contract_sha256": sha256("config/qa/radar-baseline-processing-contract.json"),
        "source_review_sha256": sha256("records/source-gates/m2-dem-vertical-datum-source-review.json"),
        "local_capability_sha256": sha256("records/surface-receipts/m2-dem-vertical-datum-capability.json"),
    }
    if any(dem_vertical_proposal.get("bindings", {}).get(key) != value for key, value in expected_vertical_proposal_bindings.items()):
        fail("M2 DEM vertical-datum proposal bindings differ")
    selected_vertical_route = dem_vertical_proposal.get("selected_if_approved", {})
    if (
        dem_vertical_proposal.get("decision_requested", {}).get("recommended_route") != "arcgis_egm2008_1x1_preconversion_then_none"
        or selected_vertical_route.get("required_arcgis_component", {}).get("feature") != "world1x1_vert"
        or selected_vertical_route.get("required_arcgis_component", {}).get("expected_grid") != "Dataset_egm2008-1.grd"
        or selected_vertical_route.get("required_arcgis_component", {}).get("expected_wkid") != 110018
        or selected_vertical_route.get("radar_tool_parameter_after_conversion") != "NONE"
        or selected_vertical_route.get("egm96_builtin_route", {}).get("production_status") != "not_selected"
    ):
        fail("M2 DEM vertical-datum proposed method differs")
    prohibited_vertical_actions = set(dem_vertical_proposal.get("actions_not_authorized", []))
    if not {
        "download or install software or coordinate-system data",
        "approve or dismiss UAC or another privileged prompt",
        "use raw EGM2008 orthometric tiles with NONE",
        "download updated orbit vectors",
    } <= prohibited_vertical_actions:
        fail("M2 DEM vertical-datum proposal no longer preserves owner-control or scientific boundaries")
    if (
        dem_vertical_capability.get("status") != "defer_exact_egm2008_grid_not_installed"
        or dem_vertical_capability.get("runtime") != {"product": "ArcGISPro", "version": "3.7.1", "license_level": "Advanced"}
        or dem_vertical_capability.get("inspection", {}).get("matching_egm2008_grids") != []
        or dem_vertical_capability.get("inspection", {}).get("listed_transformations") != []
        or dem_vertical_capability.get("inspection", {}).get("builtin_egm96_grid", {}).get("present") is not True
        or dem_vertical_capability.get("decision", {}).get("exact_egm2008_preconversion_available_now") is not False
    ):
        fail("M2 DEM vertical-datum local capability differs")
    expected_vertical_source_roles = {
        "arcgis_radiometric_terrain_flattening",
        "copernicus_dem_vertical_reference",
        "epsg_vertical_crs",
        "arcgis_coordinate_systems_data_install",
        "arcgis_coordinate_systems_data_feature",
        "arcgis_project_raster_vertical_transform",
        "arcgis_supported_vertical_transformations",
        "nga_egm2008_authority",
    }
    if (
        dem_vertical_sources.get("status") != "pass_official_sources_exact_route_requires_owner_installed_component"
        or {item.get("role") for item in dem_vertical_sources.get("official_sources", [])} != expected_vertical_source_roles
        or dem_vertical_sources.get("route_assessment", {}).get("recommended_route") != "arcgis_egm2008_1x1_preconversion_then_none"
        or dem_vertical_sources.get("assertions", {}).get("vertical_datum_route_activated") is not False
    ):
        fail("M2 DEM vertical-datum official source review differs")
    if (
        dem_vertical_blank.get("completed") is not False
        or dem_vertical_blank.get("reviewer") != {"attestation": False}
        or len(dem_vertical_blank.get("responses", [])) != 1
        or dem_vertical_blank["responses"][0].get("decision") is not None
        or dem_vertical_blank["responses"][0].get("evidence_sha256") != sha256("reviews/m2-dem-vertical-datum/review-bundle.json")
    ):
        fail("M2 DEM vertical-datum blank response is not blank and exactly bound")
    if dem_manifest.get("status") != "candidate_not_approved" or len(dem_manifest.get("records", [])) != 4:
        fail("M2 DEM candidate manifest must remain an unapproved exact four-tile set")
    expected_dem_ids = {
        "Copernicus_DSM_COG_10_N27_00_E084_00_DEM",
        "Copernicus_DSM_COG_10_N27_00_E085_00_DEM",
        "Copernicus_DSM_COG_10_N28_00_E084_00_DEM",
        "Copernicus_DSM_COG_10_N28_00_E085_00_DEM",
    }
    if {record.get("item_id") for record in dem_manifest["records"]} != expected_dem_ids:
        fail("M2 DEM candidate tile identities differ")
    if dem_manifest.get("summary", {}).get("combined_content_length_bytes") != 170302058:
        fail("M2 DEM candidate total byte count differs")
    dem_assertions = dem_receipt.get("assertions", {})
    if dem_assertions.get("payload_bytes_requested") is not False or dem_assertions.get("license_accepted") is not False:
        fail("M2 DEM metadata receipt must preserve its no-payload and no-acceptance boundary")
    if dem_gate.get("decision", {}).get("status") != "blocked" or len(dem_gate.get("sources", [])) != 4:
        fail("M2 DEM source gate must remain blocked for exactly four sources")
    for source in dem_gate["sources"]:
        criteria = {criterion.get("id"): criterion for criterion in source.get("criteria", [])}
        if criteria.get("terms-acceptance", {}).get("status") != "unknown":
            fail("M2 DEM source gate must retain pending exact license acceptance")
        if criteria.get("scope-authority", {}).get("status") != "unknown":
            fail("M2 DEM source gate must retain pending scope authority")
    if dem_proposal.get("status") != "proposed_not_active" or dem_proposal.get("authority", {}).get("mode") != "not_granted":
        fail("M2 DEM amendment must remain proposed and non-authorizing")
    expected_dem_bindings = {
        "candidate_manifest_sha256": sha256("records/source-gates/m2-dem-candidate-manifest.json"),
        "metadata_receipt_sha256": sha256("records/source-gates/m2-dem-metadata-receipt.json"),
        "source_gate_sha256": sha256("records/source-gates/m2-dem-source-gate.json"),
        "arcgis_capability_sha256": sha256("records/surface-receipts/arcgis-sar-processing-capability.json"),
    }
    if any(dem_proposal.get(key) != value for key, value in expected_dem_bindings.items()):
        fail("M2 DEM amendment has stale evidence bindings")
    if dem_bundle.get("candidate_identity") != f"M2-DEM-AMENDMENT-PROPOSAL-SHA256:{sha256('contracts/milestone-002-dem-amendment-proposal.json')}":
        fail("M2 DEM review bundle does not bind the exact amendment proposal")
    if dem_contract.get("items", [{}])[0].get("evidence_sha256") != sha256("reviews/m2-dem-amendment/review-bundle.json"):
        fail("M2 DEM review item does not bind the exact review bundle")
    if dem_blank.get("completed") is not False or dem_blank.get("reviewer", {}).get("attestation") is not False:
        fail("M2 DEM blank response must contain no human decision")
    if any(response.get("decision") is not None for response in dem_blank.get("responses", [])):
        fail("M2 DEM blank response contains a fabricated decision")
    if dem_reconciliation.get("status") != "reconciled_exact_human_response" or dem_reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        fail("M2 DEM amendment response is not one exact reconciled approval")
    if dem_reconciliation.get("contract_sha256") != sha256("reviews/m2-dem-amendment/review-contract.json") or dem_reconciliation.get("human_decisions_fabricated") is not False:
        fail("M2 DEM amendment reconciliation binding or fabrication flag differs")
    if dem_approval.get("status") != "approved":
        fail("M2 DEM amendment approval is not active")
    expected_dem_approval_bindings = {
        "review_bundle_manifest_sha256": "caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e",
        "amendment_proposal_sha256": "92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69",
        "review_reconciliation_sha256": sha256("records/source-gates/m2-dem-amendment-review-reconciliation.json"),
        "locked_response_sha256": dem_reconciliation.get("response_sha256"),
        "lock_receipt_sha256": dem_reconciliation.get("receipt_sha256"),
    }
    if any(dem_approval.get(key) != value for key, value in expected_dem_approval_bindings.items()):
        fail("M2 DEM amendment approval bindings differ")
    if dem_approval.get("license") != {
        "name": "Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full, Free & Open",
        "url": "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf",
        "document_sha256": "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd",
        "acceptance_status": "accepted_exact_hash_bound_document",
    }:
        fail("M2 DEM amendment approval license binding differs")
    expected_dem_source_ids = set(expected_dem_source_order)
    if set(dem_approval.get("authorized_source_ids", [])) != expected_dem_source_ids:
        fail("M2 DEM amendment approval source set differs")
    if dem_approval.get("human_decisions_fabricated") is not False:
        fail("M2 DEM amendment approval must not report fabricated decisions")
    if dem_intake_active.get("extensions", {}).get("status") != expected_dem_intake_status:
        fail("active M2 DEM intake identity or state differs")
    for asset in dem_current_assets:
        source_id = asset["extensions"]["source_id"]
        state = asset["state"]
        attempts = asset.get("attempts", [])
        if asset.get("source", {}).get("authorization_ref") != "records/source-gates/m2-dem-amendment-approval.json":
            fail(f"active M2 DEM intake loses approval binding for {source_id}")
        if state == "authorized":
            if attempts or any(value is not None for value in asset.get("observed", {}).values()):
                fail(f"authorized DEM asset invents transfer progress for {source_id}")
            continue
        if len(attempts) != 1 or attempts[0].get("outcome") not in {"succeeded", "failed"} or not attempts[0].get("completed_at"):
            fail(f"terminal DEM attempt history differs for {source_id}")
        if state == "promoted":
            receipt_ref = asset.get("extensions", {}).get("successful_attempt_receipt")
            if not isinstance(receipt_ref, str) or not receipt_ref.startswith("records/acquisition/dem-attempts/") or not (ROOT / receipt_ref).is_file():
                fail(f"promoted DEM asset receipt is absent for {source_id}")
            receipt = json.loads((ROOT / receipt_ref).read_text(encoding="utf-8"))
            observed = asset.get("observed", {})
            if (
                asset["extensions"].get("successful_attempt_receipt_sha256") != sha256(receipt_ref)
                or receipt.get("event") != "dem_transfer_succeeded"
                or receipt.get("attempt_id") != attempts[0].get("attempt_id")
                or receipt.get("source_id") != source_id
                or receipt.get("local_sha256") != observed.get("promoted_sha256")
                or receipt.get("local_size_bytes") != observed.get("promoted_size_bytes")
                or observed.get("staged_sha256") != observed.get("promoted_sha256")
                or observed.get("staged_size_bytes") != observed.get("promoted_size_bytes")
            ):
                fail(f"promoted DEM asset identity or receipt differs for {source_id}")
            if dem_all_geotiff_verified:
                verification_ref = asset["extensions"].get("geotiff_verification_receipt")
                if not isinstance(verification_ref, str) or not (ROOT / verification_ref).is_file():
                    fail(f"verified DEM asset receipt is absent for {source_id}")
                verification_receipt = json.loads((ROOT / verification_ref).read_text(encoding="utf-8"))
                if (
                    asset["extensions"].get("geotiff_verification_receipt_sha256") != sha256(verification_ref)
                    or verification_receipt.get("status") != "pass_structural_only"
                    or verification_receipt.get("source_id") != source_id
                    or verification_receipt.get("observed", {}).get("sha256") != observed.get("promoted_sha256")
                    or verification_receipt.get("evaluation", {}).get("failures") != []
                    or verification_receipt.get("custody_inventory_before") != verification_receipt.get("custody_inventory_after")
                ):
                    fail(f"verified DEM asset receipt differs for {source_id}")
        elif attempts[0].get("outcome") != "failed" or not asset.get("failure", {}).get("code"):
            fail(f"failed DEM asset does not preserve its terminal failure for {source_id}")
    if dem_intake_active.get("extensions", {}).get("license_acceptance_status") != "accepted_exact_hash_bound_document":
        fail("active M2 DEM intake does not preserve exact license acceptance")
    expected_dem_intake_progress_bindings = {
        "source_gate_ref": "records/source-gates/m2-dem-live-source-gate.json",
        "source_gate_sha256": sha256("records/source-gates/m2-dem-live-source-gate.json"),
        "preflight_ref": "records/acquisition/dem-preflight.json",
        "preflight_sha256": sha256("records/acquisition/dem-preflight.json"),
        "custody_initialization_ref": "records/acquisition/dem-custody-initialization.json",
        "custody_initialization_sha256": sha256("records/acquisition/dem-custody-initialization.json"),
        "custody_initialized": True,
    }
    if any(dem_intake_active.get("extensions", {}).get(key) != value for key, value in expected_dem_intake_progress_bindings.items()):
        fail("active M2 DEM intake preflight or custody bindings differ")
    if dem_state_counts["promoted"] or dem_state_counts["failed"]:
        dem_extensions = dem_intake_active.get("extensions", {})
        checkpoint_ref = dem_extensions.get("last_checkpoint_ref")
        if not isinstance(checkpoint_ref, str) or not checkpoint_ref.startswith("records/acquisition/dem-checkpoints/") or not (ROOT / checkpoint_ref).is_file():
            fail("active M2 DEM intake is missing its latest reconciliation checkpoint")
        if dem_extensions.get("last_checkpoint_sha256") != sha256(checkpoint_ref):
            fail("active M2 DEM intake latest reconciliation checkpoint hash differs")
        checkpoint_receipt = json.loads((ROOT / checkpoint_ref).read_text(encoding="utf-8"))
        if (
            checkpoint_receipt.get("attempt_id") != dem_extensions.get("last_reconciled_attempt_id")
            or checkpoint_receipt.get("progress", {}).get("counts") != dem_state_counts
            or checkpoint_receipt.get("progress", {}).get("checkpoint") != expected_dem_transfer_checkpoint
            or checkpoint_receipt.get("bindings", {}).get("approval_sha256") != sha256("records/source-gates/m2-dem-amendment-approval.json")
            or checkpoint_receipt.get("bindings", {}).get("preflight_sha256") != sha256("records/acquisition/dem-preflight.json")
        ):
            fail("active M2 DEM reconciliation checkpoint differs from current progress")
        expected_dem_claim_boundary = {
            "transferred_byte_identity_established_for_promoted_assets": True,
            "geotiff_readability_established": False,
            "valid_pixel_coverage_established": False,
            "vertical_datum_route_established": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        }
        if checkpoint_receipt.get("claim_boundary") != expected_dem_claim_boundary:
            fail("active M2 DEM reconciliation checkpoint claim boundary differs")
    if dem_verification_active.get("status") != expected_dem_verification_status:
        fail("active M2 DEM verification status differs from acquisition progress")
    active_dem_verification_authority = dem_verification_active.get("authority", {})
    if active_dem_verification_authority != {
        "dem_amendment_status": "approved",
        "license_acceptance_established": True,
        "network_access_authorized": False,
        "custody_mutation_authorized": False,
        "dem_download_authorized": False,
        "dem_pixel_processing_authorized": True,
        "this_contract_creates_authority": False,
    }:
        fail("active M2 DEM verification authority differs")
    if dem_verification_active.get("inputs", {}).get("intake_contract_ref") != "contracts/m2-dem-intake.json" or dem_verification_active.get("inputs", {}).get("intake_contract_sha256") != sha256("contracts/m2-dem-intake.json"):
        fail("active M2 DEM verification does not bind the active intake")
    if dem_all_geotiff_verified:
        dem_verification_summary = json.loads((ROOT / "records/acquisition/dem-verification-summary.json").read_text(encoding="utf-8"))
        summary_sha = sha256("records/acquisition/dem-verification-summary.json")
        if (
            dem_verification_summary.get("status") != "pass_structural_and_valid_aoi_coverage_vertical_datum_deferred"
            or dem_verification_summary.get("totals") != {"passing_tile_count": 4, "retained_failed_attempt_count": 2, "verified_bytes": 170302058, "finite_non_nodata_cells": 51840000, "nodata_or_nonfinite_cells": 0}
            or dem_verification_summary.get("next_checkpoint") != "M2-DEM-VERTICAL-DATUM-REVIEW"
            or dem_intake_active.get("extensions", {}).get("dem_verification_summary_sha256") != summary_sha
            or dem_verification_active.get("result", {}).get("summary_sha256") != summary_sha
        ):
            fail("completed M2 DEM verification summary or active bindings differ")
        if [item.get("source_id") for item in dem_verification_summary.get("passing_assets", [])] != expected_dem_source_order:
            fail("completed M2 DEM verification summary source order differs")
        for item in dem_verification_summary.get("passing_assets", []) + dem_verification_summary.get("retained_failed_attempts", []):
            relative = item.get("receipt_ref")
            if not isinstance(relative, str) or not (ROOT / relative).is_file() or item.get("receipt_sha256") != sha256(relative):
                fail("completed M2 DEM verification summary has a stale receipt binding")
        if [item.get("aoi_id") for item in dem_verification_summary.get("aoi_coverage", [])] != ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"] or any(item.get("status") != "pass_valid_coverage" for item in dem_verification_summary.get("aoi_coverage", [])):
            fail("completed M2 DEM verification AOI coverage differs")
        expected_completed_dem_claims = {
            "exact_local_byte_identity_established": True,
            "arcgis_geotiff_structural_fitness_established": True,
            "approved_aoi_valid_pixel_coverage_established": True,
            "void_seam_artifact_review_established": False,
            "vertical_datum_route_established": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        }
        if dem_verification_summary.get("claim_boundary") != expected_completed_dem_claims:
            fail("completed M2 DEM verification claim boundary differs")

    if (
        dem_terrain_contract.get("contract_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-001"
        or dem_terrain_contract.get("status") != "predeclared_not_executed"
    ):
        fail("DEM terrain-quality contract identity or pre-execution status differs")
    expected_dem_terrain_bindings = {
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256": sha256("contracts/m2-dem-intake.json"),
        "dem_verification_summary_ref": "records/acquisition/dem-verification-summary.json",
        "dem_verification_summary_sha256": sha256("records/acquisition/dem-verification-summary.json"),
        "approved_aoi_ref": "config/aoi/approved-study-areas-epsg32645.json",
        "approved_aoi_sha256": sha256("config/aoi/approved-study-areas-epsg32645.json"),
        "vertical_datum_proposal_ref": "contracts/m2-dem-vertical-datum-proposal.json",
        "vertical_datum_proposal_sha256": sha256("contracts/m2-dem-vertical-datum-proposal.json"),
        "implementation_ref": "scripts/inspect_m2_dem_terrain_quality_arcgis.py",
        "implementation_sha256": sha256("scripts/inspect_m2_dem_terrain_quality_arcgis.py"),
        "core_ref": "scripts/dem_terrain_quality_core.py",
        "core_sha256": sha256("scripts/dem_terrain_quality_core.py"),
        "test_ref": "tests/test_dem_terrain_quality_core.py",
        "test_sha256": sha256("tests/test_dem_terrain_quality_core.py"),
    }
    if dem_terrain_contract.get("bindings") != expected_dem_terrain_bindings:
        fail("DEM terrain-quality contract bindings differ")
    terrain_assets = dem_terrain_contract.get("inputs", {}).get("assets", [])
    if [item.get("source_id") for item in terrain_assets] != expected_dem_source_order:
        fail("DEM terrain-quality source order differs")
    for terrain_asset, intake_asset in zip(terrain_assets, dem_current_assets):
        observed = intake_asset.get("observed", {})
        if (
            terrain_asset.get("source_id") != intake_asset.get("extensions", {}).get("source_id")
            or terrain_asset.get("asset_id") != intake_asset.get("asset_id")
            or terrain_asset.get("custody_relative_path") != intake_asset.get("destination_relative_path")
            or terrain_asset.get("sha256") != observed.get("promoted_sha256")
            or terrain_asset.get("size_bytes") != observed.get("promoted_size_bytes")
            or terrain_asset.get("expected_bbox_wgs84") != intake_asset.get("extensions", {}).get("expected_bbox_wgs84")
        ):
            fail(f"DEM terrain-quality source binding differs for {terrain_asset.get('source_id')}")
    expected_dem_terrain_seams = [
        {"seam_id": "SEAM-E85-N27", "orientation": "west_east", "first_source_id": "M2-DEM-001", "second_source_id": "M2-DEM-002", "boundary": "longitude 85 degrees east"},
        {"seam_id": "SEAM-E85-N28", "orientation": "west_east", "first_source_id": "M2-DEM-003", "second_source_id": "M2-DEM-004", "boundary": "longitude 85 degrees east"},
        {"seam_id": "SEAM-N28-E84", "orientation": "south_north", "first_source_id": "M2-DEM-001", "second_source_id": "M2-DEM-003", "boundary": "latitude 28 degrees north"},
        {"seam_id": "SEAM-N28-E85", "orientation": "south_north", "first_source_id": "M2-DEM-002", "second_source_id": "M2-DEM-004", "boundary": "latitude 28 degrees north"},
    ]
    if dem_terrain_contract.get("seam_pairs") != expected_dem_terrain_seams:
        fail("DEM terrain-quality seam pairs differ")
    expected_dem_terrain_thresholds = {
        "tile": {
            "block_nodata_or_nonfinite_count": 0,
            "block_minimum_elevation_m": -500.0,
            "block_maximum_elevation_m": 9000.0,
            "block_max_abs_local_curvature_m": 2000.0,
            "defer_abs_local_curvature_m": 1000.0,
            "defer_local_curvature_fraction": 0.0001,
            "defer_exact_2x2_plateau_fraction": 0.5,
        },
        "seam": {
            "block_residual_abs_max_m": 2000.0,
            "defer_signed_median_abs_m": 25.0,
            "defer_residual_abs_median_m": 30.0,
            "defer_residual_abs_p95_m": 150.0,
            "defer_residual_abs_p99_m": 300.0,
            "defer_residual_level_m": 100.0,
            "defer_residual_above_level_fraction": 0.05,
        },
        "slope": {
            "block_maximum_degrees": 90.0,
            "defer_level_degrees": 85.0,
            "defer_fraction_above_level": 0.001,
        },
    }
    if dem_terrain_contract.get("thresholds") != expected_dem_terrain_thresholds:
        fail("DEM terrain-quality thresholds differ")
    terrain_processing = dem_terrain_contract.get("processing", {})
    if (
        terrain_processing.get("analysis_crs", {}).get("wkid") != 32645
        or terrain_processing.get("target_cell_size_m") != 30.0
        or terrain_processing.get("horizontal_projection_resampling") != "BILINEAR"
        or terrain_processing.get("vertical_transformation") is not None
        or terrain_processing.get("output_root") != r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-001"
        or terrain_processing.get("output_collision_policy") != "refuse"
        or terrain_processing.get("source_mutation") != "prohibited"
    ):
        fail("DEM terrain-quality processing boundary differs")
    terrain_prohibitions = set(dem_terrain_contract.get("authority", {}).get("not_authorized", []))
    required_terrain_prohibitions = {
        "alter or overwrite source DEM tiles",
        "select or execute a vertical-datum conversion",
        "process Sentinel pixels",
        "publish DEM-derived raster imagery",
    }
    if not required_terrain_prohibitions.issubset(terrain_prohibitions):
        fail("DEM terrain-quality contract loses a required prohibition")
    expected_dem_terrain_readiness_bindings = {
        "contract_ref": "config/qa/dem-terrain-quality-contract.json",
        "contract_sha256": sha256("config/qa/dem-terrain-quality-contract.json"),
        "implementation_ref": "scripts/inspect_m2_dem_terrain_quality_arcgis.py",
        "implementation_sha256": sha256("scripts/inspect_m2_dem_terrain_quality_arcgis.py"),
        "core_ref": "scripts/dem_terrain_quality_core.py",
        "core_sha256": sha256("scripts/dem_terrain_quality_core.py"),
        "test_ref": "tests/test_dem_terrain_quality_core.py",
        "test_sha256": sha256("tests/test_dem_terrain_quality_core.py"),
        "protocol_ref": "docs/DEM_TERRAIN_QUALITY_PROTOCOL.md",
        "protocol_sha256": sha256("docs/DEM_TERRAIN_QUALITY_PROTOCOL.md"),
    }
    expected_dem_terrain_validation = {
        "focused_test_count": 5,
        "focused_test_status": "pass",
        "full_repository_test_count": 190,
        "full_repository_test_status": "pass",
        "repository_required_file_count": 199,
        "repository_validation_status": "pass",
        "arcgis_runtime_execution": "not_started",
        "output_root_exists": False,
        "candidate_receipt_exists": False,
    }
    expected_dem_terrain_assertions = {
        "thresholds_fixed_before_real_metrics": True,
        "four_exact_sources_bound": True,
        "four_native_seams_bound": True,
        "analysis_crs_wkid": 32645,
        "vertical_transformation_selected": False,
        "source_dem_pixels_read_by_readiness": False,
        "derived_outputs_created_by_readiness": False,
        "external_custody_mutated_by_readiness": False,
        "network_requests_performed": False,
        "scientific_result_established": False,
        "authority_created": False,
    }
    if (
        dem_terrain_readiness.get("readiness_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-READINESS-001"
        or dem_terrain_readiness.get("status") != "pass_static_controls_real_execution_not_started"
        or dem_terrain_readiness.get("bindings") != expected_dem_terrain_readiness_bindings
        or dem_terrain_readiness.get("validation") != expected_dem_terrain_validation
        or dem_terrain_readiness.get("assertions") != expected_dem_terrain_assertions
        or not dem_terrain_readiness.get("retained_validation_failures")
    ):
        fail("DEM terrain-quality readiness receipt differs")
    expected_dem_terrain_ci_assertions = {
        "failed_runs_preserved": True,
        "dependency_version_pinned": True,
        "remote_repository_check_passed": True,
        "remote_full_suite_passed": True,
        "real_dem_metrics_observed": False,
        "arcgis_terrain_execution_started": False,
        "terrain_thresholds_changed": False,
        "source_dem_files_mutated": False,
        "vertical_datum_route_established": False,
        "sentinel_processing_executed": False,
        "scientific_result_established": False,
        "authority_created": False,
        "newline_normalization_failure_preserved": True,
        "portable_lf_hash_binding_required": True,
    }
    failed_terrain_ci_runs = dem_terrain_ci_correction.get("failed_runs", [])
    passing_terrain_ci = dem_terrain_ci_correction.get("passing_validation", {})
    terrain_ci_change = dem_terrain_ci_correction.get("correction", {})
    if (
        dem_terrain_ci_correction.get("correction_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-CI-CORRECTION-001"
        or dem_terrain_ci_correction.get("status") != "pass_pinned_numpy_dependency_workflow_syntax_and_hash_portability_corrected"
        or [item.get("run_id") for item in failed_terrain_ci_runs] != [33819299553, 33819378562, 33819677224]
        or failed_terrain_ci_runs[0].get("error") != "ModuleNotFoundError: No module named 'numpy'"
        or failed_terrain_ci_runs[1].get("status") != "failure_no_jobs"
        or failed_terrain_ci_runs[2].get("error") != "FAIL: EVID-0044 DEM terrain-quality CI correction differs"
        or terrain_ci_change.get("workflow_ref") != ".github/workflows/validate.yml"
        or terrain_ci_change.get("workflow_sha256") != "330de5934a82ae1998973ff5cf5b97360cd72e6b8f926e51a409178036932029"
        or terrain_ci_change.get("pinned_dependency") != "numpy==2.5.1"
        or terrain_ci_change.get("threshold_contract_changed") is not False
        or terrain_ci_change.get("terrain_core_changed") is not False
        or terrain_ci_change.get("terrain_test_changed") is not False
        or terrain_ci_change.get("portable_text_serialization") != "UTF-8 with LF newlines"
        or dem_terrain_ci_correction.get("hash_portability", {}).get("failed_run_id") != 33819677224
        or dem_terrain_ci_correction.get("hash_portability", {}).get("precommit_windows_sha256") != "cc092fc6ce7c1ae9e6db24f4c24da97311b0e84e77eb55aedb0cbea988afe06b"
        or dem_terrain_ci_correction.get("hash_portability", {}).get("committed_lf_blob_sha256") != "3127f09fb5dccf794d347e92abf59445941fbf7c34d52d82cb17dbae7e44914b"
        or passing_terrain_ci.get("run_id") != 33819458096
        or passing_terrain_ci.get("commit") != "d52ee5a0f1ad51062ccfe3426a759cea91fcdbcb"
        or passing_terrain_ci.get("conclusion") != "success"
        or passing_terrain_ci.get("repository_required_file_count_before_correction_receipt") != 199
        or passing_terrain_ci.get("full_repository_test_count") != 190
        or dem_terrain_ci_correction.get("assertions") != expected_dem_terrain_ci_assertions
    ):
        fail("DEM terrain-quality CI dependency correction differs")
    expected_terrain_attempt_001_assertions = {
        "dem_source_opened": False,
        "dem_bytes_hashed_by_attempt": False,
        "dem_pixels_read": False,
        "terrain_metrics_observed": False,
        "derived_output_created": False,
        "source_custody_mutated": False,
        "network_requests_performed": False,
        "vertical_transformation_applied": False,
        "sentinel_processing_executed": False,
        "scientific_result_established": False,
        "authority_created": False,
        "retry_in_attempt_001_authorized": False,
    }
    if (
        dem_terrain_attempt_001_failure.get("receipt_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-ATTEMPT-001-FAILURE"
        or dem_terrain_attempt_001_failure.get("status") != "failed_source_path_resolution_before_source_open"
        or dem_terrain_attempt_001_failure.get("bindings", {}).get("contract_sha256") != sha256("config/qa/dem-terrain-quality-contract.json")
        or dem_terrain_attempt_001_failure.get("bindings", {}).get("implementation_sha256") != sha256("scripts/inspect_m2_dem_terrain_quality_arcgis.py")
        or dem_terrain_attempt_001_failure.get("failure", {}).get("stage") != "source_path_resolution_before_source_open"
        or dem_terrain_attempt_001_failure.get("failure", {}).get("classification") != "wrapper_path_binding_failure_not_data_fitness"
        or dem_terrain_attempt_001_failure.get("post_failure_observation", {}).get("attempt_output_root_exists") is not False
        or dem_terrain_attempt_001_failure.get("post_failure_observation", {}).get("candidate_receipt_exists") is not False
        or dem_terrain_attempt_001_failure.get("assertions") != expected_terrain_attempt_001_assertions
    ):
        fail("DEM terrain-quality attempt-001 failure receipt differs")
    corrected_terrain_bindings = dem_terrain_attempt_002_contract.get("bindings", {})
    for key, value in dem_terrain_contract.get("bindings", {}).items():
        if corrected_terrain_bindings.get(key) != value:
            fail(f"DEM terrain-quality attempt-002 changed base binding {key}")
    if (
        dem_terrain_attempt_002_contract.get("contract_id") != dem_terrain_contract.get("contract_id")
        or dem_terrain_attempt_002_contract.get("status") != "predeclared_not_executed"
        or dem_terrain_attempt_002_contract.get("control_revision") != 2
        or dem_terrain_attempt_002_contract.get("correction_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-PATH-CORRECTION-001"
        or dem_terrain_attempt_002_contract.get("attempt_id") != "attempt-002"
        or corrected_terrain_bindings.get("base_contract_ref") != "config/qa/dem-terrain-quality-contract.json"
        or corrected_terrain_bindings.get("base_contract_sha256") != sha256("config/qa/dem-terrain-quality-contract.json")
        or corrected_terrain_bindings.get("failed_attempt_ref") != "records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json"
        or corrected_terrain_bindings.get("failed_attempt_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json")
        or dem_terrain_attempt_002_contract.get("inputs", {}).get("external_root") != r"C:\Projects\Active\nepal-2026-before-after-map-data\custody"
        or dem_terrain_attempt_002_contract.get("inputs", {}).get("assets") != dem_terrain_contract.get("inputs", {}).get("assets")
        or dem_terrain_attempt_002_contract.get("seam_pairs") != dem_terrain_contract.get("seam_pairs")
        or dem_terrain_attempt_002_contract.get("predeclared_metrics") != dem_terrain_contract.get("predeclared_metrics")
        or dem_terrain_attempt_002_contract.get("thresholds") != dem_terrain_contract.get("thresholds")
        or dem_terrain_attempt_002_contract.get("visual_review") != dem_terrain_contract.get("visual_review")
        or dem_terrain_attempt_002_contract.get("decision_policy") != dem_terrain_contract.get("decision_policy")
        or dem_terrain_attempt_002_contract.get("output_boundary") != dem_terrain_contract.get("output_boundary")
        or dem_terrain_attempt_002_contract.get("authority") != dem_terrain_contract.get("authority")
    ):
        fail("DEM terrain-quality attempt-002 correction changed a protected control")
    base_terrain_processing = dict(dem_terrain_contract.get("processing", {}))
    corrected_terrain_processing = dict(dem_terrain_attempt_002_contract.get("processing", {}))
    if corrected_terrain_processing.pop("output_root", None) != r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-002":
        fail("DEM terrain-quality attempt-002 output root differs")
    base_terrain_processing.pop("output_root", None)
    if corrected_terrain_processing != base_terrain_processing:
        fail("DEM terrain-quality attempt-002 processing method changed")
    expected_attempt_002_correction = {
        "scope": "path_binding_and_exclusive_attempt_only",
        "prior_declared_external_root": r"C:\Projects\Active\nepal-2026-before-after-map-data",
        "corrected_external_root": r"C:\Projects\Active\nepal-2026-before-after-map-data\custody",
        "custody_relative_paths_changed": False,
        "source_identities_changed": False,
        "source_hashes_changed": False,
        "source_sizes_changed": False,
        "seam_pairs_changed": False,
        "metrics_changed": False,
        "thresholds_changed": False,
        "processing_method_changed": False,
        "vertical_transformation_changed": False,
        "prior_output_path_reused": False,
        "corrected_output_root": r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-002",
    }
    if dem_terrain_attempt_002_contract.get("correction") != expected_attempt_002_correction:
        fail("DEM terrain-quality attempt-002 correction boundary differs")
    expected_attempt_002_readiness_bindings = {
        "base_contract_ref": "config/qa/dem-terrain-quality-contract.json",
        "base_contract_sha256": sha256("config/qa/dem-terrain-quality-contract.json"),
        "corrected_contract_ref": "config/qa/dem-terrain-quality-contract-attempt-002.json",
        "corrected_contract_sha256": sha256("config/qa/dem-terrain-quality-contract-attempt-002.json"),
        "failed_attempt_ref": "records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json",
        "failed_attempt_sha256": sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json"),
        "implementation_ref": "scripts/inspect_m2_dem_terrain_quality_arcgis.py",
        "implementation_sha256": sha256("scripts/inspect_m2_dem_terrain_quality_arcgis.py"),
        "core_ref": "scripts/dem_terrain_quality_core.py",
        "core_sha256": sha256("scripts/dem_terrain_quality_core.py"),
        "test_ref": "tests/test_dem_terrain_quality_core.py",
        "test_sha256": sha256("tests/test_dem_terrain_quality_core.py"),
    }
    expected_attempt_002_assertions = {
        "attempt_001_failure_preserved": True,
        "attempt_001_path_reused": False,
        "custody_root_segment_corrected": True,
        "exact_source_identities_unchanged": True,
        "exact_source_hashes_unchanged": True,
        "exact_source_sizes_unchanged": True,
        "seam_pairs_unchanged": True,
        "metrics_unchanged": True,
        "thresholds_unchanged": True,
        "processing_method_unchanged": True,
        "vertical_transformation_selected": False,
        "real_dem_metrics_observed_by_correction": False,
        "derived_outputs_created_by_correction": False,
        "source_custody_mutated": False,
        "network_requests_performed": False,
        "sentinel_processing_executed": False,
        "scientific_result_established": False,
        "authority_created": False,
    }
    if (
        dem_terrain_attempt_002_readiness.get("readiness_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-ATTEMPT-002-READINESS-001"
        or dem_terrain_attempt_002_readiness.get("status") != "pass_path_only_correction_predeclared_real_execution_not_started"
        or dem_terrain_attempt_002_readiness.get("bindings") != expected_attempt_002_readiness_bindings
        or dem_terrain_attempt_002_readiness.get("validation", {}).get("focused_test_count") != 5
        or dem_terrain_attempt_002_readiness.get("validation", {}).get("full_repository_test_count") != 190
        or dem_terrain_attempt_002_readiness.get("validation", {}).get("repository_required_file_count_after_integration") != 203
        or dem_terrain_attempt_002_readiness.get("assertions") != expected_attempt_002_assertions
    ):
        fail("DEM terrain-quality attempt-002 readiness differs")
    expected_terrain_attempt_002_assertions = {
        "all_four_source_bytes_opened_and_read": True,
        "source_custody_unchanged_before_failure": True,
        "source_custody_independently_reverified_after_failure": True,
        "terrain_metrics_computed_transiently": True,
        "terrain_metrics_persisted": False,
        "derived_output_created": True,
        "manifest_created": False,
        "candidate_receipt_created": False,
        "visual_review_completed": False,
        "terrain_quality_result_established": False,
        "network_requests_performed": False,
        "vertical_transformation_applied": False,
        "sentinel_processing_executed": False,
        "scientific_result_established": False,
        "authority_created": False,
        "retry_in_attempt_002_authorized": False,
    }
    expected_attempt_002_source_reverification = [
        {"source_id": item["source_id"], "size_bytes": item["size_bytes"], "sha256": item["sha256"]}
        for item in terrain_assets
    ]
    attempt_002_outputs = dem_terrain_attempt_002_failure.get("post_failure_output", {})
    if (
        dem_terrain_attempt_002_failure.get("receipt_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-ATTEMPT-002-FAILURE"
        or dem_terrain_attempt_002_failure.get("status") != "failed_transient_arcgis_lock_during_output_inventory"
        or dem_terrain_attempt_002_failure.get("bindings", {}).get("contract_sha256") != sha256("config/qa/dem-terrain-quality-contract-attempt-002.json")
        or dem_terrain_attempt_002_failure.get("bindings", {}).get("implementation_sha256") != sha256("scripts/inspect_m2_dem_terrain_quality_arcgis.py")
        or dem_terrain_attempt_002_failure.get("failure", {}).get("stage") != "stable_output_inventory_before_manifest_or_receipt"
        or dem_terrain_attempt_002_failure.get("failure", {}).get("classification") != "wrapper_transient_lock_inventory_failure_not_data_fitness"
        or attempt_002_outputs.get("attempt_output_root_exists") is not True
        or attempt_002_outputs.get("candidate_receipt_exists") is not False
        or attempt_002_outputs.get("transient_lock_present_after_process_exit") is not False
        or attempt_002_outputs.get("stable_file_count") != 189
        or attempt_002_outputs.get("stable_total_bytes") != 520653986
        or attempt_002_outputs.get("stable_inventory_sha256") != "986ad7fb2f71e496fcd0bc323712f09cf0a120ed6ba1c4b6f2793aae0dea3d91"
        or dem_terrain_attempt_002_failure.get("source_reverification_after_failure") != expected_attempt_002_source_reverification
        or dem_terrain_attempt_002_failure.get("assertions") != expected_terrain_attempt_002_assertions
    ):
        fail("DEM terrain-quality attempt-002 failure receipt differs")
    attempt_003_bindings = dem_terrain_attempt_003_contract.get("bindings", {})
    for key, value in corrected_terrain_bindings.items():
        if key not in {"implementation_ref", "implementation_sha256"} and attempt_003_bindings.get(key) != value:
            fail(f"DEM terrain-quality attempt-003 changed prior binding {key}")
    if (
        dem_terrain_attempt_003_contract.get("contract_id") != dem_terrain_contract.get("contract_id")
        or dem_terrain_attempt_003_contract.get("status") != "predeclared_not_executed"
        or dem_terrain_attempt_003_contract.get("control_revision") != 3
        or dem_terrain_attempt_003_contract.get("correction_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-LOCK-INVENTORY-CORRECTION-001"
        or dem_terrain_attempt_003_contract.get("attempt_id") != "attempt-003"
        or attempt_003_bindings.get("implementation_ref") != "scripts/inspect_m2_dem_terrain_quality_arcgis_attempt_003.py"
        or attempt_003_bindings.get("implementation_sha256") != sha256("scripts/inspect_m2_dem_terrain_quality_arcgis_attempt_003.py")
        or attempt_003_bindings.get("prior_contract_ref") != "config/qa/dem-terrain-quality-contract-attempt-002.json"
        or attempt_003_bindings.get("prior_contract_sha256") != sha256("config/qa/dem-terrain-quality-contract-attempt-002.json")
        or attempt_003_bindings.get("failed_attempt_002_ref") != "records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json"
        or attempt_003_bindings.get("failed_attempt_002_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json")
        or dem_terrain_attempt_003_contract.get("inputs") != dem_terrain_attempt_002_contract.get("inputs")
        or dem_terrain_attempt_003_contract.get("seam_pairs") != dem_terrain_attempt_002_contract.get("seam_pairs")
        or dem_terrain_attempt_003_contract.get("predeclared_metrics") != dem_terrain_attempt_002_contract.get("predeclared_metrics")
        or dem_terrain_attempt_003_contract.get("thresholds") != dem_terrain_attempt_002_contract.get("thresholds")
        or dem_terrain_attempt_003_contract.get("visual_review") != dem_terrain_attempt_002_contract.get("visual_review")
        or dem_terrain_attempt_003_contract.get("decision_policy") != dem_terrain_attempt_002_contract.get("decision_policy")
        or dem_terrain_attempt_003_contract.get("output_boundary") != dem_terrain_attempt_002_contract.get("output_boundary")
        or dem_terrain_attempt_003_contract.get("authority") != dem_terrain_attempt_002_contract.get("authority")
    ):
        fail("DEM terrain-quality attempt-003 correction changed a protected control")
    attempt_002_processing = dict(dem_terrain_attempt_002_contract.get("processing", {}))
    attempt_003_processing = dict(dem_terrain_attempt_003_contract.get("processing", {}))
    if attempt_003_processing.pop("output_root", None) != r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-003":
        fail("DEM terrain-quality attempt-003 output root differs")
    attempt_002_processing.pop("output_root", None)
    if attempt_003_processing != attempt_002_processing:
        fail("DEM terrain-quality attempt-003 raster processing changed")
    expected_attempt_003_correction = {
        "scope": "stable_inventory_lock_exclusion_and_exclusive_attempt_only",
        "prior_output_root": r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-002",
        "corrected_output_root": r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-003",
        "transient_arcgis_lock_files_excluded_from_manifest": True,
        "stable_output_files_still_hashed": True,
        "prior_output_path_reused": False,
        "source_identities_changed": False,
        "source_paths_changed": False,
        "source_hashes_changed": False,
        "source_sizes_changed": False,
        "seam_pairs_changed": False,
        "metrics_changed": False,
        "thresholds_changed": False,
        "raster_processing_method_changed": False,
        "vertical_transformation_changed": False,
    }
    if dem_terrain_attempt_003_contract.get("correction") != expected_attempt_003_correction:
        fail("DEM terrain-quality attempt-003 correction boundary differs")
    expected_attempt_003_readiness_bindings = {
        "original_contract_ref": "config/qa/dem-terrain-quality-contract.json",
        "original_contract_sha256": sha256("config/qa/dem-terrain-quality-contract.json"),
        "prior_contract_ref": "config/qa/dem-terrain-quality-contract-attempt-002.json",
        "prior_contract_sha256": sha256("config/qa/dem-terrain-quality-contract-attempt-002.json"),
        "corrected_contract_ref": "config/qa/dem-terrain-quality-contract-attempt-003.json",
        "corrected_contract_sha256": sha256("config/qa/dem-terrain-quality-contract-attempt-003.json"),
        "failed_attempt_002_ref": "records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json",
        "failed_attempt_002_sha256": sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json"),
        "implementation_ref": "scripts/inspect_m2_dem_terrain_quality_arcgis_attempt_003.py",
        "implementation_sha256": sha256("scripts/inspect_m2_dem_terrain_quality_arcgis_attempt_003.py"),
        "core_ref": "scripts/dem_terrain_quality_core.py",
        "core_sha256": sha256("scripts/dem_terrain_quality_core.py"),
        "test_ref": "tests/test_dem_terrain_quality_core.py",
        "test_sha256": sha256("tests/test_dem_terrain_quality_core.py"),
    }
    expected_attempt_003_assertions = {
        "attempt_002_failure_preserved": True,
        "attempt_002_output_preserved": True,
        "attempt_002_path_reused": False,
        "transient_lock_files_excluded_from_stable_manifest": True,
        "stable_output_files_remain_hashed": True,
        "exact_source_identities_unchanged": True,
        "exact_source_paths_unchanged": True,
        "exact_source_hashes_unchanged": True,
        "exact_source_sizes_unchanged": True,
        "seam_pairs_unchanged": True,
        "metrics_unchanged": True,
        "thresholds_unchanged": True,
        "raster_processing_method_unchanged": True,
        "vertical_transformation_selected": False,
        "real_dem_metrics_observed_by_correction": False,
        "attempt_003_outputs_created_by_correction": False,
        "source_custody_mutated": False,
        "network_requests_performed": False,
        "sentinel_processing_executed": False,
        "scientific_result_established": False,
        "authority_created": False,
    }
    if (
        dem_terrain_attempt_003_readiness.get("readiness_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-ATTEMPT-003-READINESS-001"
        or dem_terrain_attempt_003_readiness.get("status") != "pass_lock_exclusion_correction_predeclared_real_execution_not_started"
        or dem_terrain_attempt_003_readiness.get("bindings") != expected_attempt_003_readiness_bindings
        or dem_terrain_attempt_003_readiness.get("validation", {}).get("focused_test_count") != 5
        or dem_terrain_attempt_003_readiness.get("validation", {}).get("full_repository_test_count") != 190
        or dem_terrain_attempt_003_readiness.get("validation", {}).get("repository_required_file_count_after_integration") != 207
        or dem_terrain_attempt_003_readiness.get("assertions") != expected_attempt_003_assertions
    ):
        fail("DEM terrain-quality attempt-003 readiness differs")
    terrain_result_bindings = dem_terrain_result.get("bindings", {})
    expected_terrain_result_claim_boundary = {
        "source_byte_identity_reverified": True,
        "source_custody_unchanged": True,
        "stable_output_manifest_reconciled": True,
        "terrain_quantitative_screen_passed": True,
        "terrain_visual_screen_passed": True,
        "terrain_accuracy_against_ground_or_alternate_dem_established": False,
        "vertical_datum_route_established": False,
        "human_or_independent_expert_terrain_review_established": False,
        "sentinel_processing_executed": False,
        "satellite_change_established": False,
        "scientific_result_established": False,
        "authority_created": False,
    }
    if (
        dem_terrain_result.get("receipt_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-001"
        or dem_terrain_result.get("status") != "pass_terrain_qa_only_vertical_datum_and_independent_accuracy_deferred"
        or dem_terrain_result.get("quantitative_status") != "pass"
        or terrain_result_bindings.get("published_control_commit") != "439a750e2a4fb6318f4da063fa48eed748beddec"
        or terrain_result_bindings.get("contract_ref") != "config/qa/dem-terrain-quality-contract-attempt-003.json"
        or terrain_result_bindings.get("contract_sha256") != sha256("config/qa/dem-terrain-quality-contract-attempt-003.json")
        or terrain_result_bindings.get("implementation_sha256") != sha256("scripts/inspect_m2_dem_terrain_quality_arcgis_attempt_003.py")
        or terrain_result_bindings.get("core_sha256") != sha256("scripts/dem_terrain_quality_core.py")
        or terrain_result_bindings.get("active_intake_sha256") != sha256("contracts/m2-dem-intake.json")
        or terrain_result_bindings.get("dem_verification_summary_sha256") != sha256("records/acquisition/dem-verification-summary.json")
        or terrain_result_bindings.get("approved_aoi_sha256") != sha256("config/aoi/approved-study-areas-epsg32645.json")
        or terrain_result_bindings.get("authority_sha256") != sha256("records/source-gates/m2-dem-amendment-approval.json")
        or terrain_result_bindings.get("candidate_receipt_sha256") != "7fb0017e7b338ad86015b17bad78c7d4c86274718b367e2fcf50c86a2caf0f88"
        or terrain_result_bindings.get("failed_attempt_001_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json")
        or terrain_result_bindings.get("failed_attempt_002_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json")
    ):
        fail("DEM terrain-quality result identity or binding differs")
    if (
        len(dem_terrain_result.get("tile_results", [])) != 4
        or any(item.get("evaluation", {}).get("status") != "pass" for item in dem_terrain_result["tile_results"])
        or [item.get("source_id") for item in dem_terrain_result["tile_results"]] != expected_dem_source_order
        or len(dem_terrain_result.get("seam_results", [])) != 4
        or any(item.get("evaluation", {}).get("status") != "pass" for item in dem_terrain_result["seam_results"])
        or dem_terrain_result.get("slope_evaluation", {}).get("status") != "pass"
        or dem_terrain_result.get("source_inventory_before") != dem_terrain_result.get("source_inventory_after")
        or dem_terrain_result.get("projection_check") != {
            "wkid": 32645,
            "mean_cell_width_m": 30.0,
            "mean_cell_height_m": 30.0,
            "vertical_transformation_applied": False,
            "elevation_value_semantics": "EGM2008 orthometric metres",
        }
    ):
        fail("DEM terrain-quality metrics, source identity, or projection differs")
    terrain_manifest_check = dem_terrain_result.get("output_manifest_reconciliation", {})
    if terrain_manifest_check != {
        "status": "pass",
        "verified_at_utc": dem_terrain_result.get("recorded_at_utc"),
        "manifest_sha256": "6baf1ec47f4bc27c9dc2ab3501637690d717673e63d9e0f5036e1b2dc2ed1620",
        "listed_stable_file_count": 189,
        "post_exit_stable_file_count": 189,
        "stable_total_bytes": 520668653,
        "missing_file_count": 0,
        "unexpected_file_count": 0,
        "size_mismatch_count": 0,
        "sha256_mismatch_count": 0,
        "post_exit_lock_file_count": 0,
        "source_inventory_before_equals_after": True,
        "source_identities_independently_reverified": True,
    }:
        fail("DEM terrain-quality stable-output reconciliation differs")
    expected_terrain_key_hashes = {
        "arcgis_project": "08829c97eeb831758573fbfc0146f09e5d1a39d342f313f5adab4ba2c6facc83",
        "png": "39c63525171ae7cd24b540577079467c7efbaedb4aae959086e3f4d1a38ad811",
        "pdf": "139e4a4f0f5a02018c824cbfc2f85ddcf3b1d1c4b8d477dd7936efc4d0f74d0b",
    }
    if any(dem_terrain_result.get("key_exports", {}).get(key, {}).get("sha256") != value for key, value in expected_terrain_key_hashes.items()):
        fail("DEM terrain-quality key export identity differs")
    if (
        dem_terrain_result.get("visual_review", {}).get("status") != "pass"
        or dem_terrain_result.get("visual_review", {}).get("reviewer_role") != "model_visual_inspection"
        or any(item.get("status") != "pass" for item in dem_terrain_result.get("visual_review", {}).get("criteria", []))
        or dem_terrain_result.get("claim_boundary") != expected_terrain_result_claim_boundary
        or dem_terrain_result.get("next_checkpoint") != "M2-DEM-VERTICAL-DATUM-REVIEW"
    ):
        fail("DEM terrain-quality visual result or claim boundary differs")
    if (
        dem_terrain_audit_input.get("audit_id") != "nepal-m2-dem-terrain-readiness-001"
        or dem_terrain_audit_input.get("candidate_manifest_sha256") != terrain_manifest_check.get("manifest_sha256")
        or dem_terrain_audit_input.get("next_step_authority", {}).get("mode") != "inherited"
        or dem_terrain_audit_input.get("next_step_authority", {}).get("authority_ref") != "records/source-gates/m2-dem-amendment-approval.json"
        or dem_terrain_audit_decision.get("audit_id") != dem_terrain_audit_input.get("audit_id")
        or dem_terrain_audit_decision.get("candidate_id") != dem_terrain_audit_input.get("candidate_id")
        or dem_terrain_audit_decision.get("candidate_manifest_sha256") != dem_terrain_audit_input.get("candidate_manifest_sha256")
        or dem_terrain_audit_decision.get("audit_input_sha256") != sha256("records/readiness/m2-dem-terrain-readiness-input.json")
        or dem_terrain_audit_decision.get("decision") != "defer"
        or dem_terrain_audit_decision.get("blocking_required_gate_ids") != []
        or dem_terrain_audit_decision.get("deferred_required_gate_ids") != [
            "evaluation-design",
            "human-review",
            "radar-input-fitness",
            "uncertainty-and-exclusions",
        ]
        or dem_terrain_audit_decision.get("training_authority") != "inherited"
        or dem_terrain_audit_decision.get("authorized_next_actions") != []
        or dem_terrain_audit_decision.get("training_authorized") is not False
        or dem_terrain_audit_decision.get("training_authorized_by_this_audit") is not False
    ):
        fail("DEM terrain readiness audit or non-authorizing defer boundary differs")
    if (
        dem_terrain_review_proposal.get("proposal_id") != "NEPAL-M2-DEM-TERRAIN-RESULT-REVIEW-001"
        or dem_terrain_review_proposal.get("status") != "review_ready_no_human_decision"
        or dem_terrain_review_proposal.get("authority", {}).get("authority_sha256") != sha256("records/source-gates/m2-dem-amendment-approval.json")
        or dem_terrain_review_proposal.get("authority", {}).get("review_required_by_sha256") != sha256("records/readiness/m2-dem-terrain-readiness-decision.json")
        or dem_terrain_review_proposal.get("authority", {}).get("this_proposal_creates_authority") is not False
        or dem_terrain_review_proposal.get("candidate", {}).get("receipt_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality.json")
        or dem_terrain_review_proposal.get("candidate", {}).get("external_manifest_sha256") != dem_terrain_result.get("output_manifest_reconciliation", {}).get("manifest_sha256")
        or dem_terrain_review_proposal.get("candidate", {}).get("stable_file_count") != 189
        or dem_terrain_review_proposal.get("candidate", {}).get("vertical_transformation_applied") is not False
        or dem_terrain_review_proposal.get("decision_request", {}).get("allowed_decisions") != ["approve", "revise", "defer"]
    ):
        fail("DEM terrain-result review proposal differs")
    terrain_external_by_id = {
        item.get("artifact_id"): item
        for item in dem_terrain_review_proposal.get("external_review_artifacts", [])
        if isinstance(item, dict)
    }
    if (
        set(terrain_external_by_id) != {"arcgis-project", "pdf-map", "png-map", "derived-manifest"}
        or terrain_external_by_id["arcgis-project"].get("sha256") != dem_terrain_result.get("key_exports", {}).get("arcgis_project", {}).get("sha256")
        or terrain_external_by_id["pdf-map"].get("sha256") != dem_terrain_result.get("key_exports", {}).get("pdf", {}).get("sha256")
        or terrain_external_by_id["png-map"].get("sha256") != dem_terrain_result.get("key_exports", {}).get("png", {}).get("sha256")
        or terrain_external_by_id["derived-manifest"].get("sha256") != dem_terrain_result.get("output_manifest_reconciliation", {}).get("manifest_sha256")
    ):
        fail("DEM terrain-result external review identities differ")
    expected_terrain_review_surface_bindings = {
        "surface_sha256": sha256("docs/assets/m2-dem-terrain-result-review.png"),
        "proposal_sha256": sha256("contracts/m2-dem-terrain-result-review-proposal.json"),
        "terrain_result_sha256": sha256("records/surface-receipts/m2-dem-terrain-quality.json"),
        "readiness_decision_sha256": sha256("records/readiness/m2-dem-terrain-readiness-decision.json"),
        "instructions_sha256": sha256("docs/M2_DEM_TERRAIN_RESULT_REVIEW.md"),
        "renderer_sha256": sha256("scripts/render_m2_dem_terrain_result_review.py"),
    }
    if (
        dem_terrain_review_surface.get("receipt_id") != "M2-DEM-TERRAIN-RESULT-REVIEW-SURFACE-001"
        or dem_terrain_review_surface.get("status") != "pass_text_only_review_surface_no_human_decision"
        or any(dem_terrain_review_surface.get(key) != value for key, value in expected_terrain_review_surface_bindings.items())
        or dem_terrain_review_surface.get("dimensions_pixels") != {"width": 1800, "height": 1680}
        or dem_terrain_review_surface.get("checks", {}).get("visual_inspection") != "pass"
        or dem_terrain_review_surface.get("checks", {}).get("dem_derived_map_pixels_embedded") is not False
        or dem_terrain_review_surface.get("blank_state_verified") is not True
        or dem_terrain_review_surface.get("completion_controls_verified") is not True
        or dem_terrain_review_surface.get("export_verified") is not True
        or dem_terrain_review_surface.get("human_decision_count") != 0
    ):
        fail("DEM terrain-result review surface receipt differs")
    terrain_review_artifacts = dem_terrain_review_bundle.get("artifacts", [])
    if (
        dem_terrain_review_bundle.get("bundle_id") != "m2-dem-terrain-result-review-bundle-001"
        or dem_terrain_review_bundle.get("review_id") != "m2-dem-terrain-result-review-001"
        or dem_terrain_review_bundle.get("candidate_identity") != "M2-DEM-TERRAIN-RESULT-SHA256:" + sha256("records/surface-receipts/m2-dem-terrain-quality.json")
        or len(terrain_review_artifacts) != 7
    ):
        fail("DEM terrain-result review bundle identity differs")
    for artifact in terrain_review_artifacts:
        if artifact.get("sha256") != sha256(artifact.get("path", "")):
            fail(f"DEM terrain-result review artifact differs: {artifact.get('artifact_id')}")
        for render_receipt in artifact.get("render_receipts", []):
            if render_receipt.get("sha256") != sha256(render_receipt.get("path", "")):
                fail(f"DEM terrain-result review render receipt differs: {artifact.get('artifact_id')}")
    if (
        dem_terrain_review_contract.get("review_id") != dem_terrain_review_bundle.get("review_id")
        or dem_terrain_review_contract.get("review_bundle", {}).get("manifest_sha256") != sha256("reviews/m2-dem-terrain-result/review-bundle.json")
        or dem_terrain_review_contract.get("review_bundle", {}).get("candidate_identity") != dem_terrain_review_bundle.get("candidate_identity")
        or dem_terrain_review_contract.get("review_bundle", {}).get("rendered_surface_verified") is not True
        or dem_terrain_review_contract.get("workflow_authority", {}).get("review_required") is not True
        or dem_terrain_review_contract.get("workflow_authority", {}).get("lock_authorized") is not True
        or dem_terrain_review_contract.get("workflow_authority", {}).get("reconcile_authorized") is not True
        or dem_terrain_review_contract.get("allowed_decisions") != ["approve", "revise", "defer"]
        or dem_terrain_review_contract.get("items") != [{
            "item_id": "M2-DEM-TERRAIN-SCREEN-RESULT-001",
            "evidence_sha256": sha256("reviews/m2-dem-terrain-result/review-bundle.json"),
        }]
    ):
        fail("DEM terrain-result review contract differs")
    if dem_terrain_review_blank != {
        "response_schema_version": "nepal-m2-dem-terrain-result-response-v1",
        "review_id": "m2-dem-terrain-result-review-001",
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{
            "item_id": "M2-DEM-TERRAIN-SCREEN-RESULT-001",
            "evidence_sha256": sha256("reviews/m2-dem-terrain-result/review-bundle.json"),
            "decision": None,
            "notes": "",
        }],
    }:
        fail("DEM terrain-result blank response differs or contains a human decision")
    expected_dem_acquire_status = "complete" if dem_state_counts["promoted"] == 4 and not dem_state_counts["failed"] else "ready"
    expected_dem_verify_status = "complete" if dem_all_geotiff_verified else ("ready" if expected_dem_acquire_status == "complete" else "planned")
    for unit_id, expected_status in (
        ("M2-DEM-AMEND", "complete"),
        ("M2-DEM-PREFLIGHT", "complete"),
        ("M2-DEM-ACQUIRE", expected_dem_acquire_status),
        ("M2-DEM-VERIFY", expected_dem_verify_status),
        ("M2-ORBIT-AMEND", "complete"),
        ("M2-ORBIT-PREFLIGHT", "complete"),
        ("M2-ORBIT-ACQUIRE", "deferred"),
        ("M2-ORBIT-VERIFY", "planned"),
        ("M2-ORBIT-APPLY", "planned"),
        ("M2-RADAR-INPUT-LABEL-AMEND", "complete"),
    ):
        if active_m2_units.get(unit_id, {}).get("status") != expected_status:
            fail(f"active M2 unit {unit_id} status differs")
    if set(active_m2_units["M2-BASELINE"].get("depends_on", [])) != {"M2-VERIFY", "M2-DEM-VERIFY", "M2-ORBIT-APPLY"}:
        fail("M2 baseline does not preserve Sentinel, DEM, and orbit dependencies")
    if dem_activation_receipt.get("status") != "pass_exact_dem_amendment_activated_preflight_pending":
        fail("M2 DEM activation receipt status differs")
    expected_historical_dem_activation_bindings = {
        "reconciliation_ref": "records/source-gates/m2-dem-amendment-review-reconciliation.json",
        "reconciliation_sha256": "9d72c9786440da0c9149340cd69361b12e55f0d7dff88972bfd02ee0da5460e1",
        "approval_ref": "records/source-gates/m2-dem-amendment-approval.json",
        "approval_sha256": "6d1fc7e05854bc149ace177d89e84a7651cc049efd530cab650a9464222769d0",
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256": "0fa00a4be01d3caddac28088d2d3d714040d1258b33497ebee50cbb0b8b3b5b6",
        "active_verification_ref": "contracts/m2-dem-offline-verification.json",
        "active_verification_sha256": "755bdb1fd1916d68289f5266912f8bb7f25462b512ce7cfc27a49feb44bcef42",
        "active_milestone_ref": "contracts/milestone-002.json",
        "active_milestone_sha256": "fc764ba8513c05e518096e8864ba0ec49507ca924f2474637adccef31275a6cf",
        "project_profile_ref": "records/project-control-profile.json",
        "project_profile_sha256": "dd07dec7c68fbd9e486ad96e1a34dbd66266409609db05419a6eb78d723bc844",
        "long_term_goal_ref": "records/long-term-goal.json",
        "long_term_goal_sha256": "81f5b742b8aa3e829253317faa9c6017c8c93a6deb1d10a3f6cb96c7b55c44e8",
        "activation_script_ref": "scripts/activate_m2_dem_amendment.py",
        "activation_script_sha256": "a4cc4f86b0beb81f151ccdc0bc4a4ab5d674823d7c7a5879f0e223efcd36d256",
    }
    if dem_activation_receipt.get("bindings") != expected_historical_dem_activation_bindings:
        fail("M2 DEM activation receipt no longer preserves its published activation bindings")
    activation_assertions = dem_activation_receipt.get("assertions", {})
    if activation_assertions.get("exact_license_accepted") is not True or activation_assertions.get("authorized_dem_tile_count") != 4:
        fail("M2 DEM activation receipt does not preserve exact approved scope")
    if any(activation_assertions.get(key) is not False for key in ("network_requests_performed", "dem_payload_bytes_requested", "dem_pixels_examined", "scientific_result_established")):
        fail("M2 DEM activation receipt invents preflight, payload, pixel, or science evidence")
    if dem_live_source_gate.get("decision", {}).get("status") != "ready" or dem_live_source_gate.get("authority", {}).get("authority_ref") != "records/source-gates/m2-dem-amendment-approval.json":
        fail("M2 DEM live source gate is not ready under the exact amendment")
    if len(dem_live_source_gate.get("sources", [])) != 4:
        fail("M2 DEM live source gate must contain four exact sources")
    for source in dem_live_source_gate["sources"]:
        criteria = source.get("criteria", [])
        if len(criteria) != 10 or any(item.get("status") != "pass" for item in criteria):
            fail("M2 DEM live source gate has an incomplete or non-passing criterion")
    if dem_preflight.get("status") != "pass_no_payload_no_external_mutation":
        fail("M2 DEM preflight status differs")
    if dem_preflight.get("source_gate") != {
        "ref": "records/source-gates/m2-dem-live-source-gate.json",
        "sha256": sha256("records/source-gates/m2-dem-live-source-gate.json"),
        "decision": "ready",
        "exact_tile_count": 4,
    }:
        fail("M2 DEM preflight source-gate binding differs")
    license_check = dem_preflight.get("license_check", {})
    if license_check.get("sha256") != "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd" or license_check.get("status") != "pass" or not all(license_check.get("checks", {}).values()):
        fail("M2 DEM fresh license check differs")
    expected_live_tiles = {
        record["source_id"]: (
            record["anonymous_head"]["content_length_bytes"],
            record["anonymous_head"]["etag"],
            record["anonymous_head"]["last_modified"],
        )
        for record in dem_manifest["records"]
    }
    if {item.get("source_id") for item in dem_preflight.get("tile_checks", [])} != set(expected_live_tiles):
        fail("M2 DEM preflight tile set differs")
    for item in dem_preflight["tile_checks"]:
        expected_size, expected_etag, expected_modified = expected_live_tiles[item["source_id"]]
        head = item.get("head", {})
        if (
            item.get("status") != "pass"
            or not all(item.get("stac_checks", {}).values())
            or not all(item.get("head_checks", {}).values())
            or head.get("content_length_bytes") != expected_size
            or head.get("etag") != expected_etag
            or head.get("last_modified") != expected_modified
            or head.get("response_body_bytes") != 0
        ):
            fail(f"M2 DEM preflight live identity differs for {item.get('source_id')}")
    preflight_mutations = dem_preflight.get("mutations_performed", {})
    if preflight_mutations != {"external_directory_created": False, "dem_payload_requested": False, "dem_payload_bytes_received": 0, "authentication": False, "account_or_terms_action": False}:
        fail("M2 DEM preflight invents a payload or external mutation")
    if dem_preflight.get("paths", {}).get("existing_destination_or_staging_paths") != [] or dem_preflight.get("paths", {}).get("case_insensitive_path_collision") is not False:
        fail("M2 DEM preflight did not preserve collision-free paths")
    if dem_preflight.get("storage", {}).get("status") != "pass" or dem_preflight.get("storage", {}).get("exact_tile_bytes") != 170302058:
        fail("M2 DEM preflight storage result differs")
    if dem_custody_receipt.get("status") != "created_and_verified_empty":
        fail("M2 DEM custody initialization status differs")
    if dem_custody_receipt.get("bindings") != {
        "preflight_ref": "records/acquisition/dem-preflight.json",
        "preflight_sha256": sha256("records/acquisition/dem-preflight.json"),
        "source_gate_ref": "records/source-gates/m2-dem-live-source-gate.json",
        "source_gate_sha256": sha256("records/source-gates/m2-dem-live-source-gate.json"),
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256_before_initialization": "0fa00a4be01d3caddac28088d2d3d714040d1258b33497ebee50cbb0b8b3b5b6",
    }:
        fail("M2 DEM custody initialization bindings differ")
    custody_verification = dem_custody_receipt.get("verification", {})
    if any(custody_verification.get(key) is not True for key in ("all_paths_exist", "all_paths_not_reparse_points", "external_root_outside_git")):
        fail("M2 DEM custody initialization path verification differs")
    if custody_verification.get("files_downloaded") != 0 or custody_verification.get("dem_payload_bytes_present") != 0 or custody_verification.get("authentication_performed") is not False:
        fail("M2 DEM custody initialization invents payload or authentication")
    dem_preflight_unit = active_m2_units["M2-DEM-PREFLIGHT"]
    dem_acquire_unit = active_m2_units["M2-DEM-ACQUIRE"]
    if dem_preflight_unit.get("outputs") != ["records/source-gates/m2-dem-live-source-gate.json", "records/acquisition/dem-preflight.json", "records/acquisition/dem-custody-initialization.json"] or dem_preflight_unit.get("disposition") != "pass":
        fail("M2 DEM preflight milestone evidence differs")
    if dem_acquire_unit.get("inputs") != ["records/source-gates/m2-dem-live-source-gate.json", "records/acquisition/dem-preflight.json", "records/acquisition/dem-custody-initialization.json", "contracts/m2-dem-intake.json"]:
        fail("M2 DEM acquisition inputs differ")
    if active_m2.get("handoff", {}).get("parallel_checkpoint") != expected_dem_checkpoint or active_m2.get("handoff", {}).get("parallel_next_action") != expected_dem_next_action:
        fail("active M2 DEM handoff differs from acquisition progress")
    if dem_transfer_readiness.get("status") != "pass_local_controls_no_network_or_payload" or dem_transfer_readiness.get("test_count") != 7:
        fail("M2 DEM transfer-runner readiness status differs")
    expected_historical_dem_transfer_bindings = {
        "approval_sha256": "6d1fc7e05854bc149ace177d89e84a7651cc049efd530cab650a9464222769d0",
        "preflight_sha256": "18ca15363d92f6f04d672ddb3e97fef33524c94bcb54915d83c82dae77af38f1",
        "intake_sha256": "2ae511c70303f15de590daf3eef4aac1e9dab1b7e0f85544c049ef69a60caa36",
        "runner_sha256": "2d4323754609853b5b350a9e81ecc4e66db2f1bcb91656e3ecaa36e6cf7b91b3",
        "shared_transfer_core_sha256": "a858756a063148800be418bb7329ba148bcdce71b7812abafee6f7c9c62d8da9",
        "test_sha256": "68432df023f64801709ea4d7c3cfde392d8f1875688c250680b3c229364a5764",
    }
    if any(dem_transfer_readiness.get("bindings", {}).get(key) != value for key, value in expected_historical_dem_transfer_bindings.items()):
        fail("M2 DEM transfer-runner readiness no longer preserves its published bindings")
    readiness_assertions = dem_transfer_readiness.get("assertions", {})
    if readiness_assertions.get("tests_passed") is not True or any(readiness_assertions.get(key) is not False for key in ("network_requests_performed", "dem_payload_bytes_requested", "active_intake_mutated", "external_custody_mutated", "scientific_result_established")):
        fail("M2 DEM transfer-runner readiness invents execution or scientific evidence")
    if dem_acquisition_summary.get("status") != "pass_exact_four_tile_acquisition" or dem_acquisition_summary.get("totals") != {"approved": 4, "promoted": 4, "failed": 0, "bytes": 170302058}:
        fail("M2 DEM acquisition summary status or totals differ")
    if [asset.get("source_id") for asset in dem_acquisition_summary.get("assets", [])] != expected_dem_source_order:
        fail("M2 DEM acquisition summary source order differs")
    for asset in dem_acquisition_summary["assets"]:
        for ref_key, hash_key in (("attempt_receipt_ref", "attempt_receipt_sha256"), ("checkpoint_receipt_ref", "checkpoint_receipt_sha256")):
            relative = asset.get(ref_key)
            if not isinstance(relative, str) or not (ROOT / relative).is_file() or asset.get(hash_key) != sha256(relative):
                fail(f"M2 DEM acquisition summary does not bind {ref_key} for {asset.get('source_id')}")
        if asset.get("anonymous_access") is not True or asset.get("credential_or_account_used") is not False:
            fail(f"M2 DEM acquisition summary access boundary differs for {asset.get('source_id')}")
    dem_summary_assertions = dem_acquisition_summary.get("assertions", {})
    if any(dem_summary_assertions.get(key) is not True for key in ("exact_approved_source_order_preserved", "all_attempts_terminal_succeeded", "all_promoted_bytes_locally_sha256_bound", "anonymous_access_only")):
        fail("M2 DEM acquisition summary does not establish its bounded transfer claims")
    if any(dem_summary_assertions.get(key) is not False for key in ("geotiff_readability_established", "valid_pixel_coverage_established", "vertical_datum_route_established", "radar_processing_executed", "scientific_result_established")):
        fail("M2 DEM acquisition summary overclaims raster or scientific evidence")
    expected_dem_portability_bindings = {
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256": "db4329c6b10492d2c6985be528c5dceca13585736ee9f82fbf96e7f190ba92fa",
        "acquisition_summary_ref": "records/acquisition/dem-acquisition-summary.json",
        "acquisition_summary_sha256": "db9b7694e40fc836020757fc2ba2879b29fff4eed3c299af9a977eeb8d494a86",
        "verification_summary_ref": "records/acquisition/dem-verification-summary.json",
        "verification_summary_sha256": "97f6a66daccd236decc6cdaac7035ca4cafb541ce7d82cecf08973ec6962f7ef",
        "reconciliation_script_ref": "scripts/reconcile_m2_dem_acquisition.py",
        "reconciliation_script_sha256": sha256("scripts/reconcile_m2_dem_acquisition.py"),
        "test_ref": "tests/test_m2_dem_acquisition_progress.py",
        "test_sha256": sha256("tests/test_m2_dem_acquisition_progress.py"),
    }
    if (
        dem_acquisition_portability.get("status") != "pass_portable_repository_receipt_validation_external_custody_separated"
        or dem_acquisition_portability.get("bindings") != expected_dem_portability_bindings
        or dem_acquisition_portability.get("validation") != {
            "focused_test_count": 6,
            "focused_test_status": "pass",
            "full_repository_test_count": 185,
            "full_repository_test_status": "pass",
            "repository_required_file_count": 192,
            "repository_validation_status": "pass",
            "portable_repository_receipt_validation": "pass",
            "generic_intake_contract_validator": "fail_retained_historical_attempt_identifier_case",
            "local_external_custody_reconciliation": {"status": "pass", "promoted_count": 4, "verified_bytes": 170302058},
        }
    ):
        fail("M2 DEM acquisition portability correction differs")
    if dem_acquisition_portability.get("assertions") != {
        "portable_repository_test_requires_external_custody_root": False,
        "repository_receipt_identity_revalidated": True,
        "production_reconciliation_verify_external_default": True,
        "local_external_custody_reverified": True,
        "failed_ci_run_preserved": True,
        "generic_intake_validator_failure_preserved": True,
        "historical_attempt_identifiers_rewritten": False,
        "tracked_project_controls_mutated_by_validation": False,
        "external_files_mutated": False,
        "network_requests_performed": False,
        "credential_values_read_or_recorded": False,
        "dem_pixels_processed": False,
        "vertical_datum_route_established": False,
        "radar_processing_executed": False,
        "scientific_result_established": False,
    }:
        fail("M2 DEM acquisition portability correction claim boundary differs")
    retained_dem_ci = dem_acquisition_portability.get("retained_validation_failures", [])
    if (
        len(retained_dem_ci) != 2
        or retained_dem_ci[0].get("run_id") != 33809208304
        or retained_dem_ci[0].get("status") != "failure"
        or retained_dem_ci[1].get("validator") != "intake-controlled-data/validate_intake_contract.py"
        or retained_dem_ci[1].get("status") != "failure"
        or len(retained_dem_ci[1].get("failed_fields", [])) != 4
    ):
        fail("M2 DEM acquisition portability correction does not retain its failed validation results")
    if sar_capability.get("status") != "pass_capability_only_dem_dependency_unresolved":
        fail("ArcGIS SAR capability receipt status differs")
    sar_checks = sar_capability.get("checks", {})
    if sar_checks.get("all_named_tools_available") is not True or sar_checks.get("processing_executed") is not False:
        fail("ArcGIS SAR capability receipt does not preserve capability-only semantics")
    if dem_intake_candidate.get("intake_id") != "nepal-m2-dem-intake-001" or len(dem_intake_candidate.get("assets", [])) != 4:
        fail("M2 DEM intake candidate identity or asset count differs")
    if dem_intake_candidate.get("extensions", {}).get("status") != "candidate_static_control_not_authorized":
        fail("M2 DEM intake must remain a non-authorizing static candidate")
    if dem_intake_candidate.get("extensions", {}).get("candidate_manifest_sha256") != sha256("records/source-gates/m2-dem-candidate-manifest.json"):
        fail("M2 DEM intake candidate does not bind the exact DEM manifest")
    dem_intake_assets = dem_intake_candidate.get("assets", [])
    if {item.get("extensions", {}).get("source_id") for item in dem_intake_assets} != {
        "M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"
    }:
        fail("M2 DEM intake candidate source set differs")
    if sum(item.get("expected", {}).get("size_bytes", 0) for item in dem_intake_assets) != 170302058:
        fail("M2 DEM intake candidate total byte count differs")
    if any(
        item.get("state") != "planned"
        or item.get("attempts") != []
        or item.get("expected", {}).get("sha256") is not None
        for item in dem_intake_assets
    ):
        fail("M2 DEM intake candidate invents authority, attempts, or upstream SHA-256")
    if dem_verification_candidate.get("verification_id") != "NEPAL-M2-DEM-OFFLINE-VERIFICATION-001":
        fail("M2 DEM offline verification identity differs")
    if dem_verification_candidate.get("status") != "candidate_static_control_not_authorized":
        fail("M2 DEM offline verification must remain a non-authorizing candidate")
    dem_verification_authority = dem_verification_candidate.get("authority", {})
    if dem_verification_authority.get("dem_amendment_status") != "not_granted":
        fail("M2 DEM verification must retain the unapproved amendment state")
    if any(value is True for key, value in dem_verification_authority.items() if key != "dem_amendment_status"):
        fail("M2 DEM verification candidate must not authorize execution")
    dem_verification_inputs = dem_verification_candidate.get("inputs", {})
    for ref_key, hash_key in (
        ("candidate_manifest_ref", "candidate_manifest_sha256"),
        ("intake_contract_ref", "intake_contract_sha256"),
        ("amendment_proposal_ref", "amendment_proposal_sha256"),
        ("review_bundle_ref", "review_bundle_sha256"),
        ("approved_aoi_ref", "approved_aoi_sha256"),
    ):
        relative = dem_verification_inputs.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"M2 DEM verification is missing {ref_key}")
        if dem_verification_inputs.get(hash_key) != sha256(relative):
            fail(f"M2 DEM verification does not bind {ref_key}")
    if radar_processing_contract.get("contract_id") != "NEPAL-S1-BASELINE-PROCESSING-001":
        fail("radar processing contract identity differs")
    if radar_processing_contract.get("status") != "predeclared_no_real_processing":
        fail("radar processing contract must remain a predeclaration")
    if radar_processing_contract.get("analysis_crs", {}).get("wkid") != 32645:
        fail("radar processing contract must target EPSG:32645")
    if {item.get("pair_id") for item in radar_processing_contract.get("routes", [])} != {
        "PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"
    }:
        fail("radar processing contract route set differs")
    radar_bindings = radar_processing_contract.get("bindings", {})
    for ref_key, hash_key in (
        ("pair_plan_ref", "pair_plan_sha256"),
        ("pixel_readiness_ref", "pixel_readiness_sha256"),
        ("arcgis_capability_ref", "arcgis_capability_sha256"),
        ("dem_manifest_ref", "dem_manifest_sha256"),
        ("dem_intake_candidate_ref", "dem_intake_candidate_sha256"),
        ("dem_verification_candidate_ref", "dem_verification_candidate_sha256"),
        ("dem_amendment_proposal_ref", "dem_amendment_proposal_sha256"),
        ("dem_review_bundle_ref", "dem_review_bundle_sha256"),
    ):
        relative = radar_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"radar processing contract is missing {ref_key}")
        if radar_bindings.get(hash_key) != sha256(relative):
            fail(f"radar processing contract does not bind {ref_key}")
    radar_authority = radar_processing_contract.get("authority", {})
    if radar_authority.get("dem_download_or_pixel_use_authorized") is not False or radar_authority.get("auxiliary_orbit_download_authorized") is not False:
        fail("radar processing contract must not authorize DEM or orbit-file acquisition")
    if radar_processing_contract.get("vertical_datum", {}).get("status") != "defer_pending_empirical_check_or_explicit_method_decision":
        fail("radar processing contract must defer the EGM2008 and EGM96 mismatch")
    radar_chain = {item.get("operation"): item for item in radar_processing_contract.get("processing_chain", [])}
    if radar_chain.get("radiometric calibration", {}).get("calibration_type") != "BETA_NOUGHT":
        fail("radar processing contract must calibrate to beta nought")
    if radar_chain.get("radiometric terrain flattening", {}).get("calibration_type") != "GAMMA_NOUGHT":
        fail("radar processing contract must terrain-flatten to gamma nought")
    if radar_processing_contract.get("speckle_policy", {}).get("primary_quantitative_route") != "no despeckle":
        fail("radar primary quantitative speckle policy differs")
    if radar_processing_contract.get("claim_boundary", {}).get("sentinel_pixels_processed") is not False:
        fail("radar processing predeclaration invents real processing")
    if dem_radar_readiness.get("status") != "pass_static_controls_only_dependencies_deferred":
        fail("DEM and radar control-readiness receipt status differs")
    readiness_bindings = dem_radar_readiness.get("bindings", {})
    for ref_key, hash_key in (
        ("dem_candidate_manifest_ref", "dem_candidate_manifest_sha256"),
        ("dem_amendment_proposal_ref", "dem_amendment_proposal_sha256"),
        ("dem_review_bundle_ref", "dem_review_bundle_sha256"),
        ("dem_intake_candidate_ref", "dem_intake_candidate_sha256"),
        ("dem_verification_candidate_ref", "dem_verification_candidate_sha256"),
        ("radar_processing_contract_ref", "radar_processing_contract_sha256"),
        ("dem_control_builder_ref", "dem_control_builder_sha256"),
        ("dem_geotiff_verifier_ref", "dem_geotiff_verifier_sha256"),
        ("radar_contract_builder_ref", "radar_contract_builder_sha256"),
        ("dem_control_tests_ref", "dem_control_tests_sha256"),
        ("radar_contract_tests_ref", "radar_contract_tests_sha256"),
        ("dem_verification_protocol_ref", "dem_verification_protocol_sha256"),
        ("radar_processing_protocol_ref", "radar_processing_protocol_sha256"),
        ("arcgis_capability_ref", "arcgis_capability_sha256"),
    ):
        relative = readiness_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"DEM and radar readiness receipt is missing {ref_key}")
        expected_hash = (
            "64315e9d1747682890a594320b27190cd009f03d45312bd1b015c883a9b479c6"
            if ref_key == "dem_geotiff_verifier_ref"
            else sha256(relative)
        )
        if readiness_bindings.get(hash_key) != expected_hash:
            fail(f"DEM and radar readiness receipt does not bind {ref_key}")
    if dem_radar_readiness.get("checks", {}).get("full_unit_suite") != {"status": "pass", "test_count": 82}:
        fail("DEM and radar readiness receipt must preserve 82 passing tests")
    readiness_assertions = dem_radar_readiness.get("assertions", {})
    if readiness_assertions.get("sentinel_product_bytes_transferred") != 0 or any(
        readiness_assertions.get(key) is not False
        for key in (
            "dem_payload_bytes_requested",
            "dem_license_accepted",
            "external_custody_mutated",
            "dem_pixels_examined",
            "sentinel_pixels_processed",
            "baseline_established",
            "scientific_result_established",
            "existing_dem_review_bundle_mutated",
        )
    ):
        fail("DEM and radar readiness receipt violates its no-payload claim boundary")
    if optical_processing_contract.get("contract_id") != "NEPAL-S2-BASELINE-PROCESSING-001":
        fail("optical processing contract identity differs")
    if optical_processing_contract.get("status") != "predeclared_no_real_processing":
        fail("optical processing contract must remain a predeclaration")
    optical_route = optical_processing_contract.get("route", {})
    if optical_route.get("pair_id") != "PAIR-S2-RUM-R119" or optical_route.get("before_source_id") != "M1-SRC-010" or optical_route.get("after_source_id") != "M1-SRC-008":
        fail("optical processing contract exact pair differs")
    if optical_route.get("processing_baseline_from_product_name") != "05.12":
        fail("optical processing contract baseline differs")
    optical_grid = optical_processing_contract.get("analysis_grid", {})
    if optical_grid.get("wkid") != 32645 or optical_grid.get("cell_size_m") != 20.0:
        fail("optical processing contract grid must use EPSG:32645 at 20 metres")
    if optical_grid.get("extent") != {"xmin": 273300.0, "ymin": 3070220.0, "xmax": 367820.0, "ymax": 3149220.0}:
        fail("optical processing contract grid extent differs")
    if optical_grid.get("columns") != 4726 or optical_grid.get("rows") != 3950:
        fail("optical processing contract grid dimensions differ")
    if optical_processing_contract.get("reflectance_scaling", {}).get("formula") != "(DN + BOA_ADD_OFFSET_band) / BOA_QUANTIFICATION_VALUE":
        fail("optical processing contract reflectance formula differs")
    if optical_processing_contract.get("reflectance_scaling", {}).get("dn_zero_policy") != "NoData_before_offset_or_scaling":
        fail("optical processing contract DN-zero policy differs")
    if set(optical_processing_contract.get("bands", {}).get("change_core", [])) != {"B02", "B03", "B04", "B08", "B11", "B12"}:
        fail("optical processing contract change-band set differs")
    if set(optical_processing_contract.get("mask", {}).get("valid_scl_classes", {})) != {"4", "5", "6"}:
        fail("optical processing contract valid SCL classes differ")
    if optical_processing_contract.get("cross_platform", {}).get("unmeasured_harmonization") != "prohibited":
        fail("optical processing contract must prohibit unmeasured harmonization")
    if optical_processing_contract.get("authority", {}).get("real_pixel_processing_started") is not False:
        fail("optical processing contract invents real processing")
    optical_bindings = optical_processing_contract.get("bindings", {})
    for ref_key, hash_key in (
        ("source_manifest_ref", "source_manifest_sha256"),
        ("source_manifest_approval_ref", "source_manifest_approval_sha256"),
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
        ("active_verification_ref", "active_verification_sha256"),
        ("pair_plan_ref", "pair_plan_sha256"),
        ("pixel_readiness_ref", "pixel_readiness_sha256"),
        ("approved_aoi_ref", "approved_aoi_sha256"),
    ):
        relative = optical_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"optical processing contract is missing {ref_key}")
        if optical_bindings.get(hash_key) != sha256(relative):
            fail(f"optical processing contract does not bind {ref_key}")
    if optical_arcgis_receipt.get("status") != "pass_synthetic_only":
        fail("optical ArcGIS receipt status differs")
    if optical_arcgis_receipt.get("runtime") != {
        "product": "ArcGISPro",
        "version": "3.7.1",
        "license_level": "Advanced",
        "spatial_analyst": "available_and_used",
    }:
        fail("optical ArcGIS receipt runtime differs")
    optical_arcgis_inputs = optical_arcgis_receipt.get("inputs", {})
    for ref_key, hash_key in (
        ("contract", "contract_sha256"),
        ("core", "core_sha256"),
        ("arcgis_adapter", "arcgis_adapter_sha256"),
    ):
        relative = optical_arcgis_inputs.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"optical ArcGIS receipt is missing {ref_key}")
        if optical_arcgis_inputs.get(hash_key) != sha256(relative):
            fail(f"optical ArcGIS receipt does not bind {ref_key}")
    if set(optical_arcgis_receipt.get("checks", {})) != {"B03", "B04", "B08", "B11", "B12", "NDVI", "MNDWI", "NBR"}:
        fail("optical ArcGIS receipt check set differs")
    if any(item.get("status") != "pass" for item in optical_arcgis_receipt.get("checks", {}).values()):
        fail("optical ArcGIS receipt contains a failed check")
    optical_assertions = optical_arcgis_receipt.get("assertions", {})
    if optical_assertions.get("dn_zero_preserved_as_nodata") is not True or optical_assertions.get("excluded_scl_preserved_as_nodata") is not True:
        fail("optical ArcGIS receipt did not preserve NoData or SCL exclusions")
    if any(
        optical_assertions.get(key) is not False
        for key in (
            "real_product_metadata_parsed",
            "real_product_pixels_examined",
            "external_custody_accessed",
            "source_association_created",
            "optical_baseline_established",
            "change_established",
            "scientific_admission_authorized",
        )
    ):
        fail("optical ArcGIS receipt violates its synthetic-only claim boundary")
    if optical_readiness.get("status") != "pass_predeclared_and_synthetic_only_real_route_deferred":
        fail("optical control-readiness receipt status differs")
    optical_readiness_bindings = optical_readiness.get("bindings", {})
    for ref_key, hash_key in (
        ("optical_contract_ref", "optical_contract_sha256"),
        ("optical_core_ref", "optical_core_sha256"),
        ("contract_builder_ref", "contract_builder_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("arcgis_receipt_ref", "arcgis_receipt_sha256"),
        ("portable_tests_ref", "portable_tests_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("pair_plan_ref", "pair_plan_sha256"),
        ("pixel_readiness_ref", "pixel_readiness_sha256"),
        ("source_manifest_ref", "source_manifest_sha256"),
        ("active_m2_ref", "active_m2_sha256"),
    ):
        relative = optical_readiness_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"optical readiness receipt is missing {ref_key}")
        expected_hash = (
            "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb"
            if ref_key == "active_m2_ref"
            else sha256(relative)
        )
        if optical_readiness_bindings.get(hash_key) != expected_hash:
            fail(f"optical readiness receipt does not bind {ref_key}")
    if optical_readiness.get("validation", {}).get("portable_test_count") != 15 or optical_readiness.get("validation", {}).get("full_repository_test_count") != 97:
        fail("optical readiness receipt test counts differ")
    if optical_readiness.get("current_route_disposition", {}).get("status") != "defer":
        fail("optical real-data route must remain deferred")
    if materialization_contract.get("materialization_id") != "NEPAL-M2-SAFE-MATERIALIZATION-001" or materialization_contract.get("status") != "active_authorized_gate_deferred":
        fail("M2 materialization contract identity or gate-deferred status differs")
    materialization_inputs = materialization_contract.get("inputs", {})
    for ref_key, hash_key in (
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("active_verification_ref", "active_verification_sha256"),
        ("materialization_core_ref", "materialization_core_sha256"),
        ("runner_ref", "runner_sha256"),
    ):
        relative = materialization_inputs.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"M2 materialization contract is missing {ref_key}")
        if materialization_inputs.get(hash_key) != sha256(relative):
            fail(f"M2 materialization contract does not bind {ref_key}")
    materialization_authority = materialization_contract.get("authority", {})
    if materialization_authority.get("mode") != "inherited" or materialization_authority.get("authority_ref") != "records/source-gates/m2-activation-approval.json":
        fail("M2 materialization does not inherit the exact active authority")
    if materialization_authority.get("this_contract_creates_authority") is not False or materialization_authority.get("dem_products_authorized") is not False or materialization_authority.get("network_access_authorized") is not False:
        fail("M2 materialization broadens authority")
    materialization_boundary = materialization_contract.get("execution_boundary", {})
    if materialization_boundary.get("external_data_root") != r"C:\Projects\Active\nepal-2026-before-after-map-data" or materialization_boundary.get("materialization_root") != r"C:\Projects\Active\nepal-2026-before-after-map-data\materialized":
        fail("M2 materialization external boundary differs")
    if materialization_boundary.get("network_requests") != "prohibited" or materialization_boundary.get("authentication") != "prohibited" or materialization_boundary.get("source_archive_mutation") != "prohibited":
        fail("M2 materialization must remain offline and read-only with respect to source archives")
    materialization_assets = materialization_contract.get("assets", [])
    expected_materialization_sources = {item["source_id"] for item in acquisition_plan["records"]}
    if len(materialization_assets) != 8 or {item.get("source_id") for item in materialization_assets} != expected_materialization_sources:
        fail("M2 materialization source set differs from the exact approved eight")
    verification_by_source = {item["source_id"]: item for item in active_offline_verification["assets"]}
    for item in materialization_assets:
        source = verification_by_source.get(item["source_id"])
        if not source or item.get("exact_product_id") != source.get("exact_product_id") or item.get("archive_relative_path") != source.get("archive_relative_path"):
            fail(f"M2 materialization asset differs from active verification for {item.get('source_id')}")
    if any(materialization_contract.get("claim_boundary", {}).get(key) is not False for key in (
        "raster_readability_established",
        "pixel_usability_established",
        "baseline_established",
        "change_established",
        "scientific_admission_authorized",
    )):
        fail("M2 materialization contract invents downstream evidence")
    if materialization_readiness.get("status") != "pass_synthetic_only_real_materialization_deferred":
        fail("M2 materialization readiness status differs")
    materialization_bindings = materialization_readiness.get("bindings", {})
    historical_materialization_hashes = {
        "active_m2_ref": "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb",
        "test_ref": "be2287d52730aeaeed2bb7b670e9596f229e0cf1aa3afd80ba72c1a6e37a267f",
    }
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("active_m2_ref", "active_m2_sha256_at_validation"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
    ):
        relative = materialization_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"M2 materialization readiness is missing {ref_key}")
        expected_hash = historical_materialization_hashes.get(ref_key, sha256(relative))
        if materialization_bindings.get(hash_key) != expected_hash:
            fail(f"M2 materialization readiness does not bind {ref_key}")
    materialization_validation = materialization_readiness.get("validation", {})
    if materialization_validation.get("targeted_test_count") != 14 or materialization_validation.get("full_repository_test_count") != 111:
        fail("M2 materialization readiness test counts differ")
    if materialization_readiness.get("current_disposition", {}).get("status") != "defer":
        fail("real M2 materialization must remain deferred at this checkpoint")
    if materialization_readiness.get("external_state") != {
        "custody_file_count": 0,
        "materialization_root_exists": False,
        "real_archive_bytes_read": 0,
        "real_archives_materialized": 0,
    }:
        fail("M2 materialization readiness historical external-state boundary differs")
    if optical_input_contract.get("contract_id") != "NEPAL-S2-MATERIALIZED-INPUT-READINESS-001" or optical_input_contract.get("status") != "predeclared_gate_deferred_no_real_safe":
        fail("optical input-readiness contract identity or status differs")
    optical_input_route = optical_input_contract.get("route", {})
    if optical_input_route.get("before_source_id") != "M1-SRC-010" or optical_input_route.get("after_source_id") != "M1-SRC-008" or optical_input_route.get("processing_baseline") != "05.12" or optical_input_route.get("tile") != "45RUM" or optical_input_route.get("relative_orbit") != 119:
        fail("optical input-readiness route differs from the exact pair")
    if optical_input_contract.get("analysis_crs", {}).get("wkid") != 32645:
        fail("optical input-readiness contract must use EPSG:32645")
    expected_input_roles = {
        "metadata_product", "metadata_tile", "B02", "B03", "B04", "B08", "B11", "B12", "SCL", "quality_classification"
    }
    if set(optical_input_contract.get("required_members", {}).get("role_patterns", {})) != expected_input_roles:
        fail("optical input-readiness member roles differ")
    input_header_rules = optical_input_contract.get("header_checks", {})
    if input_header_rules.get("single_band_roles") != ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]:
        fail("optical input-readiness single-band role declaration differs")
    if input_header_rules.get("quality_classification") != {
        "product_member": "MSK_CLASSI_B00.jp2",
        "band_count": 3,
        "cell_size_m": 60.0,
        "pixel_types": ["U1", "U8"],
        "band_semantics": {"1": "opaque_cloud", "2": "cirrus_cloud", "3": "snow_or_ice"},
    }:
        fail("optical input-readiness MSK_CLASSI model differs from the PB 05.12 specification")
    expected_input_source_references = [
        {
            "role": "sentinel2_multiband_mask_encoding",
            "url": "https://sentiwiki.copernicus.eu/web/s2-processing",
            "checked_at_utc": "2026-09-03T19:37:30Z",
        },
        {
            "role": "sentinel2_product_specification_v15_1",
            "url": "https://sentinels.copernicus.eu/documents/d/sentinel/sentinel-2-products-specification-document-15_1",
            "checked_at_utc": "2026-09-03T19:37:30Z",
        },
    ]
    if optical_input_contract.get("source_references") != expected_input_source_references:
        fail("optical input-readiness official source references differ")
    optical_input_contract_bindings = optical_input_contract.get("inputs", {})
    for ref_key, hash_key in (
        ("materialization_contract_ref", "materialization_contract_sha256"),
        ("optical_processing_contract_ref", "optical_processing_contract_sha256"),
        ("pixel_readiness_contract_ref", "pixel_readiness_contract_sha256"),
        ("source_manifest_ref", "source_manifest_sha256"),
        ("core_ref", "core_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
    ):
        relative = optical_input_contract_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"optical input-readiness contract is missing {ref_key}")
        if optical_input_contract_bindings.get(hash_key) != sha256(relative):
            fail(f"optical input-readiness contract does not bind {ref_key}")
    input_authority = optical_input_contract.get("authority", {})
    if input_authority.get("mode") != "inherited" or input_authority.get("this_contract_creates_authority") is not False or input_authority.get("network_access_authorized") is not False or input_authority.get("dem_products_authorized") is not False:
        fail("optical input-readiness authority boundary differs")
    if any(optical_input_contract.get("claim_boundary", {}).get(key) is not False for key in (
        "pixel_values_examined", "pixel_usability_established", "baseline_established", "change_established", "scientific_admission_authorized"
    )):
        fail("optical input-readiness contract invents downstream evidence")
    if optical_input_arcgis.get("status") != "pass_synthetic_only_with_expected_misalignment_block":
        fail("optical input-readiness ArcGIS receipt status differs")
    if optical_input_arcgis.get("runtime") != {
        "product": "ArcGISPro",
        "version": "3.7.1",
        "license_level": "Advanced",
        "gdal_version": "3120210",
        "jp2_driver": "JP2OpenJPEG",
    }:
        fail("optical input-readiness ArcGIS runtime differs")
    optical_input_arcgis_bindings = optical_input_arcgis.get("bindings", {})
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("adapter_ref", "adapter_sha256"),
    ):
        relative = optical_input_arcgis_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or optical_input_arcgis_bindings.get(hash_key) != sha256(relative):
            fail(f"optical input-readiness ArcGIS receipt does not bind {ref_key}")
    fixture = optical_input_arcgis.get("fixture", {})
    if fixture.get("jp2_raster_count") != 16 or fixture.get("before_inventory_status") != "pass_inventory_only" or fixture.get("after_inventory_status") != "pass_inventory_only":
        fail("optical input-readiness synthetic inventory differs")
    for pair_role in ("before", "after"):
        descriptions = fixture.get("header_descriptions", {}).get(pair_role, {})
        if set(descriptions) != expected_input_roles - {"metadata_product", "metadata_tile"}:
            fail(f"optical input-readiness {pair_role} header inventory differs")
        if any(
            item.get("format") != "JP2"
            or item.get("wkid") != 32645
            or item.get("band_count") != (3 if role == "quality_classification" else 1)
            for role, item in descriptions.items()
        ):
            fail(f"optical input-readiness {pair_role} contains a nonpassing JP2 header")
        quality_header = descriptions.get("quality_classification", {})
        if quality_header.get("cell_width") != 60.0 or quality_header.get("cell_height") != 60.0 or quality_header.get("pixel_type") not in {"U1", "U8"}:
            fail(f"optical input-readiness {pair_role} MSK_CLASSI header differs")
        quality_bands = quality_header.get("band_details", [])
        if [item.get("name") for item in quality_bands] != ["Band_1", "Band_2", "Band_3"] or any(
            item.get("width") != 2
            or item.get("height") != 2
            or item.get("cell_width") != 60.0
            or item.get("cell_height") != 60.0
            or item.get("pixel_type") != "U8"
            for item in quality_bands
        ):
            fail(f"optical input-readiness {pair_role} MSK_CLASSI band headers differ")
        metadata_check = fixture.get("metadata_checks", {}).get(pair_role, {})
        if metadata_check.get("processing_baseline") != "05.12" or metadata_check.get("quantification_value") != 10000.0 or metadata_check.get("used_band_offset_count") != 6 or metadata_check.get("errors") != []:
            fail(f"optical input-readiness {pair_role} metadata check differs")
    if optical_input_arcgis.get("checks", {}).get("aligned_pair", {}).get("status") != "pass_header_readability_only":
        fail("optical input-readiness aligned synthetic pair did not pass")
    shifted_header = optical_input_arcgis.get("checks", {}).get("intentional_after_grid_shift", {})
    if shifted_header.get("status") != "block" or len(shifted_header.get("errors", [])) != 16:
        fail("optical input-readiness intentional grid shift did not retain its expected block")
    input_assertions = optical_input_arcgis.get("assertions", {})
    if input_assertions.get("synthetic_jp2_opened_by_arcgis") is not True or input_assertions.get("intentional_grid_shift_blocked") is not True:
        fail("optical input-readiness synthetic ArcGIS assertions differ")
    if any(input_assertions.get(key) is not False for key in (
        "external_custody_accessed", "real_materialization_receipt_used", "real_product_metadata_read", "real_product_pixels_examined", "pixel_usability_established", "baseline_established", "change_established", "scientific_admission_authorized"
    )):
        fail("optical input-readiness ArcGIS receipt violates its synthetic-only boundary")
    if optical_input_contract.get("header_checks", {}).get("extent_must_equal_dimensions_times_cell_size") is not True:
        fail("optical input-readiness contract must reconcile dimensions, cell sizes, and extents")
    if (
        len(optical_input_arcgis.get("retained_failures", [])) != 3
        or len(optical_input_arcgis.get("retained_prepublication_attempts", [])) != 5
        or len(optical_input_arcgis.get("retained_published_attempts", [])) != 1
    ):
        fail("optical input-readiness ArcGIS receipt did not retain every failed or superseded attempt")
    if optical_input_readiness.get("status") != "pass_corrected_synthetic_arcgis_real_input_deferred":
        fail("optical input-readiness control receipt status differs")
    control_bindings = optical_input_readiness.get("bindings", {})
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("arcgis_receipt_ref", "arcgis_receipt_sha256"),
        ("materialization_contract_ref", "materialization_contract_sha256"),
        ("optical_processing_contract_ref", "optical_processing_contract_sha256"),
        ("active_m2_ref", "active_m2_sha256_at_validation"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
    ):
        relative = control_bindings.get(ref_key)
        expected_hash = (
            "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb"
            if ref_key == "active_m2_ref"
            else sha256(relative) if isinstance(relative, str) and (ROOT / relative).is_file() else None
        )
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or control_bindings.get(hash_key) != expected_hash:
            fail(f"optical input-readiness control receipt does not bind {ref_key}")
    input_validation = optical_input_readiness.get("validation", {})
    if (
        input_validation.get("portable_test_count") != 12
        or input_validation.get("full_repository_test_count") != 123
        or input_validation.get("synthetic_jp2_raster_count") != 16
        or input_validation.get("quality_classification_band_count") != 3
        or input_validation.get("quality_classification_cell_size_m") != 60.0
        or input_validation.get("intentional_after_grid_shift_error_count") != 16
    ):
        fail("optical input-readiness validation counts differ")
    if optical_input_readiness.get("supersedes") != {
        "evidence_record_id": "EVID-0026",
        "published_commit": "df3e93aadef064129c928463cc1f5eec562e3950",
        "reason": "Official Sentinel-2 documentation identifies PB 05.12 MSK_CLASSI_B00.jp2 as a three-band 60 m Boolean mask, not the one-band 20 m mask used by the published fixture.",
    }:
        fail("optical input-readiness correction does not preserve the exact superseded checkpoint")
    if optical_input_readiness.get("source_references") != expected_input_source_references:
        fail("optical input-readiness control receipt does not preserve its official sources")
    retained_published_corrections = optical_input_readiness.get("retained_published_control_corrections", [])
    if len(retained_published_corrections) != 1 or retained_published_corrections[0].get("status") != "superseded_after_publication":
        fail("optical input-readiness control receipt does not retain the published correction")
    if optical_input_readiness.get("current_disposition", {}).get("status") != "defer" or optical_input_readiness.get("external_state", {}).get("custody_file_count") != 0 or optical_input_readiness.get("external_state", {}).get("materialization_root_exists") is not False:
        fail("optical input-readiness real route must remain historically deferred with empty custody")

    expected_radar_input_contract_sha = "ad478b8abd4e4a47c8d16012fffc2b67770681538bddc23b500ce5b32b17428a"
    if (
        sha256("config/qa/radar-input-readiness-contract.json") != expected_radar_input_contract_sha
        or radar_input_contract.get("contract_id") != "NEPAL-S1-MATERIALIZED-INPUT-READINESS-001"
        or radar_input_contract.get("status") != "predeclared_active_exact_three_pre_event_sources"
        or radar_input_contract.get("analysis_crs", {}).get("wkid") != 32645
    ):
        fail("Sentinel-1 input-readiness contract identity or exact bytes differ")
    expected_radar_input_sources = [
        ("M1-SRC-001", "S1D_IW_GRDH_1SDV_20260816T122116_20260816T122141_004151_007980_B057.SAFE", "retained_unintended_test_execution"),
        ("M1-SRC-002", "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB.SAFE", "planned_authorized_offline_materialization"),
        ("M1-SRC-003", "S1D_IW_GRDH_1SDV_20260819T001036_20260819T001101_004187_007ABD_DC16.SAFE", "planned_authorized_offline_materialization"),
    ]
    radar_sources = radar_input_contract.get("sources", [])
    if [
        (item.get("source_id"), item.get("exact_product_id"), item.get("materialization_provenance"))
        for item in radar_sources
    ] != expected_radar_input_sources:
        fail("Sentinel-1 input-readiness source boundary or provenance differs")
    for item in radar_sources:
        receipt_ref = item.get("materialization_receipt_ref")
        if (
            not isinstance(receipt_ref, str)
            or not (ROOT / receipt_ref).is_file()
            or item.get("materialization_receipt_sha256") != sha256(receipt_ref)
        ):
            fail(f"Sentinel-1 input-readiness receipt binding differs for {item.get('source_id')}")
        materialization = sentinel_materialization_receipts[item["source_id"]]
        if item.get("external_manifest_sha256") != materialization.get("bindings", {}).get("external_manifest_sha256"):
            fail(f"Sentinel-1 input-readiness manifest binding differs for {item.get('source_id')}")
    expected_radar_roles = {
        "manifest_safe": "manifest.safe",
        "annotation_vv": "annotation/*-vv-*.xml",
        "annotation_vh": "annotation/*-vh-*.xml",
        "calibration_vv": "annotation/calibration/calibration-*-vv-*.xml",
        "calibration_vh": "annotation/calibration/calibration-*-vh-*.xml",
        "noise_vv": "annotation/calibration/noise-*-vv-*.xml",
        "noise_vh": "annotation/calibration/noise-*-vh-*.xml",
        "measurement_vv": "measurement/*-vv-*.tiff",
        "measurement_vh": "measurement/*-vh-*.tiff",
    }
    if radar_input_contract.get("required_members", {}).get("role_patterns") != expected_radar_roles:
        fail("Sentinel-1 input-readiness required member roles differ")
    radar_input_bindings = radar_input_contract.get("inputs", {})
    for ref_key, hash_key in (
        ("materialization_contract_ref", "materialization_contract_sha256"),
        ("radar_processing_contract_ref", "radar_processing_contract_sha256"),
        ("pixel_readiness_contract_ref", "pixel_readiness_contract_sha256"),
        ("source_manifest_ref", "source_manifest_sha256"),
        ("active_m2_ref", "active_m2_sha256"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("core_ref", "core_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
    ):
        relative = radar_input_bindings.get(ref_key)
        expected_hash = (
            "411429f0d31d438a0e4d409e880c1dbac595361a155ce1a3eeaab3513f82f8c8"
            if ref_key == "active_m2_ref"
            else sha256(relative) if isinstance(relative, str) and (ROOT / relative).is_file() else None
        )
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or radar_input_bindings.get(hash_key) != expected_hash:
            fail(f"Sentinel-1 input-readiness contract does not bind {ref_key}")
    radar_execution = radar_input_contract.get("execution_boundary", {})
    if (
        radar_execution.get("network_requests") != "prohibited"
        or radar_execution.get("authentication") != "prohibited"
        or radar_execution.get("credential_access") != "prohibited"
        or radar_execution.get("external_data_mutation") != "prohibited"
        or radar_execution.get("pixel_value_decoding") != "prohibited_header_and_metadata_reads_only"
        or radar_execution.get("derived_raster_writes") != "prohibited"
        or radar_input_contract.get("metadata_checks", {}).get("embedded_orbit_vectors_must_bracket_acquisition") is not True
        or radar_input_contract.get("decision_semantics", {}).get("pass_releases_baseline_processing") is not False
        or any(radar_input_contract.get("claim_boundary", {}).get(key) is not False for key in (
            "pixel_values_examined", "pixel_usability_established", "complete_pair_established",
            "baseline_established", "change_established", "scientific_admission_authorized",
        ))
    ):
        fail("Sentinel-1 input-readiness execution or claim boundary differs")
    if radar_input_arcgis.get("status") != "pass_synthetic_arcgis_real_input_deferred":
        fail("Sentinel-1 synthetic ArcGIS input-readiness status differs")
    synthetic_bindings = radar_input_arcgis.get("bindings", {})
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("runner_ref", "runner_sha256"),
        ("adapter_ref", "adapter_sha256"),
    ):
        relative = synthetic_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or synthetic_bindings.get(hash_key) != sha256(relative):
            fail(f"Sentinel-1 synthetic ArcGIS receipt does not bind {ref_key}")
    radar_validation = radar_input_arcgis.get("validation", {})
    if (
        radar_input_arcgis.get("runtime", {}).get("product") != "ArcGISPro"
        or radar_input_arcgis.get("runtime", {}).get("version") != "3.7.1"
        or radar_validation.get("synthetic_source_count") != 3
        or radar_validation.get("synthetic_measurement_raster_count") != 6
        or radar_validation.get("required_member_role_count") != 9
        or radar_validation.get("aggregate_decision", {}).get("status") != "pass_partial_pre_event_header_readiness_only"
        or radar_validation.get("intentional_cross_polarization_width_mismatch", {}).get("status") != "block"
        or any(value.get("status") != "pass_header_readability_only" for value in radar_validation.get("aligned_source_decisions", {}).values())
    ):
        fail("Sentinel-1 synthetic ArcGIS validation result differs")
    radar_synthetic_activity = radar_input_arcgis.get("activity", {})
    if any(radar_synthetic_activity.get(key) is not False for key in (
        "external_custody_accessed", "real_materialization_receipt_used", "real_product_metadata_read",
        "real_product_raster_header_opened", "real_product_pixel_values_examined", "network_requests_performed",
        "authentication_performed",
    )):
        fail("Sentinel-1 synthetic ArcGIS receipt violates the real-data boundary")
    if (
        radar_input_failure.get("status") != "fail_synthetic_adapter_datetime_name_collision"
        or radar_input_failure.get("bindings", {}).get("contract_sha256") != sha256(radar_input_failure["bindings"]["contract_ref"])
        or radar_input_failure.get("retained_output", {}).get("file_count") != 5
        or radar_input_failure.get("retained_output", {}).get("total_bytes") != 3370
        or radar_input_failure.get("activity", {}).get("real_product_data_read") is not False
        or radar_input_failure.get("activity", {}).get("synthetic_output_deleted") is not False
    ):
        fail("Sentinel-1 synthetic ArcGIS failed attempt differs or was obscured")
    if radar_input_readiness.get("status") != "pass_predeclared_and_synthetic_arcgis_real_input_not_run":
        fail("Sentinel-1 input-readiness control status differs")
    radar_control_bindings = radar_input_readiness.get("bindings", {})
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("synthetic_arcgis_receipt_ref", "synthetic_arcgis_receipt_sha256"),
    ):
        relative = radar_control_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or radar_control_bindings.get(hash_key) != sha256(relative):
            fail(f"Sentinel-1 input-readiness control does not bind {ref_key}")
    retained_radar_attempts = radar_input_readiness.get("retained_prepublication_attempts", [])
    if len(retained_radar_attempts) != 6 or [item.get("status") for item in retained_radar_attempts] != [
        "superseded_before_publication", "fail", "superseded_before_publication",
        "superseded_before_publication", "superseded_before_publication", "superseded_before_publication"
    ]:
        fail("Sentinel-1 input-readiness control does not retain all prepublication attempts")
    for item in retained_radar_attempts:
        for ref_key, hash_key in (("contract_ref", "contract_sha256"), ("receipt_ref", "receipt_sha256"), ("failure_receipt_ref", "failure_receipt_sha256")):
            if ref_key not in item:
                continue
            relative = item[ref_key]
            if not (ROOT / relative).is_file() or item.get(hash_key) != sha256(relative):
                fail(f"Sentinel-1 input-readiness retained attempt does not bind {ref_key}")
    radar_control_validation = radar_input_readiness.get("validation", {})
    radar_external_state = radar_input_readiness.get("external_state", {})
    radar_assertions = radar_input_readiness.get("assertions", {})
    if (
        radar_control_validation.get("portable_test_count") != 14
        or radar_control_validation.get("portable_test_status") != "pass"
        or radar_control_validation.get("deterministic_contract_derivation") != "pass_exact_bytes"
        or radar_external_state.get("materialized_source_count") != 3
        or radar_external_state.get("real_runner_executed") is not False
        or any(radar_external_state.get(key) is not False for key in (
            "real_materialization_receipt_used_by_control_validation", "external_custody_accessed_by_control_validation",
            "real_product_metadata_read", "real_product_raster_header_opened", "real_product_pixel_values_examined",
        ))
        or any(radar_assertions.get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "baseline_processing_released", "pixel_usability_established", "complete_pair_established",
            "change_established", "scientific_admission_authorized", "authority_created",
        ))
    ):
        fail("Sentinel-1 input-readiness control validation or boundary differs")
    if (
        radar_input_real.get("status") != "block"
        or radar_input_real.get("bindings", {}).get("contract_sha256") != sha256("config/qa/radar-input-readiness-contract.json")
        or radar_input_real.get("runtime") != {"product": "ArcGISPro", "version": "3.7.1", "license_level": "Advanced"}
        or radar_input_real.get("decision", {}).get("ready_source_count") != 0
        or radar_input_real.get("decision", {}).get("complete_before_after_pair") is not False
    ):
        fail("Sentinel-1 real input-readiness receipt identity or aggregate block differs")
    if set(radar_input_real.get("products", {})) != {"M1-SRC-001", "M1-SRC-002", "M1-SRC-003"}:
        fail("Sentinel-1 real input-readiness source set differs")
    for source_id, product in radar_input_real.get("products", {}).items():
        annotations = product.get("annotations", {})
        headers = product.get("raster_headers", {})
        if (
            product.get("inventory", {}).get("status") != "pass_inventory_only"
            or product.get("inventory", {}).get("errors") != []
            or set(annotations) != {"vv", "vh"}
            or set(headers) != {"vv", "vh"}
            or product.get("decision", {}).get("status") != "block"
            or product.get("decision", {}).get("errors") != [
                "VV annotation pixel value is not AMPLITUDE",
                "VH annotation pixel value is not AMPLITUDE",
            ]
        ):
            fail(f"Sentinel-1 real input-readiness decision differs for {source_id}")
        for polarization in ("vv", "vh"):
            annotation = annotations[polarization]
            header = headers[polarization]
            if (
                annotation.get("pixel_value") != "Detected"
                or annotation.get("errors") != []
                or annotation.get("orbit_times_strictly_increasing") is not True
                or annotation.get("orbit_vectors_finite") is not True
                or header.get("format") != "TIFF"
                or header.get("band_count") != 1
                or header.get("pixel_type") != "U16"
                or header.get("width") != annotation.get("number_of_samples")
                or header.get("height") != annotation.get("number_of_lines")
            ):
                fail(f"Sentinel-1 real annotation or header evidence differs for {source_id} {polarization}")
    radar_real_activity = radar_input_real.get("activity", {})
    if (
        radar_real_activity.get("external_materialization_inventory_unchanged") is not True
        or radar_real_activity.get("selected_materialized_files_rehashed") is not True
        or radar_real_activity.get("all_real_annotation_metadata_parsed") is not True
        or radar_real_activity.get("all_real_measurement_raster_headers_opened_with_arcgis") is not True
        or any(radar_real_activity.get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "real_product_pixel_values_examined", "derived_raster_written",
        ))
    ):
        fail("Sentinel-1 real input-readiness activity boundary differs")
    real_reconciliation_bindings = radar_input_real_reconciliation.get("bindings", {})
    if (
        radar_input_real_reconciliation.get("status") != "block_predeclared_annotation_pixel_value_mismatch_no_retry"
        or real_reconciliation_bindings.get("contract_sha256") != sha256("config/qa/radar-input-readiness-contract.json")
        or real_reconciliation_bindings.get("real_receipt_sha256") != sha256("records/readiness/radar-input/m2-s1-input-readiness-real-001.json")
        or real_reconciliation_bindings.get("control_receipt_sha256") != sha256("records/surface-receipts/radar-input-readiness-control.json")
        or radar_input_real_reconciliation.get("publication_gate", {}).get("commit_sha") != "87aa2610f1a89fe2d612f9cdd6cb88e63e833c8d"
        or radar_input_real_reconciliation.get("publication_gate", {}).get("github_actions_run_id") != 33905019294
        or radar_input_real_reconciliation.get("publication_gate", {}).get("github_actions_conclusion") != "success"
    ):
        fail("Sentinel-1 real input-readiness reconciliation bindings or publication gate differ")
    real_observed = radar_input_real_reconciliation.get("observed_result", {})
    real_external = radar_input_real_reconciliation.get("external_custody_reverification", {})
    real_disposition = radar_input_real_reconciliation.get("disposition", {})
    real_assertions = radar_input_real_reconciliation.get("assertions", {})
    if (
        real_observed.get("source_count") != 3
        or real_observed.get("annotation_parse_count") != 6
        or real_observed.get("measurement_header_open_count") != 6
        or real_observed.get("annotation_pixel_value_observed_set") != ["Detected"]
        or real_observed.get("source_pass_count") != 0
        or real_observed.get("source_block_count") != 3
        or real_external.get("status") != "pass_exact_attempt_inventories_and_all_safe_hashes_unchanged"
        or real_external.get("attempt_file_count") != 87
        or real_external.get("safe_file_count") != 78
        or real_external.get("safe_total_bytes") != 5183550209
        or real_external.get("added_sidecar_count") != 0
        or real_disposition.get("automatic_retry_authorized") is not False
        or real_disposition.get("contract_threshold_or_label_change_authorized") is not False
        or any(real_assertions.get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "real_product_pixel_values_examined", "derived_raster_written", "pixel_usability_established",
            "complete_pair_established", "baseline_processing_released", "change_established",
            "scientific_admission_authorized", "current_checkpoint_changed",
            "sentinel_recovery_authority_created", "orbit_recovery_authority_created",
        ))
    ):
        fail("Sentinel-1 real input-readiness reconciliation result or boundary differs")
    if (
        sha256("records/source-gates/m2-radar-input-label-specification-source-gate.json") != "0bf61ef4d72444bcba3bd753fe15511cdebc87288d0d4dfeda9a9bbaeaeb2daf"
        or radar_label_source_gate.get("contract_version") != "source-gate/v1"
        or radar_label_source_gate.get("decision", {}).get("status") != "ready"
        or radar_label_source_gate.get("decision", {}).get("approved_actions") != ["metadata_capture", "update_project_records"]
        or radar_label_source_gate.get("findings", {}).get("schema_value_domain") != ["Complex", "Detected"]
        or radar_label_source_gate.get("findings", {}).get("image_information_pixel_value_domain") != ["Detected", "Complex"]
        or radar_label_source_gate.get("findings", {}).get("failed_contract_value") != "AMPLITUDE"
        or radar_label_source_gate.get("findings", {}).get("observed_real_value") != "Detected"
        or [item.get("source_id") for item in radar_label_source_gate.get("sources", [])] != ["S1-PSD-2025", "S1-PROCESSING-LIVE"]
        or any(
            criterion.get("required") is not True or criterion.get("status") != "pass" or not criterion.get("evidence")
            for source in radar_label_source_gate.get("sources", [])
            for criterion in source.get("criteria", [])
        )
    ):
        fail("Sentinel-1 annotation-label official source gate differs")
    expected_label_proposal_sha = "ebdcb763afd99ea23090c9bd83fd9e9cb6cb8dfbb2b5fed60edb80f1fa61c731"
    label_proposal_bindings = radar_label_amendment.get("bindings", {})
    if (
        sha256("contracts/milestone-002-radar-input-readiness-amendment-proposal.json") != expected_label_proposal_sha
        or radar_label_amendment.get("status") != "proposed_inactive_owner_review_required"
        or radar_label_amendment.get("authority", {}).get("human_review_required") is not True
        or radar_label_amendment.get("authority", {}).get("this_proposal_creates_authority") is not False
        or label_proposal_bindings.get("failed_contract_sha256") != sha256("config/qa/radar-input-readiness-contract.json")
        or label_proposal_bindings.get("failed_real_receipt_sha256") != sha256("records/readiness/radar-input/m2-s1-input-readiness-real-001.json")
        or label_proposal_bindings.get("failed_result_reconciliation_sha256") != sha256("records/surface-receipts/radar-input-readiness-real-reconciliation.json")
        or label_proposal_bindings.get("official_source_gate_sha256") != sha256("records/source-gates/m2-radar-input-label-specification-source-gate.json")
        or radar_label_amendment.get("proposed_exact_change", {}).get("from") != "AMPLITUDE"
        or radar_label_amendment.get("proposed_exact_change", {}).get("to") != "Detected"
        or radar_label_amendment.get("decision_semantics", {}).get("baseline_processing_released_by_pass") is not False
        or radar_label_amendment.get("claim_boundary", {}).get("amendment_active") is not False
        or radar_label_amendment.get("claim_boundary", {}).get("corrected_real_run_executed") is not False
    ):
        fail("Sentinel-1 input-readiness label amendment proposal differs or is active")
    if (
        radar_label_review_surface.get("status") != "pass_blank_review_surface"
        or radar_label_review_surface.get("artifact", {}).get("sha256") != sha256("docs/assets/m2-radar-input-readiness-amendment-review.png")
        or radar_label_review_surface.get("bindings", {}).get("proposal_sha256") != expected_label_proposal_sha
        or radar_label_review_surface.get("bindings", {}).get("source_gate_sha256") != sha256("records/source-gates/m2-radar-input-label-specification-source-gate.json")
        or radar_label_review_surface.get("bindings", {}).get("failed_real_receipt_sha256") != sha256("records/readiness/radar-input/m2-s1-input-readiness-real-001.json")
        or radar_label_review_surface.get("bindings", {}).get("render_script_sha256") != sha256("scripts/render_m2_radar_input_readiness_amendment_review.py")
        or radar_label_review_surface.get("validation", {}).get("visual_inspection") != "pass"
        or radar_label_review_surface.get("validation", {}).get("blank_state_verified") is not True
        or radar_label_review_surface.get("validation", {}).get("human_decision_count") != 0
    ):
        fail("Sentinel-1 label-amendment review surface differs or is not blank")
    expected_label_bundle_sha = "831df5d5aae06862514667ad861c815154085fa3c546039e60f517d38ee442ff"
    if (
        sha256("reviews/m2-radar-input-readiness-amendment/review-bundle.json") != expected_label_bundle_sha
        or radar_label_review_bundle.get("template") is not False
        or radar_label_review_bundle.get("candidate_identity") != f"M2-RADAR-INPUT-READINESS-AMENDMENT-PROPOSAL-SHA256:{expected_label_proposal_sha}"
        or radar_label_review_bundle.get("review_surface") != {
            "artifact_id": "review-surface",
            "blank_state_verified": True,
            "completion_controls_verified": True,
            "export_verified": True,
        }
    ):
        fail("Sentinel-1 label-amendment review bundle identity differs")
    for artifact in radar_label_review_bundle.get("artifacts", []):
        relative = artifact.get("path")
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or artifact.get("sha256") != sha256(relative):
            fail(f"Sentinel-1 label-amendment bundle artifact differs: {relative}")
        for receipt in artifact.get("render_receipts", []):
            receipt_ref = receipt.get("path")
            if not isinstance(receipt_ref, str) or not (ROOT / receipt_ref).is_file() or receipt.get("sha256") != sha256(receipt_ref):
                fail(f"Sentinel-1 label-amendment bundle render receipt differs: {receipt_ref}")
    if (
        radar_label_review_contract.get("template") is not False
        or radar_label_review_contract.get("review_bundle", {}).get("manifest_sha256") != expected_label_bundle_sha
        or radar_label_review_contract.get("review_bundle", {}).get("rendered_surface_verified") is not True
        or radar_label_review_contract.get("allowed_decisions") != ["approve", "revise", "defer"]
        or radar_label_review_contract.get("required_attestation") is not True
        or radar_label_review_contract.get("items") != [{
            "item_id": "M2-RADAR-INPUT-LABEL-AMENDMENT-001",
            "evidence_sha256": expected_label_bundle_sha,
        }]
    ):
        fail("Sentinel-1 label-amendment review contract differs")
    if (
        radar_label_blank_response.get("review_id") != "m2-radar-input-readiness-amendment-review-001"
        or radar_label_blank_response.get("completed") is not False
        or radar_label_blank_response.get("reviewer", {}).get("attestation") is not False
        or radar_label_blank_response.get("review_started_at_utc") is not None
        or radar_label_blank_response.get("review_completed_at_utc") is not None
        or radar_label_blank_response.get("responses") != [{
            "item_id": "M2-RADAR-INPUT-LABEL-AMENDMENT-001",
            "evidence_sha256": expected_label_bundle_sha,
            "decision": None,
            "notes": "",
        }]
    ):
        fail("Sentinel-1 label-amendment blank response contains a decision or differs")
    if (
        radar_label_review_reconciliation.get("status") != "reconciled_exact_human_response"
        or radar_label_review_reconciliation.get("contract_sha256") != sha256("reviews/m2-radar-input-readiness-amendment/review-contract.json")
        or radar_label_review_reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or radar_label_review_reconciliation.get("human_decision_count") != 1
        or radar_label_review_reconciliation.get("human_decisions_fabricated") is not False
    ):
        fail("Sentinel-1 label-amendment human decision reconciliation differs")
    if (
        radar_label_approval.get("status") != "approved_exact_bounded_post_observation_correction"
        or radar_label_approval.get("review_bundle_manifest_sha256") != expected_label_bundle_sha
        or radar_label_approval.get("amendment_proposal_sha256") != expected_label_proposal_sha
        or radar_label_approval.get("review_reconciliation_sha256") != sha256("records/source-gates/m2-radar-input-readiness-amendment-review-reconciliation.json")
        or radar_label_approval.get("locked_response_sha256") != radar_label_review_reconciliation.get("response_sha256")
        or radar_label_approval.get("lock_receipt_sha256") != radar_label_review_reconciliation.get("receipt_sha256")
        or radar_label_approval.get("exact_correction") != {
            "field": "metadata_checks.pixel_value", "from": "AMPLITUDE", "to": "Detected", "post_observation": True,
        }
        or radar_label_approval.get("human_decisions_fabricated") is not False
    ):
        fail("Sentinel-1 label-amendment approval identity or boundary differs")
    if (
        sha256("config/qa/radar-input-readiness-contract.json") != "ad478b8abd4e4a47c8d16012fffc2b67770681538bddc23b500ce5b32b17428a"
        or sha256("records/readiness/radar-input/m2-s1-input-readiness-real-001.json") != "feab3645709df16306c81dae959a8693925a7c6f919f2a1e414cf3765c3a5b0c"
        or sha256("records/surface-receipts/radar-input-readiness-real-reconciliation.json") != "5e4f703b938f9adaf10a6f37ec5195d1e1fc426197ffa1fa6a712ba0cb4de0a6"
    ):
        fail("Sentinel-1 real-001 failure evidence was not preserved exactly")
    if (
        radar_label_contract.get("contract_version") != "1.1"
        or radar_label_contract.get("contract_id") != "NEPAL-S1-MATERIALIZED-INPUT-READINESS-002"
        or radar_label_contract.get("status") != "active_amendment_001_exact_three_pre_event_sources"
        or radar_label_contract.get("metadata_checks", {}).get("pixel_value") != "Detected"
        or radar_label_contract.get("sources") != radar_input_contract.get("sources")
        or radar_label_contract.get("required_members") != radar_input_contract.get("required_members")
        or radar_label_contract.get("header_checks") != radar_input_contract.get("header_checks")
        or radar_label_contract.get("execution_boundary") != radar_input_contract.get("execution_boundary")
        or radar_label_contract.get("decision_semantics") != radar_input_contract.get("decision_semantics")
        or radar_label_contract.get("claim_boundary") != radar_input_contract.get("claim_boundary")
        or radar_label_contract.get("amendment", {}).get("only_observed_data_semantic_change") != "metadata_checks.pixel_value: AMPLITUDE -> Detected"
        or radar_label_contract.get("amendment", {}).get("real_002_maximum_invocations") != 1
    ):
        fail("Sentinel-1 amended input-readiness contract broadens or differs from the one-field correction")
    amended_bindings = radar_label_contract.get("inputs", {})
    for ref_key, hash_key in (
        ("failed_contract_ref", "failed_contract_sha256"),
        ("failed_real_receipt_ref", "failed_real_receipt_sha256"),
        ("failed_result_reconciliation_ref", "failed_result_reconciliation_sha256"),
        ("amendment_proposal_ref", "amendment_proposal_sha256"),
        ("amendment_approval_ref", "amendment_approval_sha256"),
        ("official_source_gate_ref", "official_source_gate_sha256"),
        ("review_bundle_ref", "review_bundle_sha256"),
        ("review_reconciliation_ref", "review_reconciliation_sha256"),
        ("core_ref", "core_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
    ):
        relative = amended_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or amended_bindings.get(hash_key) != sha256(relative):
            fail(f"Sentinel-1 amended contract does not bind {ref_key}")
    if (
        amended_bindings.get("active_m2_ref") != "contracts/milestone-002.json"
        or amended_bindings.get("active_m2_sha256") != "411429f0d31d438a0e4d409e880c1dbac595361a155ce1a3eeaab3513f82f8c8"
    ):
        fail("Sentinel-1 amended contract does not preserve its publication-time M2 binding")
    activation_bindings = radar_label_activation.get("bindings", {})
    if (
        radar_label_activation.get("status") != "pass_exact_bounded_amendment_activated_publication_pending"
        or activation_bindings.get("approval_sha256") != sha256("records/source-gates/m2-radar-input-readiness-amendment-approval.json")
        or activation_bindings.get("amended_contract_sha256") != sha256("config/qa/radar-input-readiness-contract-amendment-001.json")
        or radar_label_activation.get("assertions", {}).get("real_002_executed") is not False
        or radar_label_activation.get("assertions", {}).get("pixel_values_examined") is not False
        or radar_label_activation.get("assertions", {}).get("baseline_processing_released") is not False
        or radar_label_activation.get("assertions", {}).get("scientific_action_released") is not False
    ):
        fail("Sentinel-1 label-amendment activation boundary differs")
    amended_synthetic_bindings = radar_label_synthetic.get("bindings", {})
    if radar_label_synthetic.get("status") != "pass_synthetic_arcgis_real_input_deferred":
        fail("Sentinel-1 amended synthetic ArcGIS result did not pass")
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"), ("core_ref", "core_sha256"),
        ("runner_ref", "runner_sha256"), ("adapter_ref", "adapter_sha256"),
    ):
        relative = amended_synthetic_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or amended_synthetic_bindings.get(hash_key) != sha256(relative):
            fail(f"Sentinel-1 amended synthetic receipt does not bind {ref_key}")
    amended_synthetic_validation = radar_label_synthetic.get("validation", {})
    amended_synthetic_activity = radar_label_synthetic.get("activity", {})
    if (
        radar_label_synthetic.get("runtime", {}).get("product") != "ArcGISPro"
        or radar_label_synthetic.get("runtime", {}).get("version") != "3.7.1"
        or amended_synthetic_validation.get("synthetic_source_count") != 3
        or amended_synthetic_validation.get("synthetic_measurement_raster_count") != 6
        or amended_synthetic_validation.get("aggregate_decision", {}).get("status") != "pass_partial_pre_event_header_readiness_only"
        or amended_synthetic_validation.get("intentional_cross_polarization_width_mismatch", {}).get("status") != "block"
        or any(value.get("status") != "pass_header_readability_only" for value in amended_synthetic_validation.get("aligned_source_decisions", {}).values())
        or any(amended_synthetic_activity.get(key) is not False for key in (
            "external_custody_accessed", "real_materialization_receipt_used", "real_product_metadata_read",
            "real_product_raster_header_opened", "real_product_pixel_values_examined", "network_requests_performed",
            "authentication_performed",
        ))
    ):
        fail("Sentinel-1 amended synthetic validation or activity boundary differs")
    if (
        radar_label_real_002.get("receipt_id") != "NEPAL-S1-MATERIALIZED-INPUT-READINESS-REAL-002"
        or radar_label_real_002.get("status") != "pass_partial_pre_event_header_readiness_only"
        or radar_label_real_002.get("bindings", {}).get("contract_sha256") != sha256("config/qa/radar-input-readiness-contract-amendment-001.json")
        or radar_label_real_002.get("runtime") != {"product": "ArcGISPro", "version": "3.7.1", "license_level": "Advanced"}
        or radar_label_real_002.get("decision", {}).get("ready_source_count") != 3
        or radar_label_real_002.get("decision", {}).get("complete_before_after_pair") is not False
        or radar_label_real_002.get("decision", {}).get("baseline_processing_released") is not False
    ):
        fail("Sentinel-1 amended real-002 receipt identity or aggregate result differs")
    if set(radar_label_real_002.get("products", {})) != {"M1-SRC-001", "M1-SRC-002", "M1-SRC-003"}:
        fail("Sentinel-1 amended real-002 source set differs")
    for source_id, product in radar_label_real_002.get("products", {}).items():
        annotations = product.get("annotations", {})
        headers = product.get("raster_headers", {})
        if (
            product.get("inventory", {}).get("status") != "pass_inventory_only"
            or product.get("inventory", {}).get("errors") != []
            or product.get("decision", {}).get("status") != "pass_header_readability_only"
            or product.get("decision", {}).get("errors") != []
            or set(annotations) != {"vv", "vh"}
            or set(headers) != {"vv", "vh"}
        ):
            fail(f"Sentinel-1 amended real-002 source decision differs for {source_id}")
        for polarization in ("vv", "vh"):
            annotation = annotations[polarization]
            header = headers[polarization]
            if (
                annotation.get("pixel_value") != "Detected"
                or annotation.get("errors") != []
                or annotation.get("orbit_times_strictly_increasing") is not True
                or annotation.get("orbit_vectors_finite") is not True
                or header.get("format") != "TIFF"
                or header.get("band_count") != 1
                or header.get("pixel_type") != "U16"
                or header.get("width") != annotation.get("number_of_samples")
                or header.get("height") != annotation.get("number_of_lines")
            ):
                fail(f"Sentinel-1 amended real-002 annotation or header differs for {source_id} {polarization}")
    real_002_activity = radar_label_real_002.get("activity", {})
    if (
        real_002_activity.get("external_materialization_inventory_unchanged") is not True
        or real_002_activity.get("selected_materialized_files_rehashed") is not True
        or real_002_activity.get("all_real_annotation_metadata_parsed") is not True
        or real_002_activity.get("all_real_measurement_raster_headers_opened_with_arcgis") is not True
        or any(real_002_activity.get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "real_product_pixel_values_examined", "derived_raster_written",
        ))
    ):
        fail("Sentinel-1 amended real-002 activity boundary differs")
    real_002_reconciliation_bindings = radar_label_real_002_reconciliation.get("bindings", {})
    real_002_external = radar_label_real_002_reconciliation.get("external_custody_reverification", {})
    real_002_disposition = radar_label_real_002_reconciliation.get("disposition", {})
    real_002_assertions = radar_label_real_002_reconciliation.get("assertions", {})
    if (
        radar_label_real_002_reconciliation.get("status") != "pass_partial_pre_event_header_readiness_only_post_observation_no_downstream_release"
        or real_002_reconciliation_bindings.get("amended_contract_sha256") != sha256("config/qa/radar-input-readiness-contract-amendment-001.json")
        or real_002_reconciliation_bindings.get("real_receipt_sha256") != sha256("records/readiness/radar-input/m2-s1-input-readiness-real-002.json")
        or real_002_reconciliation_bindings.get("approval_sha256") != sha256("records/source-gates/m2-radar-input-readiness-amendment-approval.json")
        or real_002_reconciliation_bindings.get("original_real_001_receipt_sha256") != "feab3645709df16306c81dae959a8693925a7c6f919f2a1e414cf3765c3a5b0c"
        or radar_label_real_002_reconciliation.get("publication_gate", {}).get("commit_sha") != "c05e1e26c8ee8dd8755573524da90c2080de4bd7"
        or radar_label_real_002_reconciliation.get("publication_gate", {}).get("github_actions_run_id") != 33910395201
        or radar_label_real_002_reconciliation.get("publication_gate", {}).get("github_actions_conclusion") != "success"
        or radar_label_real_002_reconciliation.get("observed_result", {}).get("source_pass_count") != 3
        or radar_label_real_002_reconciliation.get("observed_result", {}).get("source_block_count") != 0
        or radar_label_real_002_reconciliation.get("observed_result", {}).get("blocking_errors") != []
        or real_002_external.get("status") != "pass_exact_attempt_inventories_and_all_safe_hashes_unchanged"
        or real_002_external.get("attempt_count") != 3
        or real_002_external.get("attempt_file_count") != 87
        or real_002_external.get("safe_file_count") != 78
        or real_002_external.get("safe_total_bytes") != 5183550209
        or real_002_external.get("added_sidecar_count") != 0
        or real_002_disposition.get("post_observation_correction") is not True
        or real_002_disposition.get("blind_or_independent_validation") is not False
        or real_002_disposition.get("real_001_remains_block") is not True
        or real_002_disposition.get("real_002_maximum_invocations_consumed") != 1
        or real_002_disposition.get("automatic_retry_authorized") is not False
        or real_002_disposition.get("baseline_processing_released") is not False
        or any(real_002_assertions.get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "real_product_pixel_values_examined", "derived_raster_written", "pixel_usability_established",
            "complete_pair_established", "baseline_processing_released", "change_established",
            "scientific_admission_authorized", "sentinel_recovery_authority_created", "orbit_recovery_authority_created",
        ))
    ):
        fail("Sentinel-1 amended real-002 reconciliation differs or overclaims")
    radar_label_unit = {unit.get("id"): unit for unit in active_m2.get("units", [])}.get("M2-RADAR-INPUT-LABEL-AMEND", {})
    if (
        radar_label_unit.get("status") != "complete"
        or radar_label_unit.get("disposition") != "pass"
        or radar_label_unit.get("gates", {}).get("publication_ci_run_id") != 33910395201
        or radar_label_unit.get("gates", {}).get("real_002_invocation_count") != 1
        or radar_label_unit.get("exit_condition_delta", {}).get("decision_value") != "risk_reduction"
        or radar_label_unit.get("retained_failures", [{}])[0].get("receipt_sha256") != "feab3645709df16306c81dae959a8693925a7c6f919f2a1e414cf3765c3a5b0c"
        or radar_label_unit.get("retained_failures", [{}])[0].get("reclassified") is not False
    ):
        fail("active M2 radar input label amendment unit differs")
    if aoi_reconciliation["contract_sha256"] != sha256("reviews/m1-aoi/review-contract.json"):
        fail("AOI reconciliation does not bind the exact historical review contract")
    if approval["status"] != "approved" or approval["reviewed_aoi_sha256"] != sha256("config/aoi/draft-study-areas.geojson"):
        fail("AOI approval does not bind the exact reviewed geometry")
    if projected_aoi.get("spatialReference", {}).get("wkid") != 32645 or len(projected_aoi.get("features", [])) != 3:
        fail("approved ArcGIS AOI must contain three EPSG:32645 features")
    if arcgis_receipt["status"] != "pass" or arcgis_receipt["input_sha256"] != sha256("config/aoi/approved-study-areas-epsg32645.json"):
        fail("ArcGIS AOI validation receipt does not bind the projected artifact")
    expected_summary = {
        "candidate_count": 10,
        "proposed_accept_count": 8,
        "proposed_defer_count": 2,
        "proposed_reject_count": 0,
        "proposed_acquisition_catalog_bytes": 12451940706,
        "proposed_acquisition_catalog_gib": 11.597,
        "pixel_usability_established_count": 0,
    }
    if manifest["status"] != "candidate_for_owner_review" or manifest["summary"] != expected_summary:
        fail("candidate source-manifest state or summary is invalid")
    if any(record["local_custody"]["status"] != "not_acquired" for record in manifest["records"]):
        fail("candidate manifest must not claim full-product custody")
    if any(record["review_status"] != "candidate_manifest_not_approved" for record in manifest["records"]):
        fail("reviewed manifest bytes must remain immutable; approval belongs in the separate approval record")
    bundle_digest = sha256("reviews/m1-manifest/review-bundle.json")
    if manifest_bundle["candidate_identity"] != f"SOURCE-MANIFEST-SHA256:{sha256('records/source-manifest.json')}":
        fail("review bundle does not bind the exact source manifest")
    if manifest_contract["review_bundle"]["manifest_sha256"] != bundle_digest:
        fail("review contract does not bind the exact review bundle")
    if manifest_response["completed"] is not False or manifest_response["reviewer"]["attestation"] is not False:
        fail("public manifest response template must remain blank after the private exact response is locked")
    if manifest_reconciliation["contract_sha256"] != sha256("reviews/m1-manifest/review-contract.json"):
        fail("manifest reconciliation does not bind the exact review contract")
    if manifest_approval["status"] != "approved":
        fail("source manifest approval status is not approved")
    if manifest_approval["review_bundle_manifest_sha256"] != bundle_digest:
        fail("source manifest approval does not bind the exact review bundle")
    if manifest_approval["reviewed_manifest_sha256"] != sha256("records/source-manifest.json"):
        fail("source manifest approval does not bind the exact candidate manifest")
    if manifest_approval["review_reconciliation_sha256"] != sha256("records/source-gates/source-manifest-review-reconciliation.json"):
        fail("source manifest approval does not bind the exact reconciliation")
    if manifest_approval["locked_response_sha256"] != manifest_reconciliation["response_sha256"]:
        fail("source manifest approval and reconciliation response hashes differ")
    if manifest_approval["decision_counts"] != {"approve": 1, "revise": 0, "defer": 0}:
        fail("source manifest approval decision counts are invalid")
    if units["M1-AOI"]["status"] != "complete" or units["M1-MANIFEST"]["status"] != "complete":
        fail("M1 control units do not reflect the completed AOI and manifest gates")
    if any(condition["status"] != "pass" for condition in contract["exit_conditions"]):
        fail("all M1 exit conditions must pass")

    expected_plan_selection = {
        "approved_candidate_count": 8,
        "deferred_candidate_count": 2,
        "rejected_candidate_count": 0,
        "planned_download_count": 8,
        "catalog_content_length_bytes": 12451940706,
        "catalog_content_length_gib": 11.597,
    }
    if acquisition_plan["status"] != "candidate_for_owner_review" or acquisition_plan["selection"] != expected_plan_selection:
        fail("M2 acquisition plan state or selection is invalid")
    if acquisition_plan["source_manifest_sha256"] != sha256("records/source-manifest.json"):
        fail("M2 acquisition plan does not bind the exact approved manifest")
    if acquisition_plan["source_manifest_approval_sha256"] != sha256("records/source-gates/source-manifest-approval.json"):
        fail("M2 acquisition plan does not bind the exact manifest approval")
    if len(acquisition_plan["records"]) != 8 or any(record["acquisition_status"] != "not_authorized" for record in acquisition_plan["records"]):
        fail("M2 plan must contain eight exact products with no acquisition authorization")
    if acquisition_plan["custody"]["root_creation_status"] != "not_authorized":
        fail("M2 plan must not claim custody-root creation authority")
    if m2_proposal["status"] != "proposed" or m2_proposal["authority"]["mode"] != "not_granted":
        fail("M2 proposal must remain proposed and non-authorizing")
    if m2_proposal["authority"]["candidate_plan_sha256"] != sha256("records/acquisition-plan.json"):
        fail("M2 proposal does not bind the exact acquisition plan")
    if m2_contract["review_bundle"]["manifest_sha256"] != sha256("reviews/m2-activation/review-bundle.json"):
        fail("M2 review contract does not bind the exact review bundle")
    if m2_bundle["candidate_identity"] != f"ACQUISITION-PLAN-SHA256:{sha256('records/acquisition-plan.json')}":
        fail("M2 review bundle does not bind the exact acquisition plan")
    if m2_response["completed"] is not False or m2_response["reviewer"]["attestation"] is not False:
        fail("M2 public blank response must remain an unchanged historical review template")
    if m2_surface_receipt["status"] != "pass_with_retained_failure":
        fail("M2 review surface receipt must preserve its remediated visual failure")
    if m2_surface_receipt["surface_sha256"] != sha256("docs/assets/m2-controlled-acquisition-review.png"):
        fail("M2 surface receipt does not bind the exact rendered review surface")
    if m2_surface_receipt["renderer_sha256"] != sha256("scripts/render_m2_activation_review.py"):
        fail("M2 surface receipt does not bind the exact renderer")
    intake_extensions = intake_contract.get("extensions", {})
    if intake_extensions.get("status") != "candidate_static_control_not_authorized":
        fail("M2 intake contract must remain a non-authorizing candidate")
    if intake_extensions.get("source_plan_sha256") != sha256("records/acquisition-plan.json"):
        fail("M2 intake contract does not bind the exact acquisition plan")
    if intake_extensions.get("m2_proposal_sha256") != sha256("contracts/milestone-002-proposal.json"):
        fail("M2 intake contract does not bind the exact proposal")
    if intake_extensions.get("activation_review_bundle_sha256") != sha256("reviews/m2-activation/review-bundle.json"):
        fail("M2 intake contract does not bind the exact pending review bundle")
    if intake_contract.get("collision_policy") != "fail" or intake_contract.get("promotion_mode") != "atomic-no-replace":
        fail("M2 intake contract must fail on collision and use atomic no-replace promotion")
    if intake_contract.get("secret_policy") != "references-only":
        fail("M2 intake contract must keep secret values out of custody records")
    if len(intake_contract.get("assets", [])) != 8:
        fail("M2 intake contract must contain exactly eight approved assets")
    intake_source_ids = set()
    for asset in intake_contract["assets"]:
        if asset.get("state") != "planned" or asset.get("attempts") != []:
            fail("M2 intake assets must remain planned with no attempts before activation")
        if asset.get("expected", {}).get("sha256") is not None or asset.get("expected", {}).get("size_bytes") is not None:
            fail("M2 intake must not mistake catalog metadata for authenticated transfer identity")
        extensions = asset.get("extensions", {})
        source_id = extensions.get("source_id")
        intake_source_ids.add(source_id)
        provider_id = extensions.get("provider_product_id")
        expected_uri = f"https://download.dataspace.copernicus.eu/odata/v1/Products({provider_id})/$value"
        if asset.get("source", {}).get("uri") != expected_uri:
            fail(f"M2 intake route differs for {source_id}")
        if asset.get("source", {}).get("authorization_ref", "").split(":", 1)[0] != "pending":
            fail(f"M2 intake asset {source_id} must preserve pending authorization")
    if intake_source_ids != {record["source_id"] for record in acquisition_plan["records"]}:
        fail("M2 intake source set differs from the exact approved acquisition plan")

    if m2_activation.get("status") != "approved" or m2_activation.get("review_bundle_manifest_sha256") != sha256("reviews/m2-activation/review-bundle.json"):
        fail("M2 activation approval does not bind the exact reviewed bundle")
    if m2_activation.get("acquisition_plan_sha256") != sha256("records/acquisition-plan.json"):
        fail("M2 activation approval does not bind the exact acquisition plan")
    if m2_activation.get("locked_response_sha256") != m2_reconciliation.get("response_sha256"):
        fail("M2 activation and reconciliation response hashes differ")
    if m2_reconciliation.get("status") != "reconciled_exact_human_response" or m2_reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        fail("M2 activation response is not one exact reconciled approval")
    if m2_reconciliation.get("human_decisions_fabricated") is not False:
        fail("M2 activation reconciliation must reject fabricated decisions")
    if active_m2.get("status") != "active" or active_m2.get("authority", {}).get("mode") != "inherited":
        fail("M2 active contract state or authority mode is invalid")
    if active_m2.get("authority", {}).get("authority_ref") != "records/source-gates/m2-activation-approval.json":
        fail("M2 active contract does not cite the exact activation approval")
    if active_m2.get("authority", {}).get("approval_sha256") != sha256("records/source-gates/m2-activation-approval.json"):
        fail("M2 active contract approval hash differs")
    m2_units = {unit["id"]: unit for unit in active_m2.get("units", [])}
    if m2_units.get("M2-CUSTODY-PREFLIGHT", {}).get("disposition") != "pass" or "M2-ACQUIRE" not in m2_units:
        fail("M2 units do not preserve the passing preflight and acquisition unit")
    if m2_units["M2-ACQUIRE"].get("gates", {}).get("custody_initialization") != "pass":
        fail("M2 acquisition unit does not bind verified custody initialization")
    if m2_source_gate.get("decision", {}).get("status") != "ready" or len(m2_source_gate.get("sources", [])) != 8:
        fail("M2 live source gate must be ready for exactly eight products")
    if m2_source_gate.get("authority", {}).get("authority_ref") != "records/source-gates/m2-activation-approval.json":
        fail("M2 live source gate does not inherit the exact activation approval")
    if any(criterion.get("status") != "pass" for source in m2_source_gate["sources"] for criterion in source.get("criteria", [])):
        fail("M2 live source gate contains a non-passing criterion")
    if m2_preflight.get("status") != "pass_no_external_mutation":
        fail("M2 preflight did not preserve its non-mutating passing state")
    if m2_preflight.get("source_gate", {}).get("sha256") != sha256("records/source-gates/m2-live-source-gate.json"):
        fail("M2 preflight does not bind the exact live source gate")
    if len(m2_preflight.get("product_checks", [])) != 8 or any(item.get("status") != "pass" for item in m2_preflight["product_checks"]):
        fail("M2 preflight must preserve eight passing exact-product checks")
    if m2_preflight.get("paths", {}).get("external_data_root_exists_before_preflight") is not False:
        fail("M2 preflight must establish that the external root was absent before mutation")
    if m2_preflight.get("access", {}).get("credential_values_read_or_recorded") is not False or m2_preflight.get("access", {}).get("authentication_performed") is not False:
        fail("M2 preflight must not read credentials or authenticate")

    if m2_terms_reconciliation.get("status") != "pass_scope_relevant_terms_identity_preserved_no_acceptance":
        fail("M2 terms-page reconciliation is not passing")
    initial_terms = m2_terms_reconciliation.get("initial_evidence", {})
    if (
        initial_terms.get("source_gate_sha256") != sha256("records/source-gates/m2-live-source-gate.json")
        or initial_terms.get("preflight_sha256") != sha256("records/acquisition/preflight.json")
        or initial_terms.get("terms_rendered_page_sha256") != "17ebc07dc1fe685b6a3ef0ec64fd376dc1bf4b500e2d583aded19a53fdd55674"
        or initial_terms.get("sentinel_legal_notice_sha256") != "fa2955ff48a1d82e77fc7296d63681670ecdb9d2811a0505ae60d0683b62fa64"
    ):
        fail("M2 terms-page reconciliation no longer binds the initial evidence")
    current_terms = m2_terms_reconciliation.get("current_evidence", {})
    terms_decision = m2_terms_reconciliation.get("decision", {})
    terms_mutations = m2_terms_reconciliation.get("mutations_performed", {})
    if (
        current_terms.get("terms_rendered_page_sha256") != "97a8ca9a5ebe8eb5cc24dfdadb926d60de04efd30a1b23ea521da564ca5ab3f0"
        or current_terms.get("terms_normalized_text_sha256") != "22cf55ad3949e8eaee715780654be9eb0e8648a2808d6ba007b47c9849ab2b01"
        or current_terms.get("terms_structured_date_modified") != "2026-05-05T08:04:39+0200"
        or current_terms.get("sentinel_legal_notice_sha256") != "fa2955ff48a1d82e77fc7296d63681670ecdb9d2811a0505ae60d0683b62fa64"
        or len(current_terms.get("required_phrases_present", [])) != 6
    ):
        fail("M2 terms-page current legal identity differs")
    if (
        terms_decision.get("rendered_page_bytes_changed") is not True
        or terms_decision.get("scope_relevant_legal_section_current") is not True
        or terms_decision.get("official_structured_terms_document_modified_after_initial_preflight") is not False
        or terms_decision.get("exact_linked_sentinel_legal_notice_unchanged") is not True
        or terms_decision.get("terms_or_account_action_performed") is not False
        or terms_mutations.get("credential_values_read_or_recorded") is not False
        or terms_mutations.get("terms_acceptance") is not False
        or terms_mutations.get("product_payload_bytes_received") != 0
        or terms_mutations.get("external_custody_mutated") is not False
    ):
        fail("M2 terms-page reconciliation weakens the no-mutation or no-acceptance boundary")

    if (
        m2_source_gate_refresh.get("decision", {}).get("status") != "ready"
        or len(m2_source_gate_refresh.get("sources", [])) != 8
        or any(criterion.get("status") != "pass" for source in m2_source_gate_refresh.get("sources", []) for criterion in source.get("criteria", []))
        or m2_source_gate_refresh.get("authority", {}).get("authority_ref") != "records/source-gates/m2-activation-approval.json"
    ):
        fail("M2 refreshed live source gate is not ready for exactly eight passing products")
    refresh_extensions = m2_source_gate_refresh.get("extensions", {})
    if (
        refresh_extensions.get("refresh_of_sha256") != sha256("records/source-gates/m2-live-source-gate.json")
        or refresh_extensions.get("terms_reconciliation_sha256") != sha256("records/source-gates/m2-terms-page-reconciliation.json")
        or refresh_extensions.get("terms_acceptance_performed") is not False
        or refresh_extensions.get("product_payload_bytes_received") != 0
    ):
        fail("M2 refreshed source gate bindings or no-mutation boundary differ")

    if (
        m2_preflight_refresh.get("status") != "pass_no_external_mutation"
        or m2_preflight_refresh.get("base_preflight", {}).get("sha256") != sha256("records/acquisition/preflight.json")
        or m2_preflight_refresh.get("source_gate", {}).get("sha256") != sha256("records/source-gates/m2-live-source-gate-refresh.json")
        or m2_preflight_refresh.get("terms_reconciliation", {}).get("sha256") != sha256("records/source-gates/m2-terms-page-reconciliation.json")
        or len(m2_preflight_refresh.get("product_checks", [])) != 8
        or any(item.get("status") != "pass" for item in m2_preflight_refresh.get("product_checks", []))
        or m2_preflight_refresh.get("intake_state") != {"authorized_count": 8, "attempt_count": 0, "promoted_count": 0, "failed_count": 0}
    ):
        fail("M2 Sentinel preflight refresh or exact-product state differs")
    refresh_pages = {item.get("page_id"): item for item in m2_preflight_refresh.get("official_page_checks", [])}
    if set(refresh_pages) != {"odata-download-documentation", "token-documentation", "terms-and-conditions", "sentinel-data-legal-notice"}:
        fail("M2 Sentinel preflight refresh does not contain four exact official pages")
    refreshed_terms_page = refresh_pages.get("terms-and-conditions", {})
    if (
        refreshed_terms_page.get("comparison_mode") != "normalized_terms_section_sha256"
        or refreshed_terms_page.get("terms_identity", {}).get("normalized_text_sha256") != current_terms.get("terms_normalized_text_sha256")
        or refreshed_terms_page.get("terms_identity", {}).get("structured_date_modified") != current_terms.get("terms_structured_date_modified")
        or refreshed_terms_page.get("rendered_page_changed_from_initial") is not True
    ):
        fail("M2 Sentinel transfer does not bind the reconciled legal-section identity")
    if any(refresh_pages[page_id].get("comparison_mode") != "raw_sha256" for page_id in ("odata-download-documentation", "token-documentation", "sentinel-data-legal-notice")):
        fail("unchanged official access and legal-notice pages must retain exact-byte binding")
    if (
        m2_preflight_refresh.get("paths", {}).get("custody_initialized") is not True
        or m2_preflight_refresh.get("paths", {}).get("existing_destination_or_staging_paths") != []
        or m2_preflight_refresh.get("storage", {}).get("status") != "pass"
        or m2_preflight_refresh.get("access", {}).get("credential_values_read_or_recorded") is not False
        or m2_preflight_refresh.get("access", {}).get("authentication_performed") is not False
        or m2_preflight_refresh.get("mutations_performed", {}).get("product_payload_bytes_received") != 0
        or m2_preflight_refresh.get("mutations_performed", {}).get("external_custody") is not False
    ):
        fail("M2 Sentinel preflight refresh invents access, mutation, or nonempty custody")

    active_extensions = active_intake.get("extensions", {})
    if active_extensions.get("status") not in {
        "active_authorized_preflight_passed_custody_initialized",
        "active_four_promoted_four_authorized_continuation_review_required",
        "active_eight_promoted_container_verified_materialization_review_required",
    } or active_extensions.get("custody_initialized") is not True:
        fail("active M2 intake must record initialized custody")
    if active_extensions.get("source_gate_sha256") != sha256("records/source-gates/m2-live-source-gate.json") or active_extensions.get("preflight_sha256") != sha256("records/acquisition/preflight.json"):
        fail("active M2 intake does not bind the live gate and preflight")
    if active_extensions.get("custody_initialization_sha256") != sha256("records/acquisition/custody-initialization.json"):
        fail("active M2 intake does not bind the custody receipt")
    if active_intake.get("collision_policy") != "fail" or active_intake.get("promotion_mode") != "atomic-no-replace" or active_intake.get("secret_policy") != "references-only":
        fail("active M2 intake weakens collision, promotion, or secret controls")
    if sha256("records/acquisition/active-intake-initial-snapshot.json") != INITIAL_ACTIVE_INTAKE_SHA256:
        fail("initial active-intake snapshot no longer has its activation-time identity")
    if initial_active_intake.get("assets") != active_intake.get("assets") and all(
        asset.get("state") == "authorized" and asset.get("attempts") == []
        for asset in active_intake.get("assets", [])
    ):
        fail("unattempted active intake differs from its immutable initial snapshot")
    acquisition_progress = validate_acquisition_progress(
        active_intake,
        initial_active_intake,
        acquisition_plan,
        root=ROOT,
        verify_external=False,
    )
    if acquisition_progress.get("status") != "pass":
        fail("active M2 acquisition progress is invalid: " + "; ".join(acquisition_progress.get("errors", [])))
    state_counts = acquisition_progress.get("state_counts", {})
    try:
        expected_checkpoint = derive_checkpoint(state_counts)["checkpoint_id"]
    except ValueError as exc:
        fail(f"active M2 acquisition checkpoint is ambiguous: {exc}")
    continuation_review_unit = m2_units.get("M2-SENTINEL-CONTINUATION-001-REVIEW", {})
    continuation_review_ready = (
        state_counts == {"authorized": 4, "promoted": 4}
        and continuation_review_unit.get("status") == "ready"
        and continuation_review_unit.get("gates", {}).get("human_decision_count") == 0
        and continuation_review_unit.get("gates", {}).get("continuation_authorized") is False
    )
    continuation_review_approved = (
        continuation_review_unit.get("status") == "complete"
        and continuation_review_unit.get("disposition") == "pass"
        and continuation_review_unit.get("human_gate") is True
        and continuation_review_unit.get("gates", {}).get("human_decision_count") == 1
        and continuation_review_unit.get("gates", {}).get("attestation") is True
        and continuation_review_unit.get("gates", {}).get("continuation_authorized") is True
        and continuation_review_unit.get("gates", {}).get("implementation_authorized") is True
    )
    continuation_completed = bool(
        state_counts == {"promoted": 8}
        and current_container_verification_complete(ROOT, state_counts)
        and continuation_success.get("status") == "reconciled_all_eight_promoted_container_pass"
        and continuation_postsuccess.get("status") == "reconciled_eight_promoted_container_verified_transfer_cohort_complete"
    )
    if continuation_completed:
        expected_checkpoint = "M2-VERIFY"
    elif continuation_review_ready or continuation_review_approved:
        expected_checkpoint = "M2-ACQUISITION-REVIEW"
    if (
        profile["current_checkpoint"]["checkpoint_id"] != expected_checkpoint
        or goal.get("current_checkpoint") != expected_checkpoint
        or active_m2.get("handoff", {}).get("current_checkpoint") != expected_checkpoint
    ):
        fail(f"profile, goal, and milestone handoff must reconcile to {expected_checkpoint}")
    expected_recovery_next_action = "Complete and locally validate the exact recovery-002 implementation, publish the exact commit, and require successful public CI before activation, no-payload preflight, credential access, or transfer."
    expected_continuation_next_action = "Review exact Sentinel continuation-001 bundle 382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b and proposal d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1; do not implement, request a token, or acquire another product before a completed owner decision."
    expected_continuation_implementation_next_action = "Publish the exact continuation-001 implementation and verify successful public CI; do not activate, request a token, or access payload bytes before the publication gate and final no-payload preflight pass."
    expected_post_container_next_action = "Prepare and review an exact bounded materialization and pixel-readiness plan for the five not-yet-materialized products. Do not materialize, decode pixels, run baselines, or start orbit recovery before the separate gates are satisfied."
    acquire_unit = m2_units.get("M2-ACQUIRE", {})
    if continuation_completed:
        gates = acquire_unit.get("gates", {})
        implementation_unit = m2_units.get("M2-SENTINEL-CONTINUATION-001-IMPLEMENTATION", {})
        implementation_gates = implementation_unit.get("gates", {})
        verify_unit = m2_units.get("M2-VERIFY", {})
        if (
            implementation_unit.get("status") != "complete"
            or implementation_gates.get("public_ci") != "pass"
            or implementation_gates.get("public_commit") != "68ac0484d598790cc8c47a8747a674b7d5d9de73"
            or implementation_gates.get("public_ci_run_id") != 33942997642
            or implementation_gates.get("terminal_code") != "continuation_001_all_four_succeeded"
            or implementation_gates.get("success_reconciliation_sha256") != sha256("records/acquisition/sentinel-continuation-001-success-reconciliation.json")
            or implementation_gates.get("postsuccess_reconciliation_sha256") != sha256("records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json")
            or acquire_unit.get("status") != "complete"
            or acquire_unit.get("disposition") != "complete_exact_eight_promoted_container_verified"
            or gates.get("continuation_supervisor_status") != "succeeded_all_four"
            or gates.get("continuation_attempt_count") != 4
            or gates.get("promoted_source_count") != 8
            or gates.get("container_verified_source_count") != 8
            or gates.get("postsuccess_reconciliation_sha256") != sha256("records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json")
            or verify_unit.get("status") != "in_progress"
            or verify_unit.get("gates", {}).get("container_verified_count") != 8
            or verify_unit.get("gates", {}).get("materialized_source_count") != 3
            or verify_unit.get("gates", {}).get("materialization_and_pixel_readiness") != "separately_gated_pending"
            or profile.get("current_checkpoint", {}).get("next_action") != expected_post_container_next_action
            or active_m2.get("handoff", {}).get("next_action") != expected_post_container_next_action
        ):
            fail("M2 continuation completion and post-container handoff differ")
    elif continuation_review_approved:
        gates = acquire_unit.get("gates", {})
        implementation_unit = m2_units.get("M2-SENTINEL-CONTINUATION-001-IMPLEMENTATION", {})
        review_gates = continuation_review_unit.get("gates", {})
        implementation_gates = implementation_unit.get("gates", {})
        if (
            continuation_review_unit.get("outputs") != [
                "records/source-gates/m2-sentinel-continuation-001-approval.json",
                "records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json",
            ]
            or review_gates.get("review_bundle_sha256") != "382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b"
            or review_gates.get("proposal_sha256") != "d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1"
            or review_gates.get("approval_sha256") != sha256("records/source-gates/m2-sentinel-continuation-001-approval.json")
            or review_gates.get("review_reconciliation_sha256") != sha256("records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json")
            or review_gates.get("locked_response_sha256") != "add004d26f7a35ed1b657089dae1c1f68f01eba495c0c4edb35cee943a13cb39"
            or implementation_unit.get("status") != "in_progress"
            or implementation_unit.get("action_class") != "external_publication"
            or implementation_unit.get("depends_on") != ["M2-SENTINEL-CONTINUATION-001-REVIEW"]
            or implementation_gates.get("implementation_readiness_sha256") != sha256("records/acquisition/sentinel-continuation-001-implementation-readiness.json")
            or implementation_gates.get("focused_test_count") != 23
            or implementation_gates.get("full_repository_test_count") != 317
            or implementation_gates.get("windows_detached_process_tested") is not True
            or implementation_gates.get("safe_error_and_secret_exposure_tests") != "pass"
            or implementation_gates.get("m1_src_004_request_permitted") is not False
            or implementation_gates.get("public_ci") != "pending_after_failed_attempt_001"
            or implementation_gates.get("credential_entry_permitted_now") is not False
            or implementation_gates.get("payload_request_permitted_now") is not False
            or implementation_unit.get("retained_failures") != [
                {
                    "record_ref": "records/acquisition/sentinel-continuation-001-implementation-readiness-attempt-001-superseded.json",
                    "record_sha256": "86af300807b6db28e97deb6b8188d609f02bf0bed3044741e1eb124eddc28c48",
                    "reason": "Superseded before publication after adding the exact prelaunch Git-state boundary.",
                },
                {
                    "record_ref": "records/acquisition/sentinel-continuation-001-implementation-readiness-attempt-002-superseded.json",
                    "record_sha256": "f52d989352541a1fb28dacf858fd14408de28bde84fcb9355154ea623df48fad",
                    "reason": "Superseded after public CI exposed a Linux synthetic-test dependency on the absent external Windows custody root.",
                },
                {
                    "record_ref": "records/acquisition/sentinel-continuation-001-implementation-publication-attempt-001-failure.json",
                    "record_sha256": "17035284194fad3645f95d2162a6ff639f6743e2d849c67fce4e3505340cc2f0",
                    "reason": "Exact commit 114cb663dbaf13bd286d26f92167ea4a9b7ec420 failed public CI run 33942595168 in the synthetic pre-attempt portability test.",
                },
            ]
            or acquire_unit.get("status") != "deferred"
            or acquire_unit.get("disposition") != "defer"
            or "M2-SENTINEL-CONTINUATION-001-IMPLEMENTATION" not in acquire_unit.get("depends_on", [])
            or gates.get("continuation_review") != "completed_approved_exact"
            or gates.get("continuation_approval_sha256") != sha256("records/source-gates/m2-sentinel-continuation-001-approval.json")
            or gates.get("continuation_review_reconciliation_sha256") != sha256("records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json")
            or gates.get("continuation_human_decision_count") != 1
            or gates.get("continuation_implementation_authorized") is not True
            or gates.get("continuation_publication_gate") != "pending_after_failed_attempt_001"
            or gates.get("continuation_transfer_authorized_after_public_ci_and_final_preflight") is not True
            or gates.get("continuation_transfer_authorized_now") is not False
            or gates.get("continuation_authorized_now") is not False
            or profile.get("current_checkpoint", {}).get("next_action") != expected_continuation_implementation_next_action
            or active_m2.get("handoff", {}).get("next_action") != expected_continuation_implementation_next_action
        ):
            fail("M2 continuation approval and implementation-publication gate differ")
        supervisor_failures = acquire_unit.get("supervisor_failures", [])
        if (
            len(supervisor_failures) != 1
            or supervisor_failures[0].get("phase") != "continuation_live_preflight"
            or supervisor_failures[0].get("terminal_code") != "unexpected_supervisor_failure"
            or supervisor_failures[0].get("exact_cause_established") is not False
            or supervisor_failures[0].get("continuation_attempt_started") is not False
            or supervisor_failures[0].get("retry_automatically_authorized") is not False
        ):
            fail("M2 acquisition unit does not retain the exact supervisor failure boundary")
    elif continuation_review_ready:
        gates = acquire_unit.get("gates", {})
        if (
            acquire_unit.get("status") != "deferred"
            or acquire_unit.get("disposition") != "defer"
            or gates.get("recovery_002_publication_gate") != "pass"
            or gates.get("recovery_002_publication_commit") != "59fa8f0c298de2fab7f5e6747e70bec3b0ad1726"
            or gates.get("recovery_002_public_ci_run_id") != 33921973385
            or gates.get("recovery_002_transfer_status") != "succeeded"
            or gates.get("recovery_002_container_status") != "pass_container_only"
            or gates.get("continuation_supervisor_status") != "failed_before_first_continuation_attempt"
            or gates.get("continuation_attempt_count") != 0
            or gates.get("continuation_payload_request_count") != 0
            or gates.get("continuation_review_bundle_sha256") != "382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b"
            or gates.get("continuation_proposal_sha256") != "d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1"
            or gates.get("continuation_authorized_now") is not False
            or gates.get("recovery_002_outcome_reconciliation_sha256") != sha256("records/acquisition/sentinel-recovery-002-supervisor-reconciliation-001.json")
            or profile.get("current_checkpoint", {}).get("next_action") != expected_continuation_next_action
            or active_m2.get("handoff", {}).get("next_action") != expected_continuation_next_action
        ):
            fail("M2 acquisition unit and handoff do not preserve the stopped continuation review gate")
        supervisor_failures = acquire_unit.get("supervisor_failures", [])
        if (
            len(supervisor_failures) != 1
            or supervisor_failures[0].get("phase") != "continuation_live_preflight"
            or supervisor_failures[0].get("terminal_code") != "unexpected_supervisor_failure"
            or supervisor_failures[0].get("exact_cause_established") is not False
            or supervisor_failures[0].get("continuation_attempt_started") is not False
            or supervisor_failures[0].get("retry_automatically_authorized") is not False
        ):
            fail("M2 acquisition unit does not retain the exact supervisor failure boundary")
    elif state_counts.get("failed", 0):
        if acquire_unit.get("status") != "in_progress":
            fail("M2 acquisition unit must remain blocked on the recovery-002 publication gate")
        if acquire_unit.get("disposition") != "authorized_implementation_pending_publication_gate":
            fail("M2 acquisition unit must expose the approved implementation and pending publication gate")
        if acquire_unit.get("gates", {}).get("authentication") != "existing_owner_controlled_credential_reference_confirmed":
            fail("M2 acquisition unit must preserve the confirmed secret-safe credential-reference boundary")
        if acquire_unit.get("gates", {}).get("retained_failure_review") != "completed_approved_attempt_failed":
            fail("M2 acquisition unit must retain the completed approved recovery and terminal failure")
        if (
            acquire_unit.get("gates", {}).get("retained_failure_review_ref") != "reviews/m2-sentinel-recovery/review-contract.json"
            or acquire_unit.get("gates", {}).get("retained_failure_review_bundle_sha256") != expected_recovery_bundle_sha
            or acquire_unit.get("gates", {}).get("retained_failure_recovery_proposal_sha256") != expected_recovery_proposal_sha
            or acquire_unit.get("gates", {}).get("recovery_approval_sha256") != sha256("records/source-gates/m2-sentinel-recovery-approval.json")
            or acquire_unit.get("gates", {}).get("recovery_attempt_receipt_sha256") != sha256(recovery_receipt_ref)
            or acquire_unit.get("gates", {}).get("recovery_interruption_reconciliation_sha256") != sha256("records/acquisition/sentinel-recovery-interruption-reconciliation-001.json")
            or acquire_unit.get("gates", {}).get("automatic_retry_authorized") is not False
            or acquire_unit.get("gates", {}).get("recovery_002_review") != "completed_approved_exact"
            or acquire_unit.get("gates", {}).get("recovery_002_review_ref") != "reviews/m2-sentinel-recovery-002/review-contract.json"
            or acquire_unit.get("gates", {}).get("recovery_002_review_bundle_sha256") != expected_recovery_002_bundle_sha
            or acquire_unit.get("gates", {}).get("recovery_002_proposal_ref") != "contracts/milestone-002-sentinel-recovery-002-proposal.json"
            or acquire_unit.get("gates", {}).get("recovery_002_proposal_sha256") != expected_recovery_002_proposal_sha
            or acquire_unit.get("gates", {}).get("recovery_002_approval_ref") != "records/source-gates/m2-sentinel-recovery-002-approval.json"
            or acquire_unit.get("gates", {}).get("recovery_002_approval_sha256") != sha256("records/source-gates/m2-sentinel-recovery-002-approval.json")
            or acquire_unit.get("gates", {}).get("recovery_002_review_reconciliation_ref") != "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json"
            or acquire_unit.get("gates", {}).get("recovery_002_review_reconciliation_sha256") != sha256("records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json")
            or acquire_unit.get("gates", {}).get("recovery_002_human_decision_count") != 1
            or acquire_unit.get("gates", {}).get("recovery_002_implementation_authorized") is not True
            or acquire_unit.get("gates", {}).get("recovery_002_publication_gate") != "pending_after_failed_ci_attempt_001"
            or acquire_unit.get("gates", {}).get("recovery_002_publication_attempt_001_ref") != "records/acquisition/sentinel-recovery-002-publication-attempt-001-failure.json"
            or acquire_unit.get("gates", {}).get("recovery_002_publication_attempt_001_sha256") != sha256("records/acquisition/sentinel-recovery-002-publication-attempt-001-failure.json")
            or acquire_unit.get("gates", {}).get("recovery_002_transfer_authorized_after_public_ci_and_final_preflight") is not True
            or acquire_unit.get("gates", {}).get("recovery_002_transfer_authorized_now") is not False
            or profile.get("current_checkpoint", {}).get("next_action") != expected_recovery_next_action
            or active_m2.get("handoff", {}).get("next_action") != expected_recovery_next_action
        ):
            fail("M2 acquisition unit and current handoff do not bind the approved recovery-002 implementation gate")
        retained_failures = acquire_unit.get("retained_failures", [])
        failed_assets = [asset for asset in active_intake.get("assets", []) if asset.get("state") == "failed"]
        if len(retained_failures) != len(failed_assets):
            fail("M2 acquisition unit retained-failure count differs from active intake")
        retained_by_source = {item.get("source_id"): item for item in retained_failures if isinstance(item, dict)}
        for asset in failed_assets:
            source_id = asset.get("extensions", {}).get("source_id")
            attempt = asset.get("attempts", [{}])[0]
            retained = retained_by_source.get(source_id, {})
            if (
                retained.get("attempt_id") != attempt.get("attempt_id")
                or retained.get("failure_code") != asset.get("failure", {}).get("code")
                or retained.get("retry_automatically_authorized") is not False
            ):
                fail(f"M2 acquisition unit retained-failure binding differs for {source_id}")
        recovery_failures = acquire_unit.get("recovery_failures", [])
        if (
            len(recovery_failures) != 1
            or recovery_failures[0].get("attempt_id") != recovery_attempt_id
            or recovery_failures[0].get("failure_code") != recovery_failure_code
            or recovery_failures[0].get("partial_bytes_preserved") != 1333788672
            or recovery_failures[0].get("partial_sha256") != recovery_partial_sha256
            or recovery_failures[0].get("retry_automatically_authorized") is not False
        ):
            fail("M2 acquisition unit does not retain the exact terminal recovery failure")
    else:
        if acquire_unit.get("status") != "ready":
            fail("M2 acquisition unit must remain ready while one-product intake is incomplete and no failure is retained")
        if acquire_unit.get("gates", {}).get("authentication") != "waiting_for_secret_safe_existing_owner_credential_reference":
            fail("each M2 acquisition invocation must still require a current secret-safe credential reference")
    if custody_receipt.get("status") != "created_and_verified":
        fail("M2 custody initialization receipt is not passing")
    if custody_receipt.get("bindings", {}).get("preflight_sha256") != sha256("records/acquisition/preflight.json") or custody_receipt.get("bindings", {}).get("source_gate_sha256") != sha256("records/source-gates/m2-live-source-gate.json"):
        fail("M2 custody receipt does not bind the preflight and source gate")
    receipt_verification = custody_receipt.get("verification", {})
    if receipt_verification.get("files_downloaded") != 0 or receipt_verification.get("authentication_performed") is not False or receipt_verification.get("credential_values_read_or_recorded") is not False:
        fail("M2 custody initialization must not claim authentication or product transfer")
    if transfer_readiness.get("status") != "pass_synthetic_only_no_authentication_or_product_transfer":
        fail("M2 transfer-runner readiness receipt has an invalid status")
    readiness_bindings = transfer_readiness.get("bindings", {})
    expected_transfer_bindings = {
        "active_contract_sha256": "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb",
        "active_intake_sha256": INITIAL_ACTIVE_INTAKE_SHA256,
        "activation_approval_sha256": sha256("records/source-gates/m2-activation-approval.json"),
        "transfer_core_sha256": sha256("scripts/m2_transfer_core.py"),
        "transfer_runner_sha256": "bf02f27d90f3ef66b713763ef62e60bf66e83d5a77ca10a10f30075f4454b7ba",
        "tests_sha256": "a7dfdfedbc7170fa51a6815f1f243f860d437245ec4f7c23cf05591b15822084",
    }
    if any(readiness_bindings.get(key) != value for key, value in expected_transfer_bindings.items()):
        fail("M2 transfer-runner readiness receipt has a stale artifact binding")
    if transfer_readiness.get("test", {}).get("status") != "pass" or transfer_readiness.get("test", {}).get("test_count") != 11:
        fail("M2 transfer-runner readiness receipt must preserve eleven passing local tests")
    expected_transfer_correction_bindings = {
        "active_intake_ref": "contracts/m2-intake.json",
        "active_intake_sha256": INITIAL_ACTIVE_INTAKE_SHA256,
        "initial_intake_snapshot_ref": "records/acquisition/active-intake-initial-snapshot.json",
        "initial_intake_snapshot_sha256": sha256("records/acquisition/active-intake-initial-snapshot.json"),
        "activation_approval_ref": "records/source-gates/m2-activation-approval.json",
        "activation_approval_sha256": sha256("records/source-gates/m2-activation-approval.json"),
        "transfer_core_ref": "scripts/m2_transfer_core.py",
        "transfer_core_sha256": sha256("scripts/m2_transfer_core.py"),
        "transfer_runner_ref": "scripts/acquire_m2_product.py",
        "transfer_runner_sha256": "8a48b3bda9d729bceebf50e237f5671c967275d8203111aa8f8972aaddc3b645",
        "test_ref": "tests/test_m2_transfer_core.py",
        "test_sha256": sha256("tests/test_m2_transfer_core.py"),
        "discovery_ref": "records/acquisition/dem-acquisition-portability-correction.json",
        "discovery_sha256": sha256("records/acquisition/dem-acquisition-portability-correction.json"),
    }
    if (
        transfer_runner_correction.get("status") != "pass_future_attempt_ids_lowercase_schema_compatible"
        or transfer_runner_correction.get("bindings") != expected_transfer_correction_bindings
        or transfer_runner_correction.get("validation") != {
            "focused_test_count": 11,
            "focused_test_status": "pass",
            "full_repository_test_count": 185,
            "full_repository_test_status": "pass",
            "repository_required_file_count": 193,
            "repository_validation_status": "pass",
            "active_sentinel_intake_generic_validator": "pass",
            "example_attempt_id": "m1-src-001-20260903t170000z-abc123ef",
            "identifier_pattern": "^[a-z0-9][a-z0-9._-]{0,127}$",
        }
    ):
        fail("M2 transfer-runner attempt-ID correction differs")
    if transfer_runner_correction.get("assertions") != {
        "future_attempt_identifier_is_lowercase": True,
        "future_attempt_identifier_is_schema_compatible": True,
        "rfc3339_event_timestamps_remain_unchanged": True,
        "active_sentinel_intake_mutated": False,
        "completed_dem_attempt_identifiers_rewritten": False,
        "external_files_mutated": False,
        "network_requests_performed": False,
        "authentication_performed": False,
        "credential_values_read_or_recorded": False,
        "product_bytes_transferred": 0,
        "authority_created": False,
        "scientific_result_established": False,
    }:
        fail("M2 transfer-runner attempt-ID correction claim boundary differs")
    readiness_activity = transfer_readiness.get("activity", {})
    if readiness_activity != {
        "network_requests_performed": False,
        "authentication_performed": False,
        "credential_values_read_or_recorded": False,
        "product_bytes_transferred": 0,
        "active_intake_mutated": False,
    }:
        fail("M2 transfer-runner readiness must not claim network, authentication, credential, data, or intake mutation")
    if acquisition_progress_readiness.get("status") != "pass_preacquisition_dynamic_progress_validation":
        fail("M2 acquisition-progress readiness receipt status differs")
    progress_bindings = acquisition_progress_readiness.get("bindings", {})
    expected_historical_progress_bindings = {
        "initial_snapshot_ref": "records/acquisition/active-intake-initial-snapshot.json",
        "initial_snapshot_sha256": "a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c",
        "acquisition_plan_ref": "records/acquisition-plan.json",
        "acquisition_plan_sha256": "6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d",
        "validator_ref": "scripts/validate_m2_acquisition_progress.py",
        "validator_sha256": "fc90a85e111135133a64249151086d7032c924148bcf5cc29cbee473703a9051",
        "test_ref": "tests/test_m2_acquisition_progress.py",
        "test_sha256": "5d1c59520d803daa05ba1bfef1ddcfbdbe894566a9cfb0c50f3c7dba00e2f191",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "0811375064b8d2681690012d82234270f00022e23e94c82649c43f28ec5b7395",
        "runbook_ref": "docs/M2_EXECUTION_RUNBOOK.md",
        "runbook_sha256": "abd658d18a80f86bb3d8c4446eac9dfde7e268ffee44ee0841421838292d66ed",
    }
    if progress_bindings != expected_historical_progress_bindings:
        fail("M2 acquisition-progress readiness no longer preserves its published bindings")
    if acquisition_progress_readiness.get("validation") != {
        "focused_test_count": 9,
        "focused_test_status": "pass",
        "initial_repository_state": "pass",
        "initial_external_state": "pass",
        "initial_state_counts": {"authorized": 8},
        "synthetic_states_covered": ["authorized", "staging", "failed", "promoted"],
    }:
        fail("M2 acquisition-progress readiness validation differs")
    if acquisition_progress_readiness.get("activity") != {
        "network_requests_performed": False,
        "authentication_performed": False,
        "credential_values_read_or_recorded": False,
        "external_files_mutated": False,
        "active_intake_mutated": False,
    }:
        fail("M2 acquisition-progress readiness invents external activity")
    if (
        acquisition_progress_portability.get("status") != "pass_windows_started_event_basename_portable"
        or acquisition_progress_portability.get("trigger", {}).get("failed_ci_run_id") != 33900195532
        or acquisition_progress_portability.get("trigger", {}).get("failed_commit") != "226157b187b0475c6ee3a8849b95b76e1d02c8c1"
        or acquisition_progress_portability.get("trigger", {}).get("affected_source_ids") != [
            "M1-SRC-001", "M1-SRC-002", "M1-SRC-003", "M1-SRC-004"
        ]
        or acquisition_progress_portability.get("correction", {}).get("validator_sha256_before") != "fc90a85e111135133a64249151086d7032c924148bcf5cc29cbee473703a9051"
        or acquisition_progress_portability.get("correction", {}).get("validator_sha256_after") != "b54301d9f690b178b75995a29ad84598b6f3555ddc2e0eff735d96c331572545"
        or acquisition_progress_portability.get("correction", {}).get("test_sha256_before") != "5d1c59520d803daa05ba1bfef1ddcfbdbe894566a9cfb0c50f3c7dba00e2f191"
        or acquisition_progress_portability.get("correction", {}).get("test_sha256_after") != "286f02a8cd023faabcd9c61e198679f1b0e5dc566e15586beddeb6e95e44b9f0"
        or acquisition_progress_portability.get("validation", {}).get("focused_acquisition_progress_test_count") != 10
        or acquisition_progress_portability.get("validation", {}).get("focused_acquisition_progress_tests") != "pass"
        or acquisition_progress_portability.get("assertions", {}).get("external_custody_mutated") is not False
        or acquisition_progress_portability.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or acquisition_progress_portability.get("assertions", {}).get("network_requests_performed_by_correction") is not False
        or acquisition_progress_portability.get("assertions", {}).get("product_bytes_requested_by_correction") != 0
        or acquisition_progress_portability.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("M2 acquisition-progress Windows-path portability correction differs")
    if acquisition_checkpoint_readiness.get("status") != "pass_preacquisition_checkpoint_derivation":
        fail("M2 acquisition-checkpoint readiness receipt status differs")
    checkpoint_bindings = acquisition_checkpoint_readiness.get("bindings", {})
    expected_historical_checkpoint_bindings = {
        "initial_snapshot_ref": "records/acquisition/active-intake-initial-snapshot.json",
        "initial_snapshot_sha256": "a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c",
        "progress_validator_ref": "scripts/validate_m2_acquisition_progress.py",
        "progress_validator_sha256": "fc90a85e111135133a64249151086d7032c924148bcf5cc29cbee473703a9051",
        "derivation_ref": "scripts/derive_m2_acquisition_checkpoint.py",
        "derivation_sha256": "4d78913210978495b320dd70ace7d9e0ef3b7e9f7bf4f2804fbe444691b728a8",
        "test_ref": "tests/test_m2_checkpoint_reconciliation.py",
        "test_sha256": "41288357950546dc5d047dc24b8a699cb8ad4afe31c6adfa6ac28e55b0065798",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "907bc0c3591e1f3c1e1e32c3651d3919c3f8ecfc83ac7f72f4ead92ca4d9498d",
        "runbook_ref": "docs/M2_EXECUTION_RUNBOOK.md",
        "runbook_sha256": "8b1aa06c0e4da9d56a9634c09822a8116aa23ed4db5c6c6aad66c9fb619201f3",
    }
    if checkpoint_bindings != expected_historical_checkpoint_bindings:
        fail("M2 acquisition-checkpoint readiness no longer preserves its published bindings")
    if acquisition_checkpoint_readiness.get("validation") != {
        "focused_test_count": 9,
        "focused_test_status": "pass",
        "repository_checkpoint_derivation": "pass",
        "external_state_reconciliation": "pass",
        "current_checkpoint": "M2-AUTHENTICATION-REFERENCE",
        "candidate_output_policy": "scratch_only_exclusive_no_replace",
    }:
        fail("M2 acquisition-checkpoint readiness validation differs")
    if acquisition_checkpoint_portability.get("status") != "pass_portable_repository_test_external_verification_separated":
        fail("M2 acquisition-checkpoint portability correction status differs")
    portability_bindings = acquisition_checkpoint_portability.get("bindings", {})
    expected_historical_portability_bindings = {
        "published_readiness_ref": "records/acquisition/acquisition-checkpoint-readiness.json",
        "published_readiness_sha256": "1a4439702be6ad448ec9eafc095d4bd25b692100b73dd19429fb20a1fde7eca9",
        "derivation_ref": "scripts/derive_m2_acquisition_checkpoint.py",
        "derivation_sha256": "4d78913210978495b320dd70ace7d9e0ef3b7e9f7bf4f2804fbe444691b728a8",
        "test_ref": "tests/test_m2_checkpoint_reconciliation.py",
        "test_sha256": "53e7e5d98b6e11a1ad3c4f3b9b6523e766bf74765d98f7a35b8e7ffeed2662a3",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "0ea6c6cc5bcc32db19105dfd2cc2ca27bdf96e38f361f3c0a131b64ef64f6801",
    }
    if portability_bindings != expected_historical_portability_bindings:
        fail("M2 acquisition-checkpoint portability correction no longer preserves its published bindings")
    if acquisition_checkpoint_portability.get("validation") != {
        "focused_test_count": 9,
        "focused_test_status": "pass",
        "full_repository_test_count": 141,
        "full_repository_test_status": "pass",
        "repository_required_file_count": 146,
        "repository_validation_status": "pass",
        "portable_repository_derivation": "pass",
        "local_external_state_reconciliation": "pass",
        "failed_ci_run_id": 33800916326,
        "failed_ci_run_status": "failure",
    }:
        fail("M2 acquisition-checkpoint portability correction validation differs")
    if pair_plan.get("authority", {}).get("mode") != "not_granted" or pair_plan.get("authority", {}).get("authorized_actions") != [] or len(pair_plan.get("pairs", [])) != 3:
        fail("candidate pair plan must remain non-authorizing with three independent routes")
    if intake_dry_run.get("status") != "pass_static_only_no_authority":
        fail("M2 static dry run must remain explicitly non-authorizing")
    dry_inputs = intake_dry_run.get("inputs", {})
    expected_dry_inputs = {
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "m2_proposal_sha256": sha256("contracts/milestone-002-proposal.json"),
        "activation_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
        "intake_contract_sha256": sha256("contracts/m2-intake-candidate.json"),
    }
    if dry_inputs != expected_dry_inputs:
        fail("M2 static dry run does not bind its exact inputs")
    dry_authority = intake_dry_run.get("authority", {})
    if dry_authority.get("acquisition_authorized") is not False or dry_authority.get("network_or_authentication_performed") is not False:
        fail("M2 static dry run must not claim acquisition, network, or authentication activity")
    if intake_dry_run.get("path_model", {}).get("directories_created") is not False:
        fail("M2 static dry run must not claim external directory creation")

    if offline_verification.get("status") != "candidate_static_control_not_authorized":
        fail("M2 offline verification contract must remain non-authorizing")
    offline_inputs = offline_verification.get("inputs", {})
    expected_offline_inputs = {
        "acquisition_plan_ref": "records/acquisition-plan.json",
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "intake_contract_ref": "contracts/m2-intake-candidate.json",
        "intake_contract_sha256": sha256("contracts/m2-intake-candidate.json"),
        "manifest_approval_ref": "records/source-gates/source-manifest-approval.json",
        "manifest_approval_sha256": sha256("records/source-gates/source-manifest-approval.json"),
        "m2_review_bundle_ref": "reviews/m2-activation/review-bundle.json",
        "m2_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
    }
    if offline_inputs != expected_offline_inputs:
        fail("M2 offline verification contract does not bind its exact approved inputs")
    offline_authority = offline_verification.get("authority", {})
    if offline_authority.get("m2_activation_status") != "not_granted":
        fail("M2 offline verification contract must preserve the pending activation gate")
    if any(value for key, value in offline_authority.items() if key != "m2_activation_status"):
        fail("M2 offline verification contract must not create operational authority")
    boundary = offline_verification.get("execution_boundary", {})
    if boundary.get("network_requests") != "prohibited" or boundary.get("archive_extraction") != "prohibited":
        fail("M2 offline verification must prohibit network requests and archive extraction")
    if boundary.get("custody_root_must_already_exist") is not True or boundary.get("overwrite_existing_receipt") is not False:
        fail("M2 offline verification must refuse root creation and receipt replacement")

    if active_offline_verification.get("status") != "active_authorized_offline_verification":
        fail("active M2 offline verification contract has an invalid status")
    active_verification_inputs = active_offline_verification.get("inputs", {})
    expected_active_verification_hashes = {
        "candidate_contract_sha256": sha256("contracts/m2-offline-verification-candidate.json"),
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "active_milestone_sha256_at_activation": "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb",
        "activation_approval_sha256": sha256("records/source-gates/m2-activation-approval.json"),
        "active_intake_sha256_at_activation": INITIAL_ACTIVE_INTAKE_SHA256,
        "source_gate_sha256": sha256("records/source-gates/m2-live-source-gate.json"),
        "custody_initialization_sha256": sha256("records/acquisition/custody-initialization.json"),
    }
    if any(active_verification_inputs.get(key) != value for key, value in expected_active_verification_hashes.items()):
        fail("active M2 offline verification contract has a stale evidence binding")
    active_verification_authority = active_offline_verification.get("authority", {})
    if active_verification_authority.get("mode") != "inherited" or active_verification_authority.get("authority_ref") != "records/source-gates/m2-activation-approval.json":
        fail("active M2 offline verification does not inherit exact M2 authority")
    if active_verification_authority.get("offline_verification_authorized") is not True or active_verification_authority.get("this_contract_creates_authority") is not False:
        fail("active M2 offline verification authority semantics are invalid")
    if active_offline_verification.get("assets") != offline_verification.get("assets"):
        fail("active M2 offline verification changed the exact candidate product controls")
    active_boundary = active_offline_verification.get("execution_boundary", {})
    if active_boundary.get("network_requests") != "prohibited" or active_boundary.get("archive_extraction") != "prohibited" or active_boundary.get("source_archive_mutation") != "prohibited":
        fail("active M2 offline verification must remain offline, non-extracting, and read-only")
    if active_offline_verification.get("activation_boundary", {}).get("product_bytes_read") != 0:
        fail("activating M2 offline verification must not claim product-byte access")
    offline_assets = offline_verification.get("assets", [])
    if len(offline_assets) != 8:
        fail("M2 offline verification contract must contain exactly eight assets")
    offline_by_source = {item.get("source_id"): item for item in offline_assets}
    plan_by_source = {item["source_id"]: item for item in acquisition_plan["records"]}
    intake_by_source = {item["extensions"]["source_id"]: item for item in intake_contract["assets"]}
    if set(offline_by_source) != set(plan_by_source):
        fail("M2 offline verification source set differs from the approved plan")
    required_radar_patterns = {
        "measurement/*-vv-*.tiff",
        "measurement/*-vh-*.tiff",
        "annotation/calibration/calibration-*-vv-*.xml",
        "annotation/calibration/noise-*-vh-*.xml",
    }
    required_optical_patterns = {
        "GRANULE/*/IMG_DATA/R10m/*_B02_10m.jp2",
        "GRANULE/*/IMG_DATA/R10m/*_B08_10m.jp2",
        "GRANULE/*/IMG_DATA/R20m/*_B11_20m.jp2",
        "GRANULE/*/IMG_DATA/R20m/*_B12_20m.jp2",
        "GRANULE/*/IMG_DATA/R20m/*_SCL_20m.jp2",
    }
    for source_id, offline_asset in offline_by_source.items():
        plan_asset = plan_by_source[source_id]
        intake_asset = intake_by_source[source_id]
        if offline_asset.get("exact_product_id") != plan_asset["exact_product_id"]:
            fail(f"M2 offline verification product identity differs for {source_id}")
        if offline_asset.get("archive_relative_path") != intake_asset["destination_relative_path"]:
            fail(f"M2 offline verification custody path differs for {source_id}")
        checksums = {item["Algorithm"].casefold(): item["Value"].casefold() for item in plan_asset["provider_checksums"]}
        if offline_asset.get("provider_md5") != checksums.get("md5"):
            fail(f"M2 offline verification provider MD5 differs for {source_id}")
        if offline_asset.get("provider_blake3_metadata") != checksums.get("blake3"):
            fail(f"M2 offline verification provider BLAKE3 metadata differs for {source_id}")
        patterns = {item.get("pattern") for item in offline_asset.get("required_members", [])}
        required = required_radar_patterns if plan_asset["sensor_route"] == "radar" else required_optical_patterns
        if not required.issubset(patterns):
            fail(f"M2 offline verification structural profile is incomplete for {source_id}")
    if readiness_input.get("candidate_manifest_sha256") != sha256("records/source-manifest.json"):
        fail("M2 readiness audit does not bind the approved source manifest")
    required_gate_ids = set(readiness_input.get("required_gate_ids", []))
    if len(required_gate_ids) != 9:
        fail("M2 readiness audit must preserve nine required non-count gates")
    if {gate.get("gate_id") for gate in readiness_input.get("gates", [])} != required_gate_ids:
        fail("M2 readiness audit gate inventory differs")
    if any(gate.get("status") != "defer" for gate in readiness_input.get("gates", [])):
        fail("M2 pre-acquisition readiness gates must remain deferred")
    if readiness_input.get("next_step_authority") != {
        "mode": "not_granted",
        "authority_ref": "reviews/m2-activation/review-bundle.json",
        "authorized_actions": [],
    }:
        fail("M2 readiness audit must not create next-step authority")
    if readiness_decision.get("audit_input_sha256") != sha256("records/readiness/m2-readiness-audit-input.json"):
        fail("M2 readiness decision does not bind its exact audit input")
    if readiness_decision.get("decision") != "defer":
        fail("M2 readiness decision must remain defer before acquisition and pixel evidence")
    if set(readiness_decision.get("deferred_required_gate_ids", [])) != required_gate_ids:
        fail("M2 readiness decision does not retain every unresolved required gate")
    if readiness_decision.get("blocking_required_gate_ids") != [] or readiness_decision.get("pass_evidence") != []:
        fail("M2 readiness decision must not invent blocking or passing gate evidence")
    if readiness_decision.get("authorized_next_actions") != [] or readiness_decision.get("training_authorized_by_this_audit") is not False:
        fail("M2 readiness decision must not authorize downstream work")
    if reproducibility["status"] != "pass_with_retained_failures":
        fail("M1 reproducibility receipt is not in a passing state")
    for check in reproducibility["checks"]:
        if check["status"] != "pass" or check["sha256"] != sha256(check["artifact"]):
            fail(f"reproducibility receipt does not bind {check['artifact']}")

    if evidence_workspace.get("status") != "pass_with_retained_failures":
        fail("ArcGIS evidence workspace receipt is not in a passing state")
    if evidence_workspace.get("runtime") != {"product": "ArcGISPro", "version": "3.7.1", "license_level": "Advanced"}:
        fail("ArcGIS evidence workspace runtime differs from the validated environment")
    evidence_inputs = evidence_workspace.get("inputs", {})
    for path_key, hash_key in (
        ("schema", "schema_sha256"),
        ("approved_aoi", "approved_aoi_sha256"),
        ("source_manifest", "source_manifest_sha256"),
        ("manifest_approval", "manifest_approval_sha256"),
        ("builder", "builder_sha256"),
    ):
        relative = evidence_inputs.get(path_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"ArcGIS evidence workspace receipt is missing {path_key}")
        if evidence_inputs.get(hash_key) != sha256(relative):
            fail(f"ArcGIS evidence workspace receipt does not bind {path_key}")
    preview = evidence_workspace.get("public_preview", {})
    preview_relative = preview.get("path")
    if not isinstance(preview_relative, str) or not (ROOT / preview_relative).is_file():
        fail("ArcGIS evidence workspace preview is missing")
    if preview.get("sha256") != sha256(preview_relative) or preview.get("visual_inspection") != "pass":
        fail("ArcGIS evidence workspace preview is unbound or not visually approved")
    if len(evidence_schema.get("datasets", [])) != 9 or len(evidence_schema.get("domains", {})) != 14:
        fail("ArcGIS evidence schema must contain nine datasets and fourteen domains")
    if len(evidence_schema.get("relationships", [])) != 8:
        fail("ArcGIS evidence schema must contain eight relationship classes")
    dataset_names = {item["name"] for item in evidence_schema["datasets"]}
    if not {"ObservedChange", "Interpretations", "AttributionAssessments"}.issubset(dataset_names):
        fail("ArcGIS evidence schema must separate observation, interpretation, and attribution")
    relationship_names = {item["name"] for item in evidence_schema["relationships"]}
    if not {"ObservedChange_Interpretations", "Interpretations_Attribution"}.issubset(relationship_names):
        fail("ArcGIS evidence schema must link observation to interpretation and attribution")
    expected_workspace_counts = evidence_schema.get("initial_counts", {})
    actual_workspace_counts = {
        name: details.get("row_count")
        for name, details in evidence_workspace.get("workspace", {}).get("datasets", {}).items()
    }
    if expected_workspace_counts != actual_workspace_counts:
        fail("ArcGIS evidence workspace row counts differ from the declared empty scientific state")
    feature_wkids = {
        name: details.get("spatial_reference_wkid")
        for name, details in evidence_workspace["workspace"]["datasets"].items()
        if name in {"StudyAreas", "ObservedChange", "AnalysisExclusions", "StableControls"}
    }
    if set(feature_wkids.values()) != {32645}:
        fail("ArcGIS evidence feature classes must use EPSG:32645")
    record_states = set(evidence_schema["domains"]["DOM_RECORD_STATUS"]["coded_values"])
    if not {"rejected", "deferred", "inconclusive", "invalid", "superseded"}.issubset(record_states):
        fail("ArcGIS evidence schema does not preserve required adverse record states")
    if len(evidence_workspace.get("retained_failures", [])) != 6:
        fail("ArcGIS evidence workspace must retain all six failed attempts")
    if {item.get("status") for item in evidence_workspace["retained_failures"]} != {"fail", "fail_visual"}:
        fail("ArcGIS evidence workspace retained failure types differ")
    if evidence_workspace.get("checks", {}).get("visual_inspection") != "pass":
        fail("ArcGIS evidence workspace visual inspection did not pass")
    if not any("No satellite pixels" in item for item in evidence_workspace.get("limitations", [])):
        fail("ArcGIS evidence workspace must preserve its no-pixels claim boundary")

    if pixel_contract.get("contract_id") != "NEPAL-PIXEL-QA-001" or pixel_contract.get("status") != "predeclared_before_product_pixels":
        fail("pixel-readiness contract identity or predeclaration status differs")
    if pixel_contract.get("analysis_crs", {}).get("wkid") != 32645:
        fail("pixel-readiness contract must use EPSG:32645")
    if pixel_contract.get("decision_semantics", {}).get("precedence") != ["invalid", "block", "defer", "pass_qa_only"]:
        fail("pixel-readiness decision precedence differs")
    if pixel_contract.get("decision_semantics", {}).get("pass_qa_only_creates_scientific_admission") is not False:
        fail("pixel-readiness pass must not create scientific admission")
    if pixel_contract.get("aoi_coverage", {}) != {
        "full_coverage_pass_minimum": 0.99,
        "usable_fraction_pass_minimum": 0.8,
        "partial_evidence_defer_minimum": 0.2,
        "area_consistency_tolerance_fraction": 0.02,
        "fraction_precision": 6,
        "rules": pixel_contract.get("aoi_coverage", {}).get("rules"),
    }:
        fail("pixel-readiness AOI thresholds differ")
    if set(pixel_contract.get("optical_scl", {}).get("valid_surface_classes", {})) != {"4", "5", "6"}:
        fail("pixel-readiness optical valid classes differ")
    if pixel_receipt.get("status") != "pass_synthetic_only_with_expected_block_and_defer":
        fail("synthetic ArcGIS pixel-QA receipt status differs")
    if pixel_receipt.get("runtime") != {
        "product": "ArcGISPro",
        "version": "3.7.1",
        "license_level": "Advanced",
        "spatial_analyst": "available_and_used",
    }:
        fail("synthetic ArcGIS pixel-QA runtime differs")
    pixel_inputs = pixel_receipt.get("inputs", {})
    for path_key, hash_key in (
        ("contract", "contract_sha256"),
        ("approved_aoi", "approved_aoi_sha256"),
        ("core", "core_sha256"),
        ("arcgis_adapter", "arcgis_adapter_sha256"),
    ):
        relative = pixel_inputs.get(path_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"synthetic ArcGIS pixel-QA receipt is missing {path_key}")
        if pixel_inputs.get(hash_key) != sha256(relative):
            fail(f"synthetic ArcGIS pixel-QA receipt does not bind {path_key}")
    fixture = pixel_receipt.get("synthetic_fixture", {})
    if fixture.get("wkid") != 32645 or fixture.get("cell_size_m") != 20.0:
        fail("synthetic ArcGIS pixel-QA fixture grid differs")
    if not isinstance(fixture.get("rows"), int) or fixture["rows"] <= 0 or not isinstance(fixture.get("columns"), int) or fixture["columns"] <= 0:
        fail("synthetic ArcGIS pixel-QA fixture dimensions are invalid")
    pixel_checks = pixel_receipt.get("checks", {})
    aoi_pixel_results = pixel_checks.get("aoi_scl_coverage", [])
    if {item.get("aoi_id") for item in aoi_pixel_results} != {"AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
        fail("synthetic ArcGIS pixel-QA AOI inventory differs")
    if any(
        item.get("status") != "pass_qa_only"
        or item.get("coverage_fraction", 0) < 0.99
        or item.get("usable_fraction_of_aoi", 0) < 0.8
        or item.get("unknown_scl_classes") != []
        or item.get("scientific_admission_authorized") is not False
        for item in aoi_pixel_results
    ):
        fail("synthetic ArcGIS pixel-QA AOI result differs from the predeclared pass-only boundary")
    if pixel_checks.get("aligned_grid_pair", {}).get("status") != "pass_qa_only":
        fail("synthetic aligned raster pair did not pass grid QA")
    shifted = pixel_checks.get("deliberately_misaligned_grid_pair", {})
    if shifted.get("status") != "block" or not any("origins" in item for item in shifted.get("errors", [])):
        fail("synthetic shifted raster did not preserve the expected grid block")
    if pixel_checks.get("registration_not_measured", {}).get("status") != "defer":
        fail("synthetic unmeasured registration did not remain deferred")
    expected_pixel_assertions = {
        "all_three_aoi_coverage_results_pass_qa_only": True,
        "aligned_grid_pair_passes_qa_only": True,
        "subpixel_shift_is_blocked": True,
        "unmeasured_registration_is_deferred": True,
        "real_product_pixels_examined": False,
        "scientific_admission_authorized": False,
        "m2_activated": False,
    }
    if pixel_receipt.get("assertions") != expected_pixel_assertions:
        fail("synthetic ArcGIS pixel-QA assertions differ")
    if pixel_receipt.get("preserved_review_bindings") != {
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "m2_activation_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
    }:
        fail("synthetic ArcGIS pixel-QA receipt does not preserve M2 review bindings")

    ledger_records = []
    for number, line in enumerate(
        (ROOT / "records/evidence-ledger.jsonl").read_text(encoding="utf-8").splitlines(), 1
    ):
        if line.strip():
            try:
                ledger_records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                fail(f"invalid evidence ledger JSON on line {number}: {exc}")
    ledger_by_id = {record.get("record_id"): record for record in ledger_records}
    offline_evidence = ledger_by_id.get("EVID-0020")
    if not isinstance(offline_evidence, dict):
        fail("evidence ledger is missing EVID-0020 offline verification evidence")
    for ref_key, hash_key in (
        ("verification_contract_ref", "verification_contract_sha256"),
        ("readiness_input_ref", "readiness_input_sha256"),
        ("readiness_decision_ref", "readiness_decision_sha256"),
        ("generator_ref", "generator_sha256"),
        ("test_ref", "test_sha256"),
    ):
        relative = offline_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0020 is missing {ref_key}")
        if offline_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0020 does not bind {ref_key}")
    if offline_evidence.get("independent_readiness_audit", {}).get("decision") != "defer":
        fail("EVID-0020 must preserve the independent DEFER readiness decision")
    if offline_evidence.get("preserved_review_bindings") != {
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "m2_activation_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
    }:
        fail("EVID-0020 does not preserve the exact M2 review bindings")
    pixel_evidence = ledger_by_id.get("EVID-0021")
    if not isinstance(pixel_evidence, dict):
        fail("evidence ledger is missing EVID-0021 pixel-readiness evidence")
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("portable_test_ref", "portable_test_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("receipt_ref", "receipt_sha256"),
    ):
        relative = pixel_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0021 is missing {ref_key}")
        if pixel_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0021 does not bind {ref_key}")
    if pixel_evidence.get("portable_test_count") != 11 or pixel_evidence.get("arcgis_native_result") != {
        "aoi_pass_qa_only_count": 3,
        "aligned_grid_status": "pass_qa_only",
        "misaligned_grid_status": "block",
        "registration_not_measured_status": "defer",
    }:
        fail("EVID-0021 validation summary differs")
    if pixel_evidence.get("preserved_review_bindings") != {
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "m2_activation_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
    }:
        fail("EVID-0021 does not preserve the exact M2 review bindings")
    dem_evidence = ledger_by_id.get("EVID-0022")
    if not isinstance(dem_evidence, dict):
        fail("evidence ledger is missing EVID-0022 DEM dependency review evidence")
    for ref_key, hash_key in (
        ("arcgis_capability_ref", "arcgis_capability_sha256"),
        ("metadata_receipt_ref", "metadata_receipt_sha256"),
        ("candidate_manifest_ref", "candidate_manifest_sha256"),
        ("source_gate_ref", "source_gate_sha256"),
        ("amendment_proposal_ref", "amendment_proposal_sha256"),
        ("review_bundle_ref", "review_bundle_manifest_sha256"),
        ("review_surface_ref", "review_surface_sha256"),
        ("test_ref", "test_sha256"),
    ):
        relative = dem_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0022 is missing {ref_key}")
        if dem_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0022 does not bind {ref_key}")
    if dem_evidence.get("status") != "ready_for_human_review_source_gate_blocked":
        fail("EVID-0022 must preserve the blocked DEM source gate")
    if dem_evidence.get("assertions") != {
        "dem_payload_bytes_requested": False,
        "account_or_authentication_used": False,
        "dem_pixels_examined": False,
        "sentinel_processing_executed": False,
        "authority_created": False,
    }:
        fail("EVID-0022 claim boundary differs")
    dem_radar_evidence = ledger_by_id.get("EVID-0023")
    if not isinstance(dem_radar_evidence, dict):
        fail("evidence ledger is missing EVID-0023 DEM and radar control evidence")
    for ref_key, hash_key in (
        ("receipt_ref", "receipt_sha256"),
        ("dem_intake_ref", "dem_intake_sha256"),
        ("dem_verification_ref", "dem_verification_sha256"),
        ("radar_contract_ref", "radar_contract_sha256"),
        ("dem_protocol_ref", "dem_protocol_sha256"),
        ("radar_protocol_ref", "radar_protocol_sha256"),
        ("dem_test_ref", "dem_test_sha256"),
        ("radar_test_ref", "radar_test_sha256"),
    ):
        relative = dem_radar_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0023 is missing {ref_key}")
        if dem_radar_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0023 does not bind {ref_key}")
    if dem_radar_evidence.get("status") != "pass_static_controls_only_dependencies_deferred":
        fail("EVID-0023 must preserve its static-only deferred status")
    if dem_radar_evidence.get("validation", {}).get("full_unit_test_count") != 82:
        fail("EVID-0023 must preserve 82 passing tests")
    if dem_radar_evidence.get("assertions") != dem_radar_readiness.get("assertions"):
        fail("EVID-0023 and its readiness receipt have different claim boundaries")
    optical_evidence = ledger_by_id.get("EVID-0024")
    if not isinstance(optical_evidence, dict):
        fail("evidence ledger is missing EVID-0024 optical processing evidence")
    for ref_key, hash_key in (
        ("readiness_receipt_ref", "readiness_receipt_sha256"),
        ("arcgis_receipt_ref", "arcgis_receipt_sha256"),
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("builder_ref", "builder_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
    ):
        relative = optical_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0024 is missing {ref_key}")
        if optical_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0024 does not bind {ref_key}")
    if optical_evidence.get("status") != "pass_synthetic_only_real_route_deferred":
        fail("EVID-0024 must preserve its synthetic-only deferred status")
    if optical_evidence.get("route_disposition", {}).get("status") != "defer":
        fail("EVID-0024 real optical route must remain deferred")
    if optical_evidence.get("assertions") != optical_readiness.get("assertions"):
        fail("EVID-0024 and optical readiness receipt have different claim boundaries")
    materialization_evidence = ledger_by_id.get("EVID-0025")
    if not isinstance(materialization_evidence, dict):
        fail("evidence ledger is missing EVID-0025 materialization preparation evidence")
    for ref_key, hash_key in (
        ("readiness_receipt_ref", "readiness_receipt_sha256"),
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
    ):
        relative = materialization_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0025 is missing {ref_key}")
        expected_hash = (
            "be2287d52730aeaeed2bb7b670e9596f229e0cf1aa3afd80ba72c1a6e37a267f"
            if ref_key == "test_ref"
            else sha256(relative)
        )
        if materialization_evidence.get(hash_key) != expected_hash:
            fail(f"EVID-0025 does not bind {ref_key}")
    if materialization_evidence.get("status") != "pass_synthetic_only_real_materialization_deferred":
        fail("EVID-0025 must preserve its synthetic-only deferred status")
    if materialization_evidence.get("current_disposition", {}).get("status") != "defer":
        fail("EVID-0025 real materialization route must remain deferred")
    evidence_assertions = materialization_evidence.get("assertions", {})
    readiness_assertions = materialization_readiness.get("assertions", {})
    for key in (
        "synthetic_materialization_passed",
        "external_materialization_directory_created",
        "real_archive_read",
        "real_safe_materialized",
        "raster_readability_established",
        "pixel_usability_established",
        "baseline_established",
        "change_established",
        "scientific_admission_authorized",
    ):
        if evidence_assertions.get(key) != readiness_assertions.get(key):
            fail(f"EVID-0025 and materialization readiness differ for {key}")
    if evidence_assertions.get("authority_created") is not False:
        fail("EVID-0025 must not create authority")
    historical_input_evidence = ledger_by_id.get("EVID-0026")
    if not isinstance(historical_input_evidence, dict):
        fail("evidence ledger is missing EVID-0026 optical input-readiness evidence")
    historical_input_bindings = (
        ("readiness_receipt_ref", "records/surface-receipts/optical-input-readiness-control.json", "readiness_receipt_sha256", "16b16e2dfebd829940340ff1ebfb9e19a038b162b9435efe5c064453cc61b55f"),
        ("arcgis_receipt_ref", "records/surface-receipts/optical-input-readiness-synthetic-arcgis.json", "arcgis_receipt_sha256", "3910aa085534a8721c0f70d50603950fe709cd0b6f084a5b7eb0b8c16b97836c"),
        ("contract_ref", "config/qa/optical-input-readiness-contract.json", "contract_sha256", "7cbcedef168a7e052ea44a8cd9b838281ace5c6b3d196a3ecd8d642ac3605427"),
        ("core_ref", "scripts/optical_input_readiness_core.py", "core_sha256", "0055e653404a0cfc98748491dc05349f8892986cb17efdd32cf7fb1be452551c"),
        ("generator_ref", "scripts/prepare_optical_input_readiness_contract.py", "generator_sha256", "c9974e80364d867bed5735be8cbda58931d92e33fb688e29c64cae58f741deb2"),
        ("runner_ref", "scripts/inspect_optical_inputs_arcgis.py", "runner_sha256", "5bc717da9095db3390ead46f5c066ffbde9f25e896dd2581db624f4b4f632db0"),
        ("arcgis_adapter_ref", "scripts/validate_optical_input_readiness_arcgis.py", "arcgis_adapter_sha256", "7a10c2ae11fcdff14be4229dd4a0bff78b3dcc99352aced72f3a06e305b6831f"),
        ("test_ref", "tests/test_optical_input_readiness.py", "test_sha256", "9b6182cc536df0feda762fbe83b0c8e87e056157d2e37b10d6823be556e3fa06"),
        ("protocol_ref", "docs/OPTICAL_INPUT_READINESS_PROTOCOL.md", "protocol_sha256", "35f77b2f2693ff2b1cf3211ca2546cd7a1479b99f7646601c88b1b4cbb235679"),
    )
    for ref_key, expected_ref, hash_key, expected_hash in historical_input_bindings:
        if historical_input_evidence.get(ref_key) != expected_ref or historical_input_evidence.get(hash_key) != expected_hash:
            fail(f"EVID-0026 no longer preserves its published {ref_key}")
    if historical_input_evidence.get("status") != "pass_synthetic_arcgis_real_input_deferred" or historical_input_evidence.get("current_disposition", {}).get("status") != "defer":
        fail("EVID-0026 must preserve its synthetic-only deferred state")
    corrected_input_evidence = ledger_by_id.get("EVID-0027")
    if not isinstance(corrected_input_evidence, dict):
        fail("evidence ledger is missing EVID-0027 corrected optical input-readiness evidence")
    for ref_key, hash_key in (
        ("readiness_receipt_ref", "readiness_receipt_sha256"),
        ("arcgis_receipt_ref", "arcgis_receipt_sha256"),
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
    ):
        relative = corrected_input_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or corrected_input_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0027 does not bind {ref_key}")
    if corrected_input_evidence.get("status") != "pass_corrected_synthetic_arcgis_real_input_deferred" or corrected_input_evidence.get("current_disposition", {}).get("status") != "defer":
        fail("EVID-0027 must preserve its corrected synthetic-only deferred state")
    if corrected_input_evidence.get("supersedes") != optical_input_readiness.get("supersedes"):
        fail("EVID-0027 and the current control receipt identify different superseded evidence")
    if corrected_input_evidence.get("source_references") != expected_input_source_references:
        fail("EVID-0027 does not preserve the official correction sources")
    evidence_input_assertions = corrected_input_evidence.get("assertions", {})
    readiness_input_assertions = optical_input_readiness.get("assertions", {})
    if evidence_input_assertions != readiness_input_assertions:
        fail("EVID-0027 and optical input-readiness receipt have different claim boundaries")
    acquisition_progress_evidence = ledger_by_id.get("EVID-0028")
    if not isinstance(acquisition_progress_evidence, dict):
        fail("evidence ledger is missing EVID-0028 acquisition-progress readiness evidence")
    expected_evid_0028_bindings = {
        "readiness_receipt_ref": "records/acquisition/acquisition-progress-readiness.json",
        "readiness_receipt_sha256": "a9ea7828c7cf48c28bbe7a3370334134eeadb7d0ab891c74d0fbb49deafe0708",
        "initial_snapshot_ref": "records/acquisition/active-intake-initial-snapshot.json",
        "initial_snapshot_sha256": "a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c",
        "validator_ref": "scripts/validate_m2_acquisition_progress.py",
        "validator_sha256": "fc90a85e111135133a64249151086d7032c924148bcf5cc29cbee473703a9051",
        "test_ref": "tests/test_m2_acquisition_progress.py",
        "test_sha256": "5d1c59520d803daa05ba1bfef1ddcfbdbe894566a9cfb0c50f3c7dba00e2f191",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "0811375064b8d2681690012d82234270f00022e23e94c82649c43f28ec5b7395",
        "runbook_ref": "docs/M2_EXECUTION_RUNBOOK.md",
        "runbook_sha256": "abd658d18a80f86bb3d8c4446eac9dfde7e268ffee44ee0841421838292d66ed",
    }
    for key, expected in expected_evid_0028_bindings.items():
        if acquisition_progress_evidence.get(key) != expected:
            fail(f"EVID-0028 no longer preserves published {key}")
    if acquisition_progress_evidence.get("status") != "pass_preacquisition_dynamic_progress_validation":
        fail("EVID-0028 status differs")
    if acquisition_progress_evidence.get("assertions") != acquisition_progress_readiness.get("assertions"):
        fail("EVID-0028 and acquisition-progress readiness have different claim boundaries")
    acquisition_checkpoint_evidence = ledger_by_id.get("EVID-0029")
    if not isinstance(acquisition_checkpoint_evidence, dict):
        fail("evidence ledger is missing EVID-0029 acquisition-checkpoint readiness evidence")
    expected_evid_0029_bindings = {
        "readiness_receipt_ref": "records/acquisition/acquisition-checkpoint-readiness.json",
        "readiness_receipt_sha256": "1a4439702be6ad448ec9eafc095d4bd25b692100b73dd19429fb20a1fde7eca9",
        "derivation_ref": "scripts/derive_m2_acquisition_checkpoint.py",
        "derivation_sha256": "4d78913210978495b320dd70ace7d9e0ef3b7e9f7bf4f2804fbe444691b728a8",
        "test_ref": "tests/test_m2_checkpoint_reconciliation.py",
        "test_sha256": "41288357950546dc5d047dc24b8a699cb8ad4afe31c6adfa6ac28e55b0065798",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "907bc0c3591e1f3c1e1e32c3651d3919c3f8ecfc83ac7f72f4ead92ca4d9498d",
        "runbook_ref": "docs/M2_EXECUTION_RUNBOOK.md",
        "runbook_sha256": "8b1aa06c0e4da9d56a9634c09822a8116aa23ed4db5c6c6aad66c9fb619201f3",
    }
    for key, expected in expected_evid_0029_bindings.items():
        if acquisition_checkpoint_evidence.get(key) != expected:
            fail(f"EVID-0029 no longer preserves published {key}")
    if acquisition_checkpoint_evidence.get("status") != "pass_preacquisition_checkpoint_derivation":
        fail("EVID-0029 status differs")
    if acquisition_checkpoint_evidence.get("assertions") != acquisition_checkpoint_readiness.get("assertions"):
        fail("EVID-0029 and acquisition-checkpoint readiness have different claim boundaries")
    acquisition_checkpoint_portability_evidence = ledger_by_id.get("EVID-0030")
    if not isinstance(acquisition_checkpoint_portability_evidence, dict):
        fail("evidence ledger is missing EVID-0030 acquisition-checkpoint portability correction")
    expected_evid_0030_bindings = {
        "correction_receipt_ref": "records/acquisition/acquisition-checkpoint-portability-correction.json",
        "correction_receipt_sha256": "f69c8b9944a048bb8645f8852281319ac8fa87e3aecce3fe39cc332f63caa352",
        "derivation_ref": "scripts/derive_m2_acquisition_checkpoint.py",
        "derivation_sha256": "4d78913210978495b320dd70ace7d9e0ef3b7e9f7bf4f2804fbe444691b728a8",
        "test_ref": "tests/test_m2_checkpoint_reconciliation.py",
        "test_sha256": "53e7e5d98b6e11a1ad3c4f3b9b6523e766bf74765d98f7a35b8e7ffeed2662a3",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "0ea6c6cc5bcc32db19105dfd2cc2ca27bdf96e38f361f3c0a131b64ef64f6801",
    }
    for key, expected in expected_evid_0030_bindings.items():
        if acquisition_checkpoint_portability_evidence.get(key) != expected:
            fail(f"EVID-0030 no longer preserves published {key}")
    if acquisition_checkpoint_portability_evidence.get("status") != "pass_portable_repository_test_external_verification_separated":
        fail("EVID-0030 status differs")
    if acquisition_checkpoint_portability_evidence.get("assertions") != acquisition_checkpoint_portability.get("assertions"):
        fail("EVID-0030 and acquisition-checkpoint portability correction have different claim boundaries")
    dem_activation_evidence = ledger_by_id.get("EVID-0031")
    if not isinstance(dem_activation_evidence, dict):
        fail("evidence ledger is missing EVID-0031 DEM amendment activation evidence")
    expected_evid_0031_bindings = {
        "activation_receipt_ref": "records/acquisition/dem-amendment-activation.json",
        "activation_receipt_sha256": "76e4233efd4dfd2d75a6873504646558eb4a16cd1f069060f91f0194c40c63d9",
        "approval_ref": "records/source-gates/m2-dem-amendment-approval.json",
        "approval_sha256": "6d1fc7e05854bc149ace177d89e84a7651cc049efd530cab650a9464222769d0",
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256": "0fa00a4be01d3caddac28088d2d3d714040d1258b33497ebee50cbb0b8b3b5b6",
        "active_verification_ref": "contracts/m2-dem-offline-verification.json",
        "active_verification_sha256": "755bdb1fd1916d68289f5266912f8bb7f25462b512ce7cfc27a49feb44bcef42",
        "reconciliation_ref": "records/source-gates/m2-dem-amendment-review-reconciliation.json",
        "reconciliation_sha256": "9d72c9786440da0c9149340cd69361b12e55f0d7dff88972bfd02ee0da5460e1",
        "activation_script_ref": "scripts/activate_m2_dem_amendment.py",
        "activation_script_sha256": "a4cc4f86b0beb81f151ccdc0bc4a4ab5d674823d7c7a5879f0e223efcd36d256",
    }
    if any(dem_activation_evidence.get(key) != expected for key, expected in expected_evid_0031_bindings.items()):
        fail("EVID-0031 no longer preserves its published activation bindings")
    if dem_activation_evidence.get("status") != "pass_exact_dem_amendment_activated_preflight_pending":
        fail("EVID-0031 status differs")
    if dem_activation_evidence.get("assertions") != dem_activation_receipt.get("assertions"):
        fail("EVID-0031 and DEM amendment activation receipt have different claim boundaries")
    dem_preflight_evidence = ledger_by_id.get("EVID-0032")
    if not isinstance(dem_preflight_evidence, dict):
        fail("evidence ledger is missing EVID-0032 DEM preflight evidence")
    expected_evid_0032_bindings = {
        "source_gate_sha256": "5baac05a9e1ede4fa3ada02e4e2cd3bac9c3032164d280ef6886e0d519ae603e",
        "preflight_sha256": "18ca15363d92f6f04d672ddb3e97fef33524c94bcb54915d83c82dae77af38f1",
        "custody_initialization_sha256": "31d1b814d8da753dd2335f3110a49107df3f7a6c75875154a0fff0338b7e80a0",
        "active_intake_sha256": "2ae511c70303f15de590daf3eef4aac1e9dab1b7e0f85544c049ef69a60caa36",
        "active_verification_sha256": "6d7ee4aa05a6ead58d56ebc11d60f4aeb71489e02201f8b0462247b63f3cd27a",
        "completion_script_sha256": "9f83e8bf33373e665fdf50cce3e37a2e4bdf4d839338df07a0e31d6aef1c1767",
        "preflight_script_sha256": "c837997f9ec37daff6644089dae234a7bfdecf11401fb7f5cb9745993c91cfc2",
    }
    if any(dem_preflight_evidence.get(key) != value for key, value in expected_evid_0032_bindings.items()):
        fail("EVID-0032 no longer preserves its published preflight bindings")
    if dem_preflight_evidence.get("status") != "pass_exact_source_and_path_controls_no_payload":
        fail("EVID-0032 status differs")
    preflight_assertions = dem_preflight_evidence.get("assertions", {})
    if preflight_assertions != {
        "exact_license_match": True,
        "exact_tile_count": 4,
        "remote_identity_unchanged": True,
        "source_gate_ready": True,
        "external_paths_initialized_empty": True,
        "dem_payload_bytes_requested": False,
        "dem_payload_bytes_present": 0,
        "authentication_performed": False,
        "scientific_result_established": False,
    }:
        fail("EVID-0032 claim boundary differs")
    dem_transfer_readiness_evidence = ledger_by_id.get("EVID-0033")
    if not isinstance(dem_transfer_readiness_evidence, dict):
        fail("evidence ledger is missing EVID-0033 DEM transfer-runner readiness")
    expected_evid_0033_bindings = {
        "readiness_sha256": "515b692ac4717540d5347a518a6f8ea47625939c11ca92fc264133d960b92337",
        "runner_sha256": "2d4323754609853b5b350a9e81ecc4e66db2f1bcb91656e3ecaa36e6cf7b91b3",
        "test_sha256": "68432df023f64801709ea4d7c3cfde392d8f1875688c250680b3c229364a5764",
        "shared_transfer_core_sha256": "a858756a063148800be418bb7329ba148bcdce71b7812abafee6f7c9c62d8da9",
    }
    if any(dem_transfer_readiness_evidence.get(key) != value for key, value in expected_evid_0033_bindings.items()):
        fail("EVID-0033 no longer preserves its published readiness bindings")
    if dem_transfer_readiness_evidence.get("status") != "pass_local_controls_no_network_or_payload":
        fail("EVID-0033 status differs")
    if dem_transfer_readiness_evidence.get("assertions") != {
        "tests_passed": True,
        "test_count": 7,
        "network_requests_performed": False,
        "dem_payload_bytes_requested": False,
        "active_intake_mutated": False,
        "external_custody_mutated": False,
        "scientific_result_established": False,
    }:
        fail("EVID-0033 claim boundary differs")
    dem_acquisition_evidence = ledger_by_id.get("EVID-0034")
    if not isinstance(dem_acquisition_evidence, dict):
        fail("evidence ledger is missing EVID-0034 DEM acquisition evidence")
    if (
        dem_acquisition_evidence.get("status") != "pass_exact_four_tiles_promoted_geotiff_verification_pending"
        or dem_acquisition_evidence.get("summary_ref") != "records/acquisition/dem-acquisition-summary.json"
        or dem_acquisition_evidence.get("summary_sha256") != sha256("records/acquisition/dem-acquisition-summary.json")
        or dem_acquisition_evidence.get("promoted_tile_count") != 4
        or dem_acquisition_evidence.get("promoted_byte_count") != 170302058
        or dem_acquisition_evidence.get("failed_attempt_count") != 0
        or dem_acquisition_evidence.get("next_checkpoint") != "M2-DEM-GEOTIFF-VERIFICATION"
    ):
        fail("EVID-0034 DEM acquisition evidence differs")
    if dem_acquisition_evidence.get("assertions") != dem_acquisition_summary.get("assertions"):
        fail("EVID-0034 and DEM acquisition summary have different claim boundaries")
    dem_geotiff_readiness_evidence = ledger_by_id.get("EVID-0035")
    if not isinstance(dem_geotiff_readiness_evidence, dict):
        fail("evidence ledger is missing EVID-0035 DEM GeoTIFF verifier readiness")
    if (
        dem_geotiff_readiness_evidence.get("status") != "pass_fail_closed_wrapper_no_real_raster_read"
        or dem_geotiff_readiness_evidence.get("readiness_ref") != "records/acquisition/dem-geotiff-verifier-readiness.json"
        or dem_geotiff_readiness_evidence.get("readiness_sha256") != sha256("records/acquisition/dem-geotiff-verifier-readiness.json")
    ):
        fail("EVID-0035 DEM GeoTIFF verifier readiness differs")
    geotiff_readiness = json.loads((ROOT / "records/acquisition/dem-geotiff-verifier-readiness.json").read_text(encoding="utf-8"))
    if geotiff_readiness.get("status") != "pass_fail_closed_wrapper_no_real_raster_read" or geotiff_readiness.get("validation") != {"focused_test_count": 12, "full_test_count": 175, "project_checker": "pass"}:
        fail("DEM GeoTIFF verifier readiness validation differs")
    if dem_geotiff_readiness_evidence.get("assertions") != geotiff_readiness.get("assertions"):
        fail("EVID-0035 and DEM GeoTIFF verifier readiness have different claim boundaries")
    dem_geotiff_correction_evidence = ledger_by_id.get("EVID-0036")
    if not isinstance(dem_geotiff_correction_evidence, dict):
        fail("evidence ledger is missing EVID-0036 DEM GeoTIFF verifier correction")
    if (
        dem_geotiff_correction_evidence.get("status") != "pass_targeted_wrapper_correction_rerun_pending"
        or dem_geotiff_correction_evidence.get("correction_ref") != "records/acquisition/dem-geotiff-verifier-correction-001.json"
        or dem_geotiff_correction_evidence.get("correction_sha256") != sha256("records/acquisition/dem-geotiff-verifier-correction-001.json")
    ):
        fail("EVID-0036 DEM GeoTIFF verifier correction differs")
    geotiff_correction = json.loads((ROOT / "records/acquisition/dem-geotiff-verifier-correction-001.json").read_text(encoding="utf-8"))
    failed_geotiff_attempt = json.loads((ROOT / "records/acquisition/dem-verification/m2-dem-001.json").read_text(encoding="utf-8"))
    if (
        geotiff_correction.get("status") != "pass_targeted_wrapper_correction_rerun_pending"
        or geotiff_correction.get("supersedes_execution_result", {}).get("failure_sha256") != sha256("records/acquisition/dem-verification/m2-dem-001.json")
        or failed_geotiff_attempt.get("status") != "fail"
        or failed_geotiff_attempt.get("custody_inventory_before") != failed_geotiff_attempt.get("custody_inventory_after")
        or failed_geotiff_attempt.get("evaluation", {}).get("checks", {}).get("arcgis_runtime", {}).get("actual", {}).get("type") != "ExecuteError"
    ):
        fail("retained DEM GeoTIFF wrapper failure or correction binding differs")
    if dem_geotiff_correction_evidence.get("assertions") != geotiff_correction.get("assertions"):
        fail("EVID-0036 and DEM GeoTIFF correction have different claim boundaries")
    dem_statistics_correction_evidence = ledger_by_id.get("EVID-0037")
    if not isinstance(dem_statistics_correction_evidence, dict):
        fail("evidence ledger is missing EVID-0037 DEM statistics correction")
    if (
        dem_statistics_correction_evidence.get("status") != "pass_read_only_statistics_correction_rerun_pending"
        or dem_statistics_correction_evidence.get("correction_ref") != "records/acquisition/dem-geotiff-verifier-correction-002.json"
        or dem_statistics_correction_evidence.get("correction_sha256") != sha256("records/acquisition/dem-geotiff-verifier-correction-002.json")
    ):
        fail("EVID-0037 DEM statistics correction differs")
    statistics_correction = json.loads((ROOT / "records/acquisition/dem-geotiff-verifier-correction-002.json").read_text(encoding="utf-8"))
    second_failed_geotiff_attempt = json.loads((ROOT / "records/acquisition/dem-verification/m2-dem-001-attempt-002.json").read_text(encoding="utf-8"))
    if (
        statistics_correction.get("status") != "pass_read_only_statistics_correction_rerun_pending"
        or statistics_correction.get("supersedes_execution_result", {}).get("failure_sha256") != sha256("records/acquisition/dem-verification/m2-dem-001-attempt-002.json")
        or second_failed_geotiff_attempt.get("status") != "fail"
        or second_failed_geotiff_attempt.get("custody_inventory_before") != second_failed_geotiff_attempt.get("custody_inventory_after")
        or "no statistics are available" not in second_failed_geotiff_attempt.get("evaluation", {}).get("checks", {}).get("arcgis_runtime", {}).get("actual", {}).get("message", "")
    ):
        fail("retained DEM statistics failure or correction binding differs")
    if dem_statistics_correction_evidence.get("assertions") != statistics_correction.get("assertions"):
        fail("EVID-0037 and DEM statistics correction have different claim boundaries")
    dem_verification_completion_readiness_evidence = ledger_by_id.get("EVID-0038")
    if not isinstance(dem_verification_completion_readiness_evidence, dict):
        fail("evidence ledger is missing EVID-0038 four-tile ArcGIS readiness")
    if (
        dem_verification_completion_readiness_evidence.get("status") != "pass_four_structural_receipts_ready_for_reconciliation"
        or dem_verification_completion_readiness_evidence.get("readiness_ref") != "records/acquisition/dem-verification-completion-readiness.json"
        or dem_verification_completion_readiness_evidence.get("readiness_sha256") != sha256("records/acquisition/dem-verification-completion-readiness.json")
    ):
        fail("EVID-0038 four-tile ArcGIS readiness differs")
    completion_readiness = json.loads((ROOT / "records/acquisition/dem-verification-completion-readiness.json").read_text(encoding="utf-8"))
    if completion_readiness.get("status") != "pass_four_structural_receipts_ready_for_reconciliation" or completion_readiness.get("validation") != {"focused_test_count": 3, "full_test_count": 180, "project_checker": "pass"}:
        fail("DEM four-tile verification completion readiness differs")
    for item in completion_readiness.get("passing_receipts", []) + completion_readiness.get("retained_failed_receipts", []):
        relative = item.get("ref")
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or item.get("sha256") != sha256(relative):
            fail("DEM verification completion readiness has a stale receipt binding")
    if len(completion_readiness.get("passing_receipts", [])) != 4 or len(completion_readiness.get("retained_failed_receipts", [])) != 2:
        fail("DEM verification completion readiness receipt counts differ")
    if dem_verification_completion_readiness_evidence.get("assertions") != completion_readiness.get("assertions"):
        fail("EVID-0038 and DEM verification completion readiness have different claim boundaries")
    dem_verification_completion_evidence = ledger_by_id.get("EVID-0039")
    if not isinstance(dem_verification_completion_evidence, dict):
        fail("evidence ledger is missing EVID-0039 four-tile ArcGIS verification completion")
    expected_evid_0039_bindings = {
        "summary_ref": "records/acquisition/dem-verification-summary.json",
        "summary_sha256": "97f6a66daccd236decc6cdaac7035ca4cafb541ce7d82cecf08973ec6962f7ef",
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256": "db4329c6b10492d2c6985be528c5dceca13585736ee9f82fbf96e7f190ba92fa",
        "active_verification_ref": "contracts/m2-dem-offline-verification.json",
        "active_verification_sha256": "0c2d4208ce1e2f545eb5a442ea07ed15e07c749c9a02730362e7701352f061a8",
        "active_milestone_ref": "contracts/milestone-002.json",
        "active_milestone_sha256": "fb85eb26d3143cd23cf96598a0447b9d5e6f3a3b70e8bdc35693bf52f7b1cbca",
        "project_profile_ref": "records/project-control-profile.json",
        "project_profile_sha256": "a4504c2d438b9932a2d36eb5cf62fc86ca278156056689b8a4bb8c115551a7bd",
        "long_term_goal_ref": "records/long-term-goal.json",
        "long_term_goal_sha256": "ec695221ec99789e817108e4e7baa5aa3c65206dcd71a39bdf64c55b7c303ee6",
        "completion_script_ref": "scripts/complete_m2_dem_verification.py",
        "completion_script_sha256": "7e6fb424dfca69bd64075dc7799cfe9bae7b6cdbbcad60a458a9dee8a7ba9925",
        "test_ref": "tests/test_m2_dem_verification_completion.py",
        "test_sha256": "252e3ad97ba7a76a52dbd20f22fbea809a411f26bcdf2d413d3d9ffcd7213f5c",
    }
    if any(dem_verification_completion_evidence.get(key) != value for key, value in expected_evid_0039_bindings.items()):
        fail("EVID-0039 four-tile ArcGIS completion bindings differ")
    expected_evid_0039_assertions = {
        "passing_tile_count": 4,
        "retained_failed_attempt_count": 2,
        "verified_byte_count": 170302058,
        "finite_non_nodata_cell_count": 51840000,
        "nodata_or_nonfinite_cell_count": 0,
        "exact_local_byte_identity_established": True,
        "arcgis_geotiff_structural_fitness_established": True,
        "approved_aoi_valid_pixel_coverage_established": True,
        "void_seam_artifact_review_established": False,
        "vertical_datum_route_established": False,
        "radar_processing_executed": False,
        "scientific_result_established": False,
    }
    if (
        dem_verification_completion_evidence.get("status") != "pass_structural_and_valid_aoi_coverage_vertical_datum_deferred"
        or dem_verification_completion_evidence.get("next_checkpoint") != "M2-DEM-VERTICAL-DATUM-REVIEW"
        or dem_verification_completion_evidence.get("assertions") != expected_evid_0039_assertions
        or len(dem_verification_completion_evidence.get("retained_validation_failures", [])) != 2
    ):
        fail("EVID-0039 four-tile ArcGIS completion claim boundary differs")
    for item in dem_verification_completion_evidence.get("retained_validation_failures", []):
        relative = item.get("receipt_ref")
        if (
            not isinstance(relative, str)
            or not (ROOT / relative).is_file()
            or item.get("receipt_sha256") != sha256(relative)
            or item.get("status") != "fail_retained_superseded_as_data_result"
        ):
            fail("EVID-0039 retained DEM failure binding differs")
    dem_vertical_review_evidence = ledger_by_id.get("EVID-0040")
    if not isinstance(dem_vertical_review_evidence, dict):
        fail("evidence ledger is missing EVID-0040 DEM vertical-datum review readiness")
    expected_evid_0040_bindings = {
        "proposal_ref": "contracts/m2-dem-vertical-datum-proposal.json",
        "proposal_sha256": sha256("contracts/m2-dem-vertical-datum-proposal.json"),
        "review_bundle_ref": "reviews/m2-dem-vertical-datum/review-bundle.json",
        "review_bundle_sha256": sha256("reviews/m2-dem-vertical-datum/review-bundle.json"),
        "review_contract_ref": "reviews/m2-dem-vertical-datum/review-contract.json",
        "review_contract_sha256": sha256("reviews/m2-dem-vertical-datum/review-contract.json"),
        "blank_response_ref": "reviews/m2-dem-vertical-datum/blank-response.json",
        "blank_response_sha256": sha256("reviews/m2-dem-vertical-datum/blank-response.json"),
        "source_review_ref": "records/source-gates/m2-dem-vertical-datum-source-review.json",
        "source_review_sha256": sha256("records/source-gates/m2-dem-vertical-datum-source-review.json"),
        "local_capability_ref": "records/surface-receipts/m2-dem-vertical-datum-capability.json",
        "local_capability_sha256": sha256("records/surface-receipts/m2-dem-vertical-datum-capability.json"),
        "review_surface_ref": "docs/assets/m2-dem-vertical-datum-review.png",
        "review_surface_sha256": sha256("docs/assets/m2-dem-vertical-datum-review.png"),
        "render_receipt_ref": "records/surface-receipts/m2-dem-vertical-datum-review.json",
        "render_receipt_sha256": sha256("records/surface-receipts/m2-dem-vertical-datum-review.json"),
    }
    if any(dem_vertical_review_evidence.get(key) != value for key, value in expected_evid_0040_bindings.items()):
        fail("EVID-0040 DEM vertical-datum review bindings differ")
    expected_evid_0040_assertions = {
        "official_source_count": 8,
        "arcgis_version": "3.7.1",
        "builtin_egm96_grid_present": True,
        "egm2008_one_minute_grid_present": False,
        "usable_exact_egm2008_transform_count": 0,
        "human_decisions_present": 0,
        "method_route_approved": False,
        "license_or_terms_accepted": False,
        "software_downloaded_or_installed": False,
        "dem_preconversion_executed": False,
        "radar_processing_executed": False,
        "scientific_result_established": False,
    }
    if (
        dem_vertical_review_evidence.get("status") != "pass_review_ready_exact_egm2008_route_owner_install_pending"
        or dem_vertical_review_evidence.get("next_checkpoint") != "M2-DEM-VERTICAL-DATUM-REVIEW"
        or dem_vertical_review_evidence.get("assertions") != expected_evid_0040_assertions
    ):
        fail("EVID-0040 DEM vertical-datum review claim boundary differs")
    dem_portability_evidence = ledger_by_id.get("EVID-0041")
    if not isinstance(dem_portability_evidence, dict):
        fail("evidence ledger is missing EVID-0041 DEM acquisition portability correction")
    if (
        dem_portability_evidence.get("status") != dem_acquisition_portability.get("status")
        or dem_portability_evidence.get("correction_ref") != "records/acquisition/dem-acquisition-portability-correction.json"
        or dem_portability_evidence.get("correction_sha256") != sha256("records/acquisition/dem-acquisition-portability-correction.json")
        or dem_portability_evidence.get("reconciliation_script_ref") != "scripts/reconcile_m2_dem_acquisition.py"
        or dem_portability_evidence.get("reconciliation_script_sha256") != sha256("scripts/reconcile_m2_dem_acquisition.py")
        or dem_portability_evidence.get("test_ref") != "tests/test_m2_dem_acquisition_progress.py"
        or dem_portability_evidence.get("test_sha256") != sha256("tests/test_m2_dem_acquisition_progress.py")
        or dem_portability_evidence.get("failed_ci_run_id") != 33809208304
        or dem_portability_evidence.get("assertions") != dem_acquisition_portability.get("assertions")
    ):
        fail("EVID-0041 DEM acquisition portability correction differs")
    transfer_id_evidence = ledger_by_id.get("EVID-0042")
    if not isinstance(transfer_id_evidence, dict):
        fail("evidence ledger is missing EVID-0042 transfer-runner attempt-ID correction")
    if (
        transfer_id_evidence.get("status") != transfer_runner_correction.get("status")
        or transfer_id_evidence.get("correction_ref") != "records/acquisition/transfer-runner-attempt-id-correction.json"
        or transfer_id_evidence.get("correction_sha256") != sha256("records/acquisition/transfer-runner-attempt-id-correction.json")
        or transfer_id_evidence.get("transfer_runner_ref") != "scripts/acquire_m2_product.py"
        or transfer_id_evidence.get("transfer_runner_sha256") != "8a48b3bda9d729bceebf50e237f5671c967275d8203111aa8f8972aaddc3b645"
        or transfer_id_evidence.get("test_ref") != "tests/test_m2_transfer_core.py"
        or transfer_id_evidence.get("test_sha256") != sha256("tests/test_m2_transfer_core.py")
        or transfer_id_evidence.get("assertions") != transfer_runner_correction.get("assertions")
    ):
        fail("EVID-0042 transfer-runner attempt-ID correction differs")
    dem_terrain_readiness_evidence = ledger_by_id.get("EVID-0043")
    if not isinstance(dem_terrain_readiness_evidence, dict):
        fail("evidence ledger is missing EVID-0043 DEM terrain-quality predeclaration readiness")
    if (
        dem_terrain_readiness_evidence.get("status") != dem_terrain_readiness.get("status")
        or dem_terrain_readiness_evidence.get("readiness_ref") != "records/readiness/m2-dem-terrain-quality-readiness.json"
        or dem_terrain_readiness_evidence.get("readiness_sha256") != sha256("records/readiness/m2-dem-terrain-quality-readiness.json")
        or dem_terrain_readiness_evidence.get("contract_ref") != "config/qa/dem-terrain-quality-contract.json"
        or dem_terrain_readiness_evidence.get("contract_sha256") != sha256("config/qa/dem-terrain-quality-contract.json")
        or dem_terrain_readiness_evidence.get("assertions") != dem_terrain_readiness.get("assertions")
    ):
        fail("EVID-0043 DEM terrain-quality predeclaration readiness differs")
    dem_terrain_ci_evidence = ledger_by_id.get("EVID-0044")
    if not isinstance(dem_terrain_ci_evidence, dict):
        fail("evidence ledger is missing EVID-0044 DEM terrain-quality CI correction")
    if (
        dem_terrain_ci_evidence.get("status") != dem_terrain_ci_correction.get("status")
        or dem_terrain_ci_evidence.get("correction_ref") != "records/readiness/m2-dem-terrain-quality-ci-correction.json"
        or dem_terrain_ci_evidence.get("correction_sha256") != sha256("records/readiness/m2-dem-terrain-quality-ci-correction.json")
        or dem_terrain_ci_evidence.get("failed_run_ids") != [33819299553, 33819378562, 33819677224]
        or dem_terrain_ci_evidence.get("passing_run_id") != 33819458096
        or dem_terrain_ci_evidence.get("assertions") != dem_terrain_ci_correction.get("assertions")
    ):
        fail("EVID-0044 DEM terrain-quality CI correction differs")
    terrain_attempt_001_evidence = ledger_by_id.get("EVID-0045")
    if not isinstance(terrain_attempt_001_evidence, dict):
        fail("evidence ledger is missing EVID-0045 DEM terrain-quality attempt-001 failure")
    if (
        terrain_attempt_001_evidence.get("status") != dem_terrain_attempt_001_failure.get("status")
        or terrain_attempt_001_evidence.get("failure_ref") != "records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json"
        or terrain_attempt_001_evidence.get("failure_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json")
        or terrain_attempt_001_evidence.get("contract_sha256") != sha256("config/qa/dem-terrain-quality-contract.json")
        or terrain_attempt_001_evidence.get("assertions") != dem_terrain_attempt_001_failure.get("assertions")
    ):
        fail("EVID-0045 DEM terrain-quality attempt-001 failure differs")
    terrain_attempt_002_evidence = ledger_by_id.get("EVID-0046")
    if not isinstance(terrain_attempt_002_evidence, dict):
        fail("evidence ledger is missing EVID-0046 DEM terrain-quality attempt-002 predeclaration")
    if (
        terrain_attempt_002_evidence.get("status") != dem_terrain_attempt_002_readiness.get("status")
        or terrain_attempt_002_evidence.get("corrected_contract_ref") != "config/qa/dem-terrain-quality-contract-attempt-002.json"
        or terrain_attempt_002_evidence.get("corrected_contract_sha256") != sha256("config/qa/dem-terrain-quality-contract-attempt-002.json")
        or terrain_attempt_002_evidence.get("readiness_ref") != "records/readiness/m2-dem-terrain-quality-attempt-002-readiness.json"
        or terrain_attempt_002_evidence.get("readiness_sha256") != sha256("records/readiness/m2-dem-terrain-quality-attempt-002-readiness.json")
        or terrain_attempt_002_evidence.get("failed_attempt_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-001-failure.json")
        or terrain_attempt_002_evidence.get("assertions") != dem_terrain_attempt_002_readiness.get("assertions")
    ):
        fail("EVID-0046 DEM terrain-quality attempt-002 predeclaration differs")
    terrain_attempt_002_failure_evidence = ledger_by_id.get("EVID-0047")
    if not isinstance(terrain_attempt_002_failure_evidence, dict):
        fail("evidence ledger is missing EVID-0047 DEM terrain-quality attempt-002 failure")
    if (
        terrain_attempt_002_failure_evidence.get("status") != dem_terrain_attempt_002_failure.get("status")
        or terrain_attempt_002_failure_evidence.get("failure_ref") != "records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json"
        or terrain_attempt_002_failure_evidence.get("failure_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json")
        or terrain_attempt_002_failure_evidence.get("contract_sha256") != sha256("config/qa/dem-terrain-quality-contract-attempt-002.json")
        or terrain_attempt_002_failure_evidence.get("assertions") != dem_terrain_attempt_002_failure.get("assertions")
    ):
        fail("EVID-0047 DEM terrain-quality attempt-002 failure differs")
    terrain_attempt_003_evidence = ledger_by_id.get("EVID-0048")
    if not isinstance(terrain_attempt_003_evidence, dict):
        fail("evidence ledger is missing EVID-0048 DEM terrain-quality attempt-003 predeclaration")
    if (
        terrain_attempt_003_evidence.get("status") != dem_terrain_attempt_003_readiness.get("status")
        or terrain_attempt_003_evidence.get("corrected_contract_ref") != "config/qa/dem-terrain-quality-contract-attempt-003.json"
        or terrain_attempt_003_evidence.get("corrected_contract_sha256") != sha256("config/qa/dem-terrain-quality-contract-attempt-003.json")
        or terrain_attempt_003_evidence.get("readiness_ref") != "records/readiness/m2-dem-terrain-quality-attempt-003-readiness.json"
        or terrain_attempt_003_evidence.get("readiness_sha256") != sha256("records/readiness/m2-dem-terrain-quality-attempt-003-readiness.json")
        or terrain_attempt_003_evidence.get("failed_attempt_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality-attempt-002-failure.json")
        or terrain_attempt_003_evidence.get("implementation_sha256") != sha256("scripts/inspect_m2_dem_terrain_quality_arcgis_attempt_003.py")
        or terrain_attempt_003_evidence.get("assertions") != dem_terrain_attempt_003_readiness.get("assertions")
    ):
        fail("EVID-0048 DEM terrain-quality attempt-003 predeclaration differs")
    terrain_result_evidence = ledger_by_id.get("EVID-0049")
    if not isinstance(terrain_result_evidence, dict):
        fail("evidence ledger is missing EVID-0049 DEM terrain-quality result")
    if (
        terrain_result_evidence.get("status") != dem_terrain_result.get("status")
        or terrain_result_evidence.get("receipt_ref") != "records/surface-receipts/m2-dem-terrain-quality.json"
        or terrain_result_evidence.get("receipt_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality.json")
        or terrain_result_evidence.get("manifest_sha256") != dem_terrain_result.get("output_manifest_reconciliation", {}).get("manifest_sha256")
        or terrain_result_evidence.get("candidate_receipt_sha256") != dem_terrain_result.get("bindings", {}).get("candidate_receipt_sha256")
        or terrain_result_evidence.get("contract_sha256") != sha256("config/qa/dem-terrain-quality-contract-attempt-003.json")
        or terrain_result_evidence.get("quantitative_status") != "pass"
        or terrain_result_evidence.get("visual_status") != "pass"
        or terrain_result_evidence.get("stable_file_count") != 189
        or terrain_result_evidence.get("claim_boundary") != dem_terrain_result.get("claim_boundary")
    ):
        fail("EVID-0049 DEM terrain-quality result differs")
    terrain_audit_evidence = ledger_by_id.get("EVID-0050")
    if not isinstance(terrain_audit_evidence, dict):
        fail("evidence ledger is missing EVID-0050 DEM terrain readiness audit")
    if (
        terrain_audit_evidence.get("status") != "defer"
        or terrain_audit_evidence.get("audit_input_ref") != "records/readiness/m2-dem-terrain-readiness-input.json"
        or terrain_audit_evidence.get("audit_input_sha256") != sha256("records/readiness/m2-dem-terrain-readiness-input.json")
        or terrain_audit_evidence.get("decision_ref") != "records/readiness/m2-dem-terrain-readiness-decision.json"
        or terrain_audit_evidence.get("decision_sha256") != sha256("records/readiness/m2-dem-terrain-readiness-decision.json")
        or terrain_audit_evidence.get("candidate_manifest_sha256") != dem_terrain_audit_decision.get("candidate_manifest_sha256")
        or terrain_audit_evidence.get("pass_gate_ids") != [
            "coverage-and-balance",
            "provenance-and-custody",
            "reproducibility",
            "schema-and-quality",
            "source-and-terms",
        ]
        or terrain_audit_evidence.get("deferred_gate_ids") != dem_terrain_audit_decision.get("deferred_required_gate_ids")
        or terrain_audit_evidence.get("authorized_next_actions") != []
        or terrain_audit_evidence.get("authority_created") is not False
    ):
        fail("EVID-0050 DEM terrain readiness audit differs")
    terrain_review_evidence = ledger_by_id.get("EVID-0051")
    if not isinstance(terrain_review_evidence, dict):
        fail("evidence ledger is missing EVID-0051 DEM terrain-result review preparation")
    expected_terrain_review_assertions = {
        "review_bundle_ready_for_handoff": True,
        "blank_state_verified": True,
        "completion_controls_verified": True,
        "export_verified": True,
        "dem_derived_map_pixels_embedded": False,
        "vertical_datum_resolved": False,
        "radar_processing_authorized_by_review": False,
        "scientific_result_established": False,
        "authority_created": False,
    }
    if (
        terrain_review_evidence.get("status") != "pass_review_ready_zero_human_decisions"
        or terrain_review_evidence.get("proposal_sha256") != sha256("contracts/m2-dem-terrain-result-review-proposal.json")
        or terrain_review_evidence.get("bundle_sha256") != sha256("reviews/m2-dem-terrain-result/review-bundle.json")
        or terrain_review_evidence.get("contract_sha256") != sha256("reviews/m2-dem-terrain-result/review-contract.json")
        or terrain_review_evidence.get("blank_response_sha256") != sha256("reviews/m2-dem-terrain-result/blank-response.json")
        or terrain_review_evidence.get("review_surface_sha256") != sha256("docs/assets/m2-dem-terrain-result-review.png")
        or terrain_review_evidence.get("render_receipt_sha256") != sha256("records/surface-receipts/m2-dem-terrain-result-review.json")
        or terrain_review_evidence.get("candidate_receipt_sha256") != sha256("records/surface-receipts/m2-dem-terrain-quality.json")
        or terrain_review_evidence.get("external_review_artifact_count") != 4
        or terrain_review_evidence.get("human_decision_count") != 0
        or terrain_review_evidence.get("assertions") != expected_terrain_review_assertions
    ):
        fail("EVID-0051 DEM terrain-result review preparation differs")

    orbit_review_evidence = ledger_by_id.get("EVID-0052")
    if (
        not isinstance(orbit_review_evidence, dict)
        or orbit_review_evidence.get("status") != "ready_for_human_review_source_gate_blocked"
        or orbit_review_evidence.get("proposal_sha256") != sha256("contracts/milestone-002-orbit-amendment-proposal.json")
        or orbit_review_evidence.get("bundle_sha256") != sha256("reviews/m2-orbit-amendment/review-bundle.json")
        or orbit_review_evidence.get("contract_sha256") != sha256("reviews/m2-orbit-amendment/review-contract.json")
        or orbit_review_evidence.get("human_decision_count") != 0
        or orbit_review_evidence.get("assertions", {}).get("authority_created") is not False
    ):
        fail("EVID-0052 orbit amendment review preparation differs")
    orbit_activation_evidence = ledger_by_id.get("EVID-0053")
    if (
        not isinstance(orbit_activation_evidence, dict)
        or orbit_activation_evidence.get("status") != "pass_exact_orbit_amendment_activated_preflight_and_sentinel_custody_pending"
        or orbit_activation_evidence.get("activation_receipt_sha256") != sha256("records/acquisition/orbit-amendment-activation.json")
        or orbit_activation_evidence.get("approval_sha256") != sha256("records/source-gates/m2-orbit-amendment-approval.json")
        or orbit_activation_evidence.get("reconciliation_sha256") != sha256("records/source-gates/m2-orbit-amendment-review-reconciliation.json")
        or orbit_activation_evidence.get("assertions") != orbit_activation.get("assertions")
    ):
        fail("EVID-0053 orbit amendment activation differs")
    orbit_preflight_evidence = ledger_by_id.get("EVID-0054")
    if (
        not isinstance(orbit_preflight_evidence, dict)
        or orbit_preflight_evidence.get("status") != "pass_no_payload_no_external_mutation_sentinel_custody_pending"
        or orbit_preflight_evidence.get("preflight_sha256") != sha256("records/acquisition/orbit-preflight.json")
        or orbit_preflight_evidence.get("source_gate_sha256") != sha256("records/source-gates/m2-orbit-live-source-gate.json")
        or orbit_preflight_evidence.get("assertions") != orbit_preflight.get("assertions")
    ):
        fail("EVID-0054 orbit fresh preflight differs")
    orbit_custody_failure_evidence = ledger_by_id.get("EVID-0055")
    if (
        not isinstance(orbit_custody_failure_evidence, dict)
        or orbit_custody_failure_evidence.get("status") != orbit_custody_failure.get("status")
        or orbit_custody_failure_evidence.get("failure_sha256") != sha256("records/acquisition/orbit-custody-initialization-attempt-001-failure.json")
        or orbit_custody_failure_evidence.get("assertions") != orbit_custody_failure.get("assertions")
    ):
        fail("EVID-0055 orbit custody initialization failure differs")
    orbit_custody_readiness_evidence = ledger_by_id.get("EVID-0056")
    if (
        not isinstance(orbit_custody_readiness_evidence, dict)
        or orbit_custody_readiness_evidence.get("status") != orbit_custody_readiness.get("status")
        or orbit_custody_readiness_evidence.get("readiness_sha256") != sha256("records/acquisition/orbit-custody-initialization-attempt-002-readiness.json")
        or orbit_custody_readiness_evidence.get("failure_sha256") != sha256("records/acquisition/orbit-custody-initialization-attempt-001-failure.json")
        or orbit_custody_readiness_evidence.get("implementation_sha256") != sha256("scripts/initialize_m2_orbit_custody.py")
    ):
        fail("EVID-0056 orbit custody attempt-002 readiness differs")
    orbit_custody_evidence = ledger_by_id.get("EVID-0057")
    if (
        not isinstance(orbit_custody_evidence, dict)
        or orbit_custody_evidence.get("status") != "pass_empty_custody_initialized_sentinel_custody_pending"
        or orbit_custody_evidence.get("custody_receipt_sha256") != sha256("records/acquisition/orbit-custody-initialization.json")
        or orbit_custody_evidence.get("attempt_001_failure_sha256") != sha256("records/acquisition/orbit-custody-initialization-attempt-001-failure.json")
        or orbit_custody_evidence.get("attempt_002_readiness_sha256") != sha256("records/acquisition/orbit-custody-initialization-attempt-002-readiness.json")
        or orbit_custody_evidence.get("initialization_script_sha256") != sha256("scripts/initialize_m2_orbit_custody.py")
        or orbit_custody_evidence.get("assertions", {}).get("orbit_payload_bytes_requested") != 0
        or orbit_custody_evidence.get("assertions", {}).get("sentinel_promoted_and_verified_count") != 0
    ):
        fail("EVID-0057 orbit empty custody initialization differs")
    orbit_runner_evidence = ledger_by_id.get("EVID-0058")
    if (
        not isinstance(orbit_runner_evidence, dict)
        or orbit_runner_evidence.get("status") != orbit_runner_readiness.get("status")
        or orbit_runner_evidence.get("readiness_ref") != "records/acquisition/orbit-runner-readiness.json"
        or orbit_runner_evidence.get("readiness_sha256") != sha256("records/acquisition/orbit-runner-readiness.json")
        or orbit_runner_evidence.get("execution_bindings") != {
            key: value
            for key, value in expected_orbit_runner_bindings.items()
            if key.startswith(("scripts_", "tests_", "_github_"))
        }
        or orbit_runner_evidence.get("dependency") != orbit_runner_readiness.get("dependency")
        or orbit_runner_evidence.get("verification") != orbit_runner_readiness.get("verification")
        or orbit_runner_evidence.get("assertions") != orbit_runner_readiness.get("assertions")
    ):
        fail("EVID-0058 orbit runner readiness differs")
    orbit_schema_correction_evidence = ledger_by_id.get("EVID-0059")
    if (
        not isinstance(orbit_schema_correction_evidence, dict)
        or orbit_schema_correction_evidence.get("status") != orbit_intake_schema_correction.get("status")
        or orbit_schema_correction_evidence.get("failure_sha256") != sha256("records/acquisition/orbit-intake-schema-validation-failure.json")
        or orbit_schema_correction_evidence.get("correction_ref") != "records/acquisition/orbit-intake-schema-correction.json"
        or orbit_schema_correction_evidence.get("correction_sha256") != sha256("records/acquisition/orbit-intake-schema-correction.json")
        or orbit_schema_correction_evidence.get("active_intake_sha256") != "b52512ecf86a7d85f99f5cff932219bc29620f08871e3b3242b76b645b0e2604"
        or orbit_schema_correction_evidence.get("historical_runner_readiness_sha256") != sha256("records/acquisition/orbit-runner-readiness.json")
        or orbit_schema_correction_evidence.get("verification") != orbit_intake_schema_correction.get("verification")
        or orbit_schema_correction_evidence.get("assertions") != orbit_intake_schema_correction.get("assertions")
    ):
        fail("EVID-0059 orbit active-intake schema correction differs")
    orbit_label_correction_evidence = ledger_by_id.get("EVID-0060")
    if (
        not isinstance(orbit_label_correction_evidence, dict)
        or orbit_label_correction_evidence.get("status") != orbit_intake_label_correction.get("status")
        or orbit_label_correction_evidence.get("finding_sha256") != sha256("records/acquisition/orbit-intake-activation-label-inconsistency.json")
        or orbit_label_correction_evidence.get("correction_ref") != "records/acquisition/orbit-intake-activation-label-correction.json"
        or orbit_label_correction_evidence.get("correction_sha256") != sha256("records/acquisition/orbit-intake-activation-label-correction.json")
        or orbit_label_correction_evidence.get("active_intake_sha256") != "9e1c2675b4716ec78fbca8c3c2e9cf0bd3df20cf6362b5bba0db4de582a27539"
        or orbit_label_correction_evidence.get("validation") != orbit_intake_label_correction.get("validation")
        or orbit_label_correction_evidence.get("assertions") != orbit_intake_label_correction.get("assertions")
    ):
        fail("EVID-0060 orbit active-intake activation label correction differs")

    sentinel_refresh_evidence = ledger_by_id.get("EVID-0061")
    expected_sentinel_refresh_bindings = {
        "terms_reconciliation_sha256": sha256("records/source-gates/m2-terms-page-reconciliation.json"),
        "source_gate_refresh_sha256": sha256("records/source-gates/m2-live-source-gate-refresh.json"),
        "preflight_refresh_sha256": sha256("records/acquisition/preflight-refresh.json"),
        "page_identity_sha256": sha256("scripts/m2_page_identity.py"),
        "preflight_refresh_script_sha256": sha256("scripts/refresh_m2_preflight.py"),
        "transfer_runner_sha256": sha256("scripts/acquire_m2_product.py"),
        "test_sha256": sha256("tests/test_m2_page_identity.py"),
    }
    if (
        sentinel_refresh_readiness.get("status") != "pass_refreshed_preflight_ready_secret_safe_token_reference_pending"
        or sentinel_refresh_readiness.get("bindings") != expected_sentinel_refresh_bindings
        or sentinel_refresh_readiness.get("assertions", {}).get("sentinel_payload_bytes_received") != 0
        or sentinel_refresh_readiness.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or sentinel_refresh_readiness.get("assertions", {}).get("external_custody_mutated") is not False
        or not isinstance(sentinel_refresh_evidence, dict)
        or sentinel_refresh_evidence.get("status") != sentinel_refresh_readiness.get("status")
        or sentinel_refresh_evidence.get("readiness_sha256") != sha256("records/acquisition/sentinel-preflight-refresh-readiness.json")
        or sentinel_refresh_evidence.get("bindings") != expected_sentinel_refresh_bindings
        or sentinel_refresh_evidence.get("assertions") != sentinel_refresh_readiness.get("assertions")
    ):
        fail("EVID-0061 Sentinel terms reconciliation and preflight refresh differ")

    sentinel_acquisition_evidence = ledger_by_id.get("EVID-0062")
    expected_attempt_receipts = {
        item["source_id"]: item["transfer_receipt_sha256"]
        for item in successful_reconciliation
    }
    expected_attempt_receipts["M1-SRC-004"] = failed_attempt_sha
    expected_container_receipts = {
        item["source_id"]: item["container_receipt_sha256"]
        for item in successful_reconciliation
    }
    if (
        not isinstance(sentinel_acquisition_evidence, dict)
        or sentinel_acquisition_evidence.get("status") != "pass_three_promoted_one_retained_failure_recovery_review_ready"
        or sentinel_acquisition_evidence.get("reconciliation_sha256") != sha256("records/acquisition/sentinel-acquisition-reconciliation-001.json")
        or sentinel_acquisition_evidence.get("active_intake_sha256") != "734455b7c0e772aa22253a81f944dc685e4c73cf73490ca2f821d12d7e2b5ca0"
        or sentinel_acquisition_evidence.get("recovery_proposal_sha256") != expected_recovery_proposal_sha
        or sentinel_acquisition_evidence.get("review_bundle_sha256") != expected_recovery_bundle_sha
        or sentinel_acquisition_evidence.get("review_contract_sha256") != sha256("reviews/m2-sentinel-recovery/review-contract.json")
        or sentinel_acquisition_evidence.get("blank_response_sha256") != sha256("reviews/m2-sentinel-recovery/blank-response.json")
        or sentinel_acquisition_evidence.get("review_surface_sha256") != expected_recovery_surface_sha
        or sentinel_acquisition_evidence.get("attempt_receipt_sha256") != expected_attempt_receipts
        or sentinel_acquisition_evidence.get("container_receipt_sha256") != expected_container_receipts
        or sentinel_acquisition_evidence.get("state_counts") != {"authorized": 4, "failed": 1, "promoted": 3}
        or sentinel_acquisition_evidence.get("assertions", {}).get("recovery_transfers_performed") != 0
        or sentinel_acquisition_evidence.get("assertions", {}).get("human_decision_count") != 0
        or sentinel_acquisition_evidence.get("assertions", {}).get("retry_automatically_authorized") is not False
        or sentinel_acquisition_evidence.get("assertions", {}).get("credential_values_recorded") is not False
        or sentinel_acquisition_evidence.get("assertions", {}).get("pixel_usability_established") is not False
        or sentinel_acquisition_evidence.get("assertions", {}).get("scientific_fitness_established") is not False
    ):
        fail("EVID-0062 Sentinel acquisition and recovery review differs")

    materialization_boundary_evidence = ledger_by_id.get("EVID-0063")
    if (
        not isinstance(materialization_boundary_evidence, dict)
        or materialization_boundary_evidence.get("status") != materialization_boundary_reconciliation.get("status")
        or materialization_boundary_evidence.get("reconciliation_ref") != "records/acquisition/materialization-test-boundary-reconciliation-001.json"
        or materialization_boundary_evidence.get("reconciliation_sha256") != sha256("records/acquisition/materialization-test-boundary-reconciliation-001.json")
        or materialization_boundary_evidence.get("materialization_receipt_ref") != "records/acquisition/materialization/m1-src-001-fixture-must-not-run.json"
        or materialization_boundary_evidence.get("materialization_receipt_sha256") != sha256("records/acquisition/materialization/m1-src-001-fixture-must-not-run.json")
        or materialization_boundary_evidence.get("external_manifest_sha256") != materialization_boundary_reconciliation.get("outcome", {}).get("external_manifest_sha256")
        or materialization_boundary_evidence.get("file_count") != 26
        or materialization_boundary_evidence.get("total_extracted_bytes") != 1732324248
        or materialization_boundary_evidence.get("assertions", {}).get("full_manifest_file_hash_verification") != "pass"
        or materialization_boundary_evidence.get("assertions", {}).get("repeat_automatically_authorized") is not False
        or materialization_boundary_evidence.get("assertions", {}).get("next_processing_released") is not False
        or materialization_boundary_evidence.get("assertions", {}).get("pixel_usability_established") is not False
        or materialization_boundary_evidence.get("assertions", {}).get("scientific_admission_authorized") is not False
    ):
        fail("EVID-0063 test-induced materialization reconciliation differs")

    orbit_boundary_evidence = ledger_by_id.get("EVID-0064")
    if (
        not isinstance(orbit_boundary_evidence, dict)
        or orbit_boundary_evidence.get("status") != "review_required_zero_byte_failure_preserved_full_m2_verify_guard_pass_orbit_recovery_review_ready"
        or orbit_boundary_evidence.get("reconciliation_sha256") != sha256("records/acquisition/orbit-test-boundary-reconciliation-001.json")
        or orbit_boundary_evidence.get("runner_correction_sha256") != sha256("records/acquisition/orbit-runner-production-boundary-correction-001.json")
        or orbit_boundary_evidence.get("failed_attempt_sha256") != sha256("records/acquisition/orbit-attempts/m2-orb-001-20260904t050937z-8ed21d05.json")
        or orbit_boundary_evidence.get("recovery_proposal_sha256") != expected_orbit_recovery_proposal_sha
        or orbit_boundary_evidence.get("review_bundle_sha256") != expected_orbit_recovery_bundle_sha
        or orbit_boundary_evidence.get("review_contract_sha256") != sha256("reviews/m2-orbit-recovery/review-contract.json")
        or orbit_boundary_evidence.get("blank_response_sha256") != sha256("reviews/m2-orbit-recovery/blank-response.json")
        or orbit_boundary_evidence.get("review_surface_sha256") != expected_orbit_recovery_surface_sha
        or orbit_boundary_evidence.get("state_counts") != {
            "orbit": {"authorized": 3, "failed": 1, "promoted": 0},
            "sentinel": {"authorized": 4, "failed": 1, "promoted": 3},
        }
        or orbit_boundary_evidence.get("assertions", {}).get("owner_credential_used_in_failed_attempt") is not False
        or orbit_boundary_evidence.get("assertions", {}).get("orbit_payload_bytes_received") != 0
        or orbit_boundary_evidence.get("assertions", {}).get("runner_requires_full_m2_verify_dependency") is not True
        or orbit_boundary_evidence.get("assertions", {}).get("guard_precedes_catalogue_and_token_access") is not True
        or orbit_boundary_evidence.get("assertions", {}).get("retry_automatically_authorized") is not False
        or orbit_boundary_evidence.get("assertions", {}).get("human_decision_count") != 0
        or orbit_boundary_evidence.get("assertions", {}).get("radar_processing_performed") is not False
        or orbit_boundary_evidence.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("EVID-0064 orbit boundary correction and recovery review differs")

    acquisition_progress_portability_evidence = ledger_by_id.get("EVID-0065")
    if (
        not isinstance(acquisition_progress_portability_evidence, dict)
        or acquisition_progress_portability_evidence.get("status") != "pass_windows_started_event_basename_portable_local_ci_reverification_pending"
        or acquisition_progress_portability_evidence.get("correction_ref") != "records/acquisition/acquisition-progress-windows-path-portability-correction.json"
        or acquisition_progress_portability_evidence.get("correction_sha256") != sha256("records/acquisition/acquisition-progress-windows-path-portability-correction.json")
        or acquisition_progress_portability_evidence.get("failed_ci_run_id") != 33900195532
        or acquisition_progress_portability_evidence.get("failed_commit") != "226157b187b0475c6ee3a8849b95b76e1d02c8c1"
        or acquisition_progress_portability_evidence.get("validator_sha256") != "b54301d9f690b178b75995a29ad84598b6f3555ddc2e0eff735d96c331572545"
        or acquisition_progress_portability_evidence.get("test_sha256") != "286f02a8cd023faabcd9c61e198679f1b0e5dc566e15586beddeb6e95e44b9f0"
        or acquisition_progress_portability_evidence.get("validation", {}).get("focused_acquisition_progress_test_count") != 10
        or acquisition_progress_portability_evidence.get("validation", {}).get("focused_acquisition_progress_tests") != "pass"
        or acquisition_progress_portability_evidence.get("validation", {}).get("new_ci_run") != "pending"
        or acquisition_progress_portability_evidence.get("assertions", {}).get("external_custody_mutated") is not False
        or acquisition_progress_portability_evidence.get("assertions", {}).get("network_requests_performed_by_correction") is not False
        or acquisition_progress_portability_evidence.get("assertions", {}).get("product_bytes_requested_by_correction") != 0
        or acquisition_progress_portability_evidence.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("EVID-0065 acquisition-progress portability correction differs")

    acquisition_progress_ci_evidence = ledger_by_id.get("EVID-0066")
    if (
        not isinstance(acquisition_progress_ci_evidence, dict)
        or acquisition_progress_ci_evidence.get("status") != "pass_repository_and_project_control_tests"
        or acquisition_progress_ci_evidence.get("workflow") != "Validate project controls"
        or acquisition_progress_ci_evidence.get("run_id") != 33900641522
        or acquisition_progress_ci_evidence.get("head_sha") != "c73dab23bef6afd9a7b7afe3d78e265fd32c2196"
        or acquisition_progress_ci_evidence.get("correction_sha256") != sha256("records/acquisition/acquisition-progress-windows-path-portability-correction.json")
        or acquisition_progress_ci_evidence.get("verification") != {
            "repository_validation": "pass",
            "project_control_tests": "pass",
            "workflow_conclusion": "success",
        }
        or acquisition_progress_ci_evidence.get("retained_failure", {}).get("run_id") != 33900195532
        or acquisition_progress_ci_evidence.get("retained_failure", {}).get("conclusion") != "failure"
        or acquisition_progress_ci_evidence.get("retained_failure", {}).get("reclassified") is not False
        or acquisition_progress_ci_evidence.get("assertions", {}).get("external_custody_mutated_by_ci") is not False
        or acquisition_progress_ci_evidence.get("assertions", {}).get("credential_values_available_to_ci") is not False
        or acquisition_progress_ci_evidence.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("EVID-0066 acquisition-progress Linux CI reverification differs")

    sentinel_materialization_evidence = ledger_by_id.get("EVID-0067")
    if (
        not isinstance(sentinel_materialization_evidence, dict)
        or sentinel_materialization_evidence.get("status") != sentinel_materialization_reconciliation.get("status")
        or sentinel_materialization_evidence.get("reconciliation_ref") != "records/acquisition/sentinel-materialization-reconciliation-001.json"
        or sentinel_materialization_evidence.get("reconciliation_sha256") != sha256("records/acquisition/sentinel-materialization-reconciliation-001.json")
        or sentinel_materialization_evidence.get("receipt_sha256") != {
            item["source_id"]: item["receipt_sha256"] for item in materialization_records
        }
        or sentinel_materialization_evidence.get("external_manifest_sha256") != {
            item["source_id"]: item["external_manifest_sha256"] for item in materialization_records
        }
        or sentinel_materialization_evidence.get("summary") != {
            "materialized_source_count": 3,
            "planned_materialization_count": 2,
            "retained_unintended_test_materialization_count": 1,
            "verified_file_count": 78,
            "total_extracted_bytes": 5183550209,
        }
        or sentinel_materialization_evidence.get("assertions", {}).get("network_requests_performed") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("authentication_performed") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("source_archives_mutated") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("raster_readability_established") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("pixel_usability_established") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("baseline_established") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("change_established") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("scientific_admission_authorized") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("current_checkpoint_changed") is not False
        or sentinel_materialization_evidence.get("assertions", {}).get("recovery_authority_created") is not False
    ):
        fail("EVID-0067 Sentinel materialization continuation differs or overclaims")

    radar_input_evidence = ledger_by_id.get("EVID-0068")
    if (
        not isinstance(radar_input_evidence, dict)
        or radar_input_evidence.get("status") != radar_input_readiness.get("status")
        or radar_input_evidence.get("contract_ref") != "config/qa/radar-input-readiness-contract.json"
        or radar_input_evidence.get("contract_sha256") != sha256("config/qa/radar-input-readiness-contract.json")
        or radar_input_evidence.get("control_receipt_ref") != "records/surface-receipts/radar-input-readiness-control.json"
        or radar_input_evidence.get("control_receipt_sha256") != sha256("records/surface-receipts/radar-input-readiness-control.json")
        or radar_input_evidence.get("synthetic_arcgis_receipt_sha256") != sha256("records/surface-receipts/radar-input-readiness-synthetic-arcgis.json")
        or radar_input_evidence.get("protocol_sha256") != sha256("docs/RADAR_INPUT_READINESS_PROTOCOL.md")
        or radar_input_evidence.get("validation") != {
            "portable_test_count": 14,
            "portable_tests": "pass",
            "synthetic_arcgis_status": "pass_synthetic_arcgis_real_input_deferred",
            "synthetic_source_count": 3,
            "synthetic_measurement_raster_count": 6,
            "intentional_header_mismatch": "block",
            "deterministic_contract_derivation": "pass_exact_bytes",
        }
        or radar_input_evidence.get("retained_prepublication_attempt_count") != 6
        or any(radar_input_evidence.get("assertions", {}).get(key) is not False for key in (
            "external_custody_accessed", "real_materialization_receipt_used", "real_product_metadata_read",
            "real_product_raster_header_opened", "real_product_pixel_values_examined", "network_requests_performed",
            "authentication_performed", "credential_values_read_or_recorded", "complete_pair_established",
            "baseline_processing_released", "change_established", "scientific_admission_authorized",
            "current_checkpoint_changed", "recovery_authority_created",
        ))
    ):
        fail("EVID-0068 Sentinel-1 input-readiness predeclaration differs or overclaims")

    radar_input_real_evidence = ledger_by_id.get("EVID-0069")
    if (
        not isinstance(radar_input_real_evidence, dict)
        or radar_input_real_evidence.get("status") != radar_input_real_reconciliation.get("status")
        or radar_input_real_evidence.get("contract_sha256") != sha256("config/qa/radar-input-readiness-contract.json")
        or radar_input_real_evidence.get("real_receipt_ref") != "records/readiness/radar-input/m2-s1-input-readiness-real-001.json"
        or radar_input_real_evidence.get("real_receipt_sha256") != sha256("records/readiness/radar-input/m2-s1-input-readiness-real-001.json")
        or radar_input_real_evidence.get("reconciliation_ref") != "records/surface-receipts/radar-input-readiness-real-reconciliation.json"
        or radar_input_real_evidence.get("reconciliation_sha256") != sha256("records/surface-receipts/radar-input-readiness-real-reconciliation.json")
        or radar_input_real_evidence.get("publication_gate") != radar_input_real_reconciliation.get("publication_gate")
        or radar_input_real_evidence.get("external_custody_reverification") != radar_input_real_reconciliation.get("external_custody_reverification")
        or radar_input_real_evidence.get("disposition") != radar_input_real_reconciliation.get("disposition")
        or radar_input_real_evidence.get("assertions") != radar_input_real_reconciliation.get("assertions")
        or radar_input_real_evidence.get("observed_result") != {
            "source_count": 3,
            "source_pass_count": 0,
            "source_block_count": 3,
            "required_member_inventory_pass_count": 3,
            "annotation_parse_count": 6,
            "annotation_pixel_value_observed_set": ["Detected"],
            "measurement_header_open_count": 6,
            "all_measurement_headers_one_band_u16": True,
            "blocking_error_count": 6,
        }
    ):
        fail("EVID-0069 Sentinel-1 real input-readiness result differs or overclaims")

    radar_label_review_evidence = ledger_by_id.get("EVID-0070")
    if (
        not isinstance(radar_label_review_evidence, dict)
        or radar_label_review_evidence.get("status") != "review_ready_zero_human_decisions"
        or radar_label_review_evidence.get("source_gate_sha256") != sha256("records/source-gates/m2-radar-input-label-specification-source-gate.json")
        or radar_label_review_evidence.get("proposal_sha256") != sha256("contracts/milestone-002-radar-input-readiness-amendment-proposal.json")
        or radar_label_review_evidence.get("review_bundle_sha256") != sha256("reviews/m2-radar-input-readiness-amendment/review-bundle.json")
        or radar_label_review_evidence.get("review_contract_sha256") != sha256("reviews/m2-radar-input-readiness-amendment/review-contract.json")
        or radar_label_review_evidence.get("blank_response_sha256") != sha256("reviews/m2-radar-input-readiness-amendment/blank-response.json")
        or radar_label_review_evidence.get("surface_receipt_sha256") != sha256("records/surface-receipts/m2-radar-input-readiness-amendment-review.json")
        or radar_label_review_evidence.get("source_findings") != radar_label_source_gate.get("findings")
        or radar_label_review_evidence.get("review_state") != {
            "item_count": 1,
            "human_decision_count": 0,
            "completed": False,
            "attestation": False,
            "allowed_decisions": ["approve", "revise", "defer"],
        }
        or any(radar_label_review_evidence.get("assertions", {}).get(key) is not False for key in (
            "third_party_document_downloaded_to_project", "failed_contract_or_receipt_modified",
            "amendment_active", "corrected_contract_created", "synthetic_amendment_run_executed",
            "real_002_executed", "real_product_pixel_values_examined", "baseline_processing_released",
            "scientific_admission_authorized", "current_checkpoint_changed",
            "sentinel_recovery_authority_created", "orbit_recovery_authority_created",
        ))
    ):
        fail("EVID-0070 Sentinel-1 label-amendment review readiness differs or overclaims")

    arcgis_package_contract = json.loads(
        (ROOT / "config/qa/arcgis-package-portability-contract.json").read_text(encoding="utf-8")
    )
    arcgis_package_control = json.loads(
        (ROOT / "records/readiness/arcgis-package-portability-control.json").read_text(encoding="utf-8")
    )
    portability_errors = validate_arcgis_package_portability_contract(arcgis_package_contract)
    if portability_errors:
        fail("ArcGIS package portability contract differs: " + "; ".join(portability_errors))
    portability_bindings = arcgis_package_control.get("bindings", {})
    expected_portability_bindings = {
        "contract_ref": "config/qa/arcgis-package-portability-contract.json",
        "portable_core_ref": "scripts/arcgis_package_portability_core.py",
        "arcgis_runner_ref": "scripts/run_arcgis_package_portability_arcgis.py",
        "test_ref": "tests/test_arcgis_package_portability.py",
        "protocol_ref": "docs/ARCGIS_PACKAGE_PORTABILITY_PROTOCOL.md",
        "source_receipt_ref": "records/surface-receipts/arcgis-evidence-workspace.json",
    }
    if (
        arcgis_package_control.get("status") != "pass_predeclared_source_revalidated_real_package_not_run"
        or arcgis_package_control.get("validation", {}).get("portable_test_count") != 7
        or arcgis_package_control.get("validation", {}).get("portable_test_status") != "pass"
        or arcgis_package_control.get("validation", {}).get("source_stable_inventory")
        != arcgis_package_contract["source_workspace"]["expected_inventory"]
        or arcgis_package_control.get("validation", {}).get("prepublication_guard_probe")
        != "stopped_repository_not_clean_before_external_output"
        or arcgis_package_control.get("external_state") != {
            "attempt_001_exists": False,
            "project_package_created": False,
            "package_extracted": False,
            "round_trip_export_created": False,
            "source_workspace_mutated": False,
        }
        or any(portability_bindings.get(ref_key) != ref for ref_key, ref in expected_portability_bindings.items())
        or any(
            portability_bindings.get(ref_key.replace("_ref", "_sha256")) != sha256(ref)
            for ref_key, ref in expected_portability_bindings.items()
        )
        or any(arcgis_package_control.get("assertions", {}).get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "satellite_or_dem_pixels_read", "scientific_evidence_created", "clean_machine_portability_established",
            "m6_complete", "current_checkpoint_changed", "authority_created",
        ))
    ):
        fail("ArcGIS package portability predeclaration receipt differs or overclaims")

    arcgis_package_evidence = ledger_by_id.get("EVID-0071")
    if (
        not isinstance(arcgis_package_evidence, dict)
        or arcgis_package_evidence.get("status") != arcgis_package_control.get("status")
        or arcgis_package_evidence.get("contract_sha256") != sha256("config/qa/arcgis-package-portability-contract.json")
        or arcgis_package_evidence.get("control_receipt_sha256") != sha256("records/readiness/arcgis-package-portability-control.json")
        or arcgis_package_evidence.get("protocol_sha256") != sha256("docs/ARCGIS_PACKAGE_PORTABILITY_PROTOCOL.md")
        or arcgis_package_evidence.get("source_inventory") != arcgis_package_contract["source_workspace"]["expected_inventory"]
        or arcgis_package_evidence.get("validation", {}).get("portable_test_count") != 7
        or arcgis_package_evidence.get("validation", {}).get("real_package_attempted") is not False
        or any(arcgis_package_evidence.get("assertions", {}).get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "source_workspace_mutated", "satellite_or_dem_pixels_read", "scientific_evidence_created",
            "clean_machine_portability_established", "m6_complete", "current_checkpoint_changed", "authority_created",
        ))
    ):
        fail("EVID-0071 ArcGIS package portability predeclaration differs or overclaims")

    arcgis_package_deviation = json.loads(
        (ROOT / "records/surface-receipts/arcgis-package-portability-postrun-boundary-deviation.json").read_text(encoding="utf-8")
    )
    arcgis_package_result = json.loads(
        (ROOT / "records/surface-receipts/arcgis-package-portability.json").read_text(encoding="utf-8")
    )
    if (
        arcgis_package_deviation.get("status")
        != "fail_retained_unplanned_second_extraction_no_source_or_attempt_mutation"
        or arcgis_package_deviation.get("bindings", {}).get("contract_sha256")
        != sha256("config/qa/arcgis-package-portability-contract.json")
        or arcgis_package_deviation.get("unplanned_output_inventory") != {
            "file_count": 107,
            "total_bytes": 544361,
            "inventory_sha256": "e1b54effd6268740d08e6d349e3d6dd7c142dbd1aeba7b85f2cd5940d99d0672",
            "forbidden_raster_files": [],
            "lock_count": 0,
            "symbolic_link_count": 0,
            "matches_attempt_001_preopen_extraction_inventory": True,
        }
        or arcgis_package_deviation.get("disposition", {}).get("preserve_unplanned_output") is not True
        or arcgis_package_deviation.get("disposition", {}).get("automatic_cleanup_authorized") is not False
        or arcgis_package_deviation.get("disposition", {}).get("attempt_001_runtime_result_invalidated") is not False
        or any(arcgis_package_deviation.get("activity", {}).get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "source_workspace_mutated", "attempt_001_mutated", "satellite_or_dem_pixels_read_or_written",
        ))
    ):
        fail("ArcGIS package post-run boundary deviation differs or is not preserved")
    result_bindings = arcgis_package_result.get("bindings", {})
    result_assertions = arcgis_package_result.get("assertions", {})
    if (
        arcgis_package_result.get("status")
        != "pass_same_machine_round_trip_with_visual_review_and_retained_postrun_boundary_deviation"
        or result_bindings.get("contract_sha256") != sha256("config/qa/arcgis-package-portability-contract.json")
        or result_bindings.get("control_receipt_sha256") != sha256("records/readiness/arcgis-package-portability-control.json")
        or result_bindings.get("source_receipt_sha256") != sha256("records/surface-receipts/arcgis-evidence-workspace.json")
        or result_bindings.get("postrun_boundary_deviation_sha256")
        != sha256("records/surface-receipts/arcgis-package-portability-postrun-boundary-deviation.json")
        or arcgis_package_result.get("publication_gate", {}).get("commit_sha")
        != "b21edbcc93067139b99c389f6d0fc181cf8cd8f8"
        or arcgis_package_result.get("publication_gate", {}).get("github_actions_run_id") != 33908130118
        or arcgis_package_result.get("publication_gate", {}).get("github_actions_conclusion") != "success"
        or arcgis_package_result.get("source_reconciliation", {}).get("unchanged") is not True
        or arcgis_package_result.get("package", {}).get("sha256")
        != "9d469ac98a8fd378baee3f0e22216bd8594f638c70ba7bb217cafc9c5464fa78"
        or arcgis_package_result.get("external_manifest_reconciliation", {}).get("inventory_sha256")
        != "dcb6f21abb6f84814f4e76b9175bbd7355fb6b661b8b27d9c6c7e4c8561fbfac"
        or any(arcgis_package_result.get("external_manifest_reconciliation", {}).get(key) != 0 for key in (
            "missing_file_count", "unexpected_file_count", "changed_file_count", "remaining_lock_count",
            "symbolic_link_count", "forbidden_raster_file_count",
        ))
        or arcgis_package_result.get("extracted_project", {}).get("scientific_record_count") != 0
        or arcgis_package_result.get("round_trip_exports", {}).get("exact_pixel_match") is not True
        or arcgis_package_result.get("visual_inspection", {}).get("status") != "pass"
        or result_assertions.get("same_machine_arcgis_3_7_1_round_trip_established") is not True
        or result_assertions.get("operational_layers_self_contained_in_extraction") is not True
        or any(result_assertions.get(key) is not False for key in (
            "source_workspace_mutated", "network_requests_performed_by_attempt", "authentication_performed_by_attempt",
            "credential_values_read_or_recorded", "scientific_pixels_packaged", "scientific_evidence_created",
            "full_process_conformance_established", "clean_machine_portability_established",
            "cross_version_portability_established", "m6_complete", "current_checkpoint_changed",
            "scientific_admission_authorized",
        ))
    ):
        fail("ArcGIS package portability result differs or overclaims")

    arcgis_package_deviation_evidence = ledger_by_id.get("EVID-0072")
    if (
        not isinstance(arcgis_package_deviation_evidence, dict)
        or arcgis_package_deviation_evidence.get("status") != arcgis_package_deviation.get("status")
        or arcgis_package_deviation_evidence.get("failure_sha256")
        != sha256("records/surface-receipts/arcgis-package-portability-postrun-boundary-deviation.json")
        or arcgis_package_deviation_evidence.get("unplanned_output_inventory", {}).get("inventory_sha256")
        != arcgis_package_deviation["unplanned_output_inventory"]["inventory_sha256"]
        or arcgis_package_deviation_evidence.get("assertions", {}).get("process_conformance_passed") is not False
        or arcgis_package_deviation_evidence.get("assertions", {}).get("automatic_cleanup_authorized") is not False
    ):
        fail("EVID-0072 ArcGIS package boundary deviation differs or is hidden")
    arcgis_package_result_evidence = ledger_by_id.get("EVID-0073")
    if (
        not isinstance(arcgis_package_result_evidence, dict)
        or arcgis_package_result_evidence.get("status") != arcgis_package_result.get("status")
        or arcgis_package_result_evidence.get("result_sha256")
        != sha256("records/surface-receipts/arcgis-package-portability.json")
        or arcgis_package_result_evidence.get("publication_gate", {}).get("github_actions_run_id") != 33908130118
        or arcgis_package_result_evidence.get("validation", {}).get("retained_postrun_boundary_deviation_count") != 1
        or arcgis_package_result_evidence.get("assertions", {}).get("same_machine_arcgis_3_7_1_round_trip_established") is not True
        or any(arcgis_package_result_evidence.get("assertions", {}).get(key) is not False for key in (
            "clean_machine_portability_established", "cross_version_portability_established",
            "scientific_pixels_packaged", "scientific_evidence_created", "full_process_conformance_established",
            "m6_complete", "current_checkpoint_changed", "scientific_admission_authorized",
        ))
    ):
        fail("EVID-0073 ArcGIS package portability result differs or overclaims")

    radar_label_activation_evidence = ledger_by_id.get("EVID-0074")
    if (
        not isinstance(radar_label_activation_evidence, dict)
        or radar_label_activation_evidence.get("status") != "pass_approval_reconciled_synthetic_arcgis_pass_public_ci_pending"
        or radar_label_activation_evidence.get("approval_sha256") != sha256("records/source-gates/m2-radar-input-readiness-amendment-approval.json")
        or radar_label_activation_evidence.get("review_reconciliation_sha256") != sha256("records/source-gates/m2-radar-input-readiness-amendment-review-reconciliation.json")
        or radar_label_activation_evidence.get("amended_contract_sha256") != sha256("config/qa/radar-input-readiness-contract-amendment-001.json")
        or radar_label_activation_evidence.get("synthetic_arcgis_receipt_sha256") != sha256("records/surface-receipts/radar-input-readiness-synthetic-arcgis-amendment-001.json")
        or radar_label_activation_evidence.get("validation", {}).get("focused_amendment_test_count") != 3
        or radar_label_activation_evidence.get("validation", {}).get("full_repository_test_count") != 251
        or radar_label_activation_evidence.get("assertions", {}).get("only_observed_data_semantic_change") != "metadata_checks.pixel_value: AMPLITUDE -> Detected"
        or radar_label_activation_evidence.get("assertions", {}).get("post_observation_correction") is not True
        or any(radar_label_activation_evidence.get("assertions", {}).get(key) is not False for key in (
            "real_002_executed", "network_requests_performed", "external_custody_accessed",
            "real_product_pixel_values_examined", "baseline_processing_released", "scientific_admission_authorized",
        ))
    ):
        fail("EVID-0074 Sentinel-1 label-amendment activation differs or overclaims")

    radar_label_result_evidence = ledger_by_id.get("EVID-0075")
    if (
        not isinstance(radar_label_result_evidence, dict)
        or radar_label_result_evidence.get("status") != radar_label_real_002_reconciliation.get("status")
        or radar_label_result_evidence.get("contract_sha256") != sha256("config/qa/radar-input-readiness-contract-amendment-001.json")
        or radar_label_result_evidence.get("real_receipt_sha256") != sha256("records/readiness/radar-input/m2-s1-input-readiness-real-002.json")
        or radar_label_result_evidence.get("reconciliation_sha256") != sha256("records/surface-receipts/radar-input-readiness-amendment-real-002-reconciliation.json")
        or radar_label_result_evidence.get("publication_gate") != {
            "commit_sha": "c05e1e26c8ee8dd8755573524da90c2080de4bd7",
            "github_actions_run_id": 33910395201,
            "github_actions_conclusion": "success",
        }
        or radar_label_result_evidence.get("observed_result") != {
            "source_count": 3,
            "source_pass_count": 3,
            "source_block_count": 0,
            "required_member_inventory_pass_count": 3,
            "annotation_parse_count": 6,
            "annotation_pixel_value_observed_set": ["Detected"],
            "measurement_header_open_count": 6,
            "all_measurement_headers_one_band_u16": True,
            "blocking_error_count": 0,
        }
        or radar_label_result_evidence.get("external_custody_reverification") != {
            "status": "pass_exact_attempt_inventories_and_all_safe_hashes_unchanged",
            "attempt_count": 3,
            "attempt_file_count": 87,
            "safe_file_count": 78,
            "safe_total_bytes": 5183550209,
            "added_sidecar_count": 0,
        }
        or radar_label_result_evidence.get("disposition", {}).get("real_001_remains_block") is not True
        or radar_label_result_evidence.get("disposition", {}).get("real_002_maximum_invocations_consumed") != 1
        or radar_label_result_evidence.get("disposition", {}).get("automatic_retry_authorized") is not False
        or any(radar_label_result_evidence.get("assertions", {}).get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "real_product_pixel_values_examined", "derived_raster_written", "pixel_usability_established",
            "complete_pair_established", "baseline_processing_released", "change_established",
            "scientific_admission_authorized",
        ))
    ):
        fail("EVID-0075 Sentinel-1 amended real-002 result differs or overclaims")

    sentinel_recovery_failure_evidence = ledger_by_id.get("EVID-0076")
    if (
        not isinstance(sentinel_recovery_failure_evidence, dict)
        or sentinel_recovery_failure_evidence.get("status") != "fail_terminal_interrupted_approved_attempt_consumed_no_retry"
        or sentinel_recovery_failure_evidence.get("approval_sha256") != sha256("records/source-gates/m2-sentinel-recovery-approval.json")
        or sentinel_recovery_failure_evidence.get("publication_gate_sha256") != sha256("records/acquisition/sentinel-recovery-publication-gate.json")
        or sentinel_recovery_failure_evidence.get("activation_sha256") != sha256("records/acquisition/sentinel-recovery-activation.json")
        or sentinel_recovery_failure_evidence.get("recovery_contract_sha256") != sha256("contracts/m2-sentinel-recovery.json")
        or sentinel_recovery_failure_evidence.get("attempt_receipt_sha256") != sha256(recovery_receipt_ref)
        or sentinel_recovery_failure_evidence.get("interruption_reconciliation_sha256") != sha256("records/acquisition/sentinel-recovery-interruption-reconciliation-001.json")
        or sentinel_recovery_failure_evidence.get("attempt", {}).get("attempt_id") != recovery_attempt_id
        or sentinel_recovery_failure_evidence.get("attempt", {}).get("failure_code") != recovery_failure_code
        or sentinel_recovery_failure_evidence.get("attempt", {}).get("failure_cause_established") is not False
        or sentinel_recovery_failure_evidence.get("attempt", {}).get("partial_bytes_preserved") != 1333788672
        or sentinel_recovery_failure_evidence.get("attempt", {}).get("partial_sha256") != recovery_partial_sha256
        or sentinel_recovery_failure_evidence.get("retained_original_failure", {}).get("unchanged") is not True
        or sentinel_recovery_failure_evidence.get("assertions", {}).get("approved_attempt_consumed") is not True
        or sentinel_recovery_failure_evidence.get("assertions", {}).get("automatic_retry_authorized") is not False
        or sentinel_recovery_failure_evidence.get("assertions", {}).get("further_sentinel_transfer_authorized_now") is not False
        or sentinel_recovery_failure_evidence.get("assertions", {}).get("destination_promoted") is not False
        or sentinel_recovery_failure_evidence.get("assertions", {}).get("credential_value_recorded") is not False
        or sentinel_recovery_failure_evidence.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("EVID-0076 Sentinel recovery terminal interruption differs or overclaims")

    sentinel_recovery_002_evidence = ledger_by_id.get("EVID-0077")
    if (
        not isinstance(sentinel_recovery_002_evidence, dict)
        or sentinel_recovery_002_evidence.get("status") != "pass_blank_exact_review_no_authority"
        or sentinel_recovery_002_evidence.get("proposal_sha256") != expected_recovery_002_proposal_sha
        or sentinel_recovery_002_evidence.get("review_bundle_sha256") != expected_recovery_002_bundle_sha
        or sentinel_recovery_002_evidence.get("review_contract_sha256") != sha256("reviews/m2-sentinel-recovery-002/review-contract.json")
        or sentinel_recovery_002_evidence.get("blank_response_sha256") != sha256("reviews/m2-sentinel-recovery-002/blank-response.json")
        or sentinel_recovery_002_evidence.get("review_surface_sha256") != expected_recovery_002_surface_sha
        or sentinel_recovery_002_evidence.get("interruption_reconciliation_sha256") != sha256("records/acquisition/sentinel-recovery-interruption-reconciliation-001.json")
        or sentinel_recovery_002_evidence.get("assertions", {}).get("retained_partial_count") != 2
        or sentinel_recovery_002_evidence.get("assertions", {}).get("prior_approved_attempt_consumed") is not True
        or sentinel_recovery_002_evidence.get("assertions", {}).get("human_decision_count") != 0
        or sentinel_recovery_002_evidence.get("assertions", {}).get("implementation_authorized") is not False
        or sentinel_recovery_002_evidence.get("assertions", {}).get("credential_access_authorized") is not False
        or sentinel_recovery_002_evidence.get("assertions", {}).get("recovery_002_transfer_authorized") is not False
        or sentinel_recovery_002_evidence.get("assertions", {}).get("automatic_retry_authorized") is not False
        or sentinel_recovery_002_evidence.get("assertions", {}).get("pixel_usability_established") is not False
        or sentinel_recovery_002_evidence.get("assertions", {}).get("scientific_result_established") is not False
    ):
        fail("EVID-0077 Sentinel recovery-002 review readiness differs or overclaims")

    sentinel_recovery_002_approval_evidence = ledger_by_id.get("EVID-0080")
    if (
        not isinstance(sentinel_recovery_002_approval_evidence, dict)
        or sentinel_recovery_002_approval_evidence.get("status") != "approved_implementation_only_pending_publication_gate"
        or sentinel_recovery_002_approval_evidence.get("approval_sha256") != sha256("records/source-gates/m2-sentinel-recovery-002-approval.json")
        or sentinel_recovery_002_approval_evidence.get("review_reconciliation_sha256") != sha256("records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json")
        or sentinel_recovery_002_approval_evidence.get("proposal_sha256") != expected_recovery_002_proposal_sha
        or sentinel_recovery_002_approval_evidence.get("review_bundle_sha256") != expected_recovery_002_bundle_sha
        or sentinel_recovery_002_approval_evidence.get("assertions", {}).get("human_decision_count") != 1
        or sentinel_recovery_002_approval_evidence.get("assertions", {}).get("implementation_authorized") is not True
        or sentinel_recovery_002_approval_evidence.get("assertions", {}).get("real_recovery_started") is not False
        or sentinel_recovery_002_approval_evidence.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or sentinel_recovery_002_approval_evidence.get("assertions", {}).get("pixel_processing_released") is not False
        or sentinel_recovery_002_approval_evidence.get("assertions", {}).get("automatic_retry_authorized") is not False
    ):
        fail("EVID-0080 recovery-002 approval custody differs or overclaims")
    expected_recovery_002_implementation_bindings = {
        key: sha256(str(path.relative_to(ROOT)).replace("\\", "/"))
        for key, path in RECOVERY_002_IMPLEMENTATION_FILES.items()
    }
    if (
        sentinel_recovery_002_readiness.get("status") != "pass_local_synthetic_ready_public_ci_pending"
        or sentinel_recovery_002_readiness.get("bindings") != expected_recovery_002_implementation_bindings
        or sentinel_recovery_002_readiness.get("tests", {}).get("focused_test_count") != 12
        or sentinel_recovery_002_readiness.get("tests", {}).get("full_repository_test_count") != 293
        or sentinel_recovery_002_readiness.get("tests", {}).get("focused_result") != "pass"
        or sentinel_recovery_002_readiness.get("tests", {}).get("full_repository_result") != "pass"
        or sentinel_recovery_002_readiness.get("assertions", {}).get("real_credential_read") is not False
        or sentinel_recovery_002_readiness.get("assertions", {}).get("network_requests_performed") is not False
        or sentinel_recovery_002_readiness.get("assertions", {}).get("external_data_mutated") is not False
        or sentinel_recovery_002_readiness.get("assertions", {}).get("real_recovery_started") is not False
    ):
        fail("recovery-002 implementation readiness receipt differs or overclaims")
    sentinel_recovery_002_publication_failure = ledger_by_id.get("EVID-0081")
    if (
        not isinstance(sentinel_recovery_002_publication_failure, dict)
        or sentinel_recovery_002_publication_failure.get("status") != "fail_public_ci_no_gate_no_activation"
        or sentinel_recovery_002_publication_failure.get("failure_receipt_sha256") != sha256("records/acquisition/sentinel-recovery-002-publication-attempt-001-failure.json")
        or sentinel_recovery_002_publication_failure.get("implementation_commit") != "7e772f6c45d2a24490e080fa4dfc2a92a4ca1bcb"
        or sentinel_recovery_002_publication_failure.get("github_actions_run_id") != 33921807360
        or sentinel_recovery_002_publication_failure.get("github_actions_conclusion") != "failure"
        or any(sentinel_recovery_002_publication_failure.get("assertions", {}).get(key) is not False for key in (
            "publication_gate_created", "activation_performed", "credential_values_read_or_recorded",
            "product_payload_requested", "external_data_mutated", "data_transfer_retry_performed",
        ))
    ):
        fail("EVID-0081 recovery-002 failed publication attempt differs or overclaims")

    final_delivery_contract = json.loads(
        (ROOT / "config/qa/arcgis-final-delivery-contract.json").read_text(encoding="utf-8")
    )
    final_delivery_readiness = json.loads(
        (ROOT / "records/readiness/m6-arcgis-final-delivery-control-readiness.json").read_text(encoding="utf-8")
    )
    final_delivery_errors = validate_arcgis_final_delivery_contract(final_delivery_contract)
    if final_delivery_errors:
        fail("ArcGIS final delivery contract differs: " + "; ".join(final_delivery_errors))
    expected_final_delivery_bindings = {
        "contract_ref": "config/qa/arcgis-final-delivery-contract.json",
        "contract_sha256": "a3eda86374e77e4c8dbc48ff7a37b0f3766119878a65b95ff137477ba497527d",
        "portable_core_ref": "scripts/arcgis_final_delivery_core.py",
        "portable_core_sha256": "c11a99929dedcd9b086d037b28b6c7980ba47d713dff4e890a741931600ac866",
        "tests_ref": "tests/test_arcgis_final_delivery.py",
        "tests_sha256": "f916d73811074005ba0eae313e0b59dd1e7a05ce0b351f9982a80b6ce3b1ad26",
        "protocol_ref": "docs/ARCGIS_FINAL_DELIVERY_ACCEPTANCE.md",
        "protocol_sha256": "7a51460f74dceb3113acd3102de8e529f14c18376c8bd643b3556417f737575a",
    }
    if (
        final_delivery_readiness.get("status") != "pass_synthetic_control_only_m6_not_executed"
        or final_delivery_readiness.get("bindings") != expected_final_delivery_bindings
        or final_delivery_readiness.get("validation", {}).get("focused_test_count") != 8
        or final_delivery_readiness.get("validation", {}).get("focused_test_status") != "pass"
        or any(final_delivery_readiness.get("assertions", {}).get(key) is not False for key in (
            "external_data_read", "arcgis_runtime_invoked", "scientific_pixels_read_or_written",
            "scientific_evidence_admitted", "final_maps_created", "clean_environment_test_performed",
            "m6_complete", "public_release_authorized", "emergency_guidance_authorized",
            "current_checkpoint_changed",
        ))
    ):
        fail("ArcGIS final delivery readiness differs or overclaims")
    for binding in final_delivery_contract.get("authoritative_inputs", {}).values():
        if binding.get("sha256") != sha256(binding.get("ref", "")):
            fail("ArcGIS final delivery authoritative input binding is stale")
    if expected_final_delivery_bindings["contract_sha256"] != sha256(expected_final_delivery_bindings["contract_ref"]):
        fail("ArcGIS final delivery contract hash differs")
    if expected_final_delivery_bindings["portable_core_sha256"] != sha256(expected_final_delivery_bindings["portable_core_ref"]):
        fail("ArcGIS final delivery core hash differs")
    if expected_final_delivery_bindings["tests_sha256"] != sha256(expected_final_delivery_bindings["tests_ref"]):
        fail("ArcGIS final delivery tests hash differs")
    if expected_final_delivery_bindings["protocol_sha256"] != sha256(expected_final_delivery_bindings["protocol_ref"]):
        fail("ArcGIS final delivery protocol hash differs")

    final_delivery_evidence = ledger_by_id.get("EVID-0078")
    if (
        not isinstance(final_delivery_evidence, dict)
        or final_delivery_evidence.get("status") != "pass_synthetic_control_only_m6_not_executed"
        or final_delivery_evidence.get("contract_sha256") != sha256("config/qa/arcgis-final-delivery-contract.json")
        or final_delivery_evidence.get("portable_core_sha256") != sha256("scripts/arcgis_final_delivery_core.py")
        or final_delivery_evidence.get("tests_sha256") != sha256("tests/test_arcgis_final_delivery.py")
        or final_delivery_evidence.get("readiness_sha256") != sha256("records/readiness/m6-arcgis-final-delivery-control-readiness.json")
        or final_delivery_evidence.get("assertions", {}).get("focused_test_count") != 8
        or any(final_delivery_evidence.get("assertions", {}).get(key) is not False for key in (
            "external_data_read", "arcgis_runtime_invoked", "scientific_pixels_read_or_written",
            "final_maps_created", "clean_environment_test_performed", "m6_complete",
            "public_release_authorized", "current_checkpoint_changed",
        ))
    ):
        fail("EVID-0078 ArcGIS final delivery control readiness differs or overclaims")

    change_evidence_contract = json.loads(
        (ROOT / "config/qa/change-evidence-contract.json").read_text(encoding="utf-8")
    )
    change_evidence_readiness = json.loads(
        (ROOT / "records/readiness/m4-change-evidence-control-readiness.json").read_text(encoding="utf-8")
    )
    change_evidence_errors = validate_change_evidence_contract(change_evidence_contract)
    if change_evidence_errors:
        fail("M4 change-evidence contract differs: " + "; ".join(change_evidence_errors))
    expected_change_evidence_bindings = {
        "contract_ref": "config/qa/change-evidence-contract.json",
        "contract_sha256": "fc2d18fa758d25b212361110ec9dba2611ba447611a2f7a284f5d1859b0ad33e",
        "portable_core_ref": "scripts/change_evidence_core.py",
        "portable_core_sha256": "0b9660a8f8717d3190473de72e6c566b320ff086d208140faf2ed61a8fa25903",
        "tests_ref": "tests/test_change_evidence_core.py",
        "tests_sha256": "aad916113d5d77c44e974af6c4816901f68af4e1ab063b17794e47d523ef67e4",
        "protocol_ref": "docs/CHANGE_EVIDENCE_PROTOCOL.md",
        "protocol_sha256": "62c3d0462d8b84dfe0fb14f19e17c21d76323e495ae24186c2514f465b5f3c13",
    }
    if (
        change_evidence_readiness.get("status") != "pass_synthetic_control_only_no_real_change_processing"
        or change_evidence_readiness.get("bindings") != expected_change_evidence_bindings
        or change_evidence_readiness.get("validation", {}).get("focused_test_count") != 12
        or change_evidence_readiness.get("validation", {}).get("focused_test_status") != "pass"
        or any(change_evidence_readiness.get("assertions", {}).get(key) is not False for key in (
            "external_data_read", "arcgis_runtime_invoked", "satellite_pixels_read_or_written",
            "real_route_evaluated", "candidate_change_created", "interpretation_created",
            "attribution_created", "scientific_admission_authorized",
            "threshold_change_after_observation_authorized", "publication_authorized",
            "current_checkpoint_changed",
        ))
    ):
        fail("M4 change-evidence control readiness differs or overclaims")
    for binding in change_evidence_contract.get("bindings", {}).values():
        if binding.get("sha256") != sha256(binding.get("ref", "")):
            fail("M4 change-evidence source binding is stale")
    for ref_key, sha_key in (
        ("contract_ref", "contract_sha256"), ("portable_core_ref", "portable_core_sha256"),
        ("tests_ref", "tests_sha256"), ("protocol_ref", "protocol_sha256"),
    ):
        if expected_change_evidence_bindings[sha_key] != sha256(expected_change_evidence_bindings[ref_key]):
            fail(f"M4 change-evidence {sha_key} differs")

    change_evidence_ledger = ledger_by_id.get("EVID-0079")
    if (
        not isinstance(change_evidence_ledger, dict)
        or change_evidence_ledger.get("status") != "pass_synthetic_control_only_no_real_change_processing"
        or change_evidence_ledger.get("contract_sha256") != sha256("config/qa/change-evidence-contract.json")
        or change_evidence_ledger.get("portable_core_sha256") != sha256("scripts/change_evidence_core.py")
        or change_evidence_ledger.get("tests_sha256") != sha256("tests/test_change_evidence_core.py")
        or change_evidence_ledger.get("readiness_sha256") != sha256("records/readiness/m4-change-evidence-control-readiness.json")
        or change_evidence_ledger.get("assertions", {}).get("focused_test_count") != 12
        or any(change_evidence_ledger.get("assertions", {}).get(key) is not False for key in (
            "external_data_read", "arcgis_runtime_invoked", "satellite_pixels_read_or_written",
            "real_route_evaluated", "candidate_change_created", "interpretation_created",
            "attribution_created", "scientific_admission_authorized",
            "threshold_change_after_observation_authorized", "publication_authorized",
            "current_checkpoint_changed",
        ))
    ):
        fail("EVID-0079 M4 change-evidence readiness differs or overclaims")

    recovery_002_outcome = json.loads(
        (ROOT / "records/acquisition/sentinel-recovery-002-supervisor-reconciliation-001.json").read_text(encoding="utf-8")
    )
    if (
        recovery_002_outcome.get("status") != "recovery_and_container_pass_continuation_stopped_before_attempt_cause_unknown"
        or recovery_002_outcome.get("recovery", {}).get("transfer_receipt_sha256") != sha256("records/acquisition/recovery-attempts/m1-src-004-recovery-002-20260905t002925z-cc1fe1e9.json")
        or recovery_002_outcome.get("recovery", {}).get("container_receipt_sha256") != sha256("records/acquisition/container-verification/m1-src-004-m1-src-004-recovery-002-20260905t002925z-cc1fe1e9.json")
        or recovery_002_outcome.get("recovery", {}).get("destination_size_bytes") != 1732332897
        or recovery_002_outcome.get("recovery", {}).get("destination_sha256") != "a606cac063cc23e60a623f020192fc097d327f3dafadf1115802b2a458eaceab"
        or recovery_002_outcome.get("supervisor", {}).get("terminal_phase") != "continuation_live_preflight"
        or recovery_002_outcome.get("supervisor", {}).get("terminal_code") != "unexpected_supervisor_failure"
        or recovery_002_outcome.get("supervisor", {}).get("exact_cause_established") is not False
        or recovery_002_outcome.get("continuation_boundary", {}).get("attempt_count") != 0
        or recovery_002_outcome.get("continuation_boundary", {}).get("payload_request_count") != 0
        or recovery_002_outcome.get("continuation_boundary", {}).get("automatic_retry_authorized") is not False
        or recovery_002_outcome.get("assertions", {}).get("credential_value_recorded") is not False
        or recovery_002_outcome.get("assertions", {}).get("pixel_usability_established") is not False
        or recovery_002_outcome.get("assertions", {}).get("scientific_fitness_established") is not False
    ):
        fail("M2 recovery-002 outcome reconciliation differs or overclaims")

    current_by_source = {
        item.get("extensions", {}).get("source_id"): item
        for item in active_intake.get("assets", [])
        if isinstance(item, dict)
    }
    recovered = current_by_source.get("M1-SRC-004", {})
    continuation_source_ids = ("M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010")
    if (
        recovered.get("state") != "promoted"
        or recovered.get("extensions", {}).get("satisfied_by_recovery_002") is not True
        or recovered.get("observed", {}).get("promoted_sha256") != "a606cac063cc23e60a623f020192fc097d327f3dafadf1115802b2a458eaceab"
        or [current_by_source.get(source_id, {}).get("state") for source_id in continuation_source_ids] != ["promoted"] * 4
    ):
        fail("active Sentinel intake does not preserve the reconciled eight-promoted state")

    continuation_proposal_ref = "contracts/milestone-002-sentinel-continuation-001-proposal.json"
    continuation_bundle_ref = "reviews/m2-sentinel-continuation-001/review-bundle.json"
    continuation_contract_ref = "reviews/m2-sentinel-continuation-001/review-contract.json"
    continuation_blank_ref = "reviews/m2-sentinel-continuation-001/blank-response.json"
    continuation_proposal_sha = "d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1"
    continuation_bundle_sha = "382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b"
    if sha256(continuation_proposal_ref) != continuation_proposal_sha or sha256(continuation_bundle_ref) != continuation_bundle_sha:
        fail("M2 continuation-001 proposal or review-bundle identity differs")
    continuation_contract = json.loads((ROOT / continuation_contract_ref).read_text(encoding="utf-8"))
    continuation_blank = json.loads((ROOT / continuation_blank_ref).read_text(encoding="utf-8"))
    if (
        continuation_contract.get("review_bundle", {}).get("manifest_sha256") != continuation_bundle_sha
        or continuation_contract.get("items") != [{"item_id": "M2-SENTINEL-CONTINUATION-001", "evidence_sha256": continuation_bundle_sha}]
        or continuation_blank.get("completed") is not False
        or continuation_blank.get("reviewer", {}).get("attestation") is not False
        or continuation_blank.get("responses") != [{"item_id": "M2-SENTINEL-CONTINUATION-001", "evidence_sha256": continuation_bundle_sha, "decision": None, "notes": ""}]
    ):
        fail("M2 continuation-001 review contract or blank response differs")

    continuation_approval_ref = "records/source-gates/m2-sentinel-continuation-001-approval.json"
    continuation_reconciliation_ref = "records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json"
    continuation_readiness_ref = "records/acquisition/sentinel-continuation-001-implementation-readiness.json"
    continuation_first_superseded_readiness_ref = "records/acquisition/sentinel-continuation-001-implementation-readiness-attempt-001-superseded.json"
    continuation_superseded_readiness_ref = "records/acquisition/sentinel-continuation-001-implementation-readiness-attempt-002-superseded.json"
    continuation_publication_failure_ref = "records/acquisition/sentinel-continuation-001-implementation-publication-attempt-001-failure.json"
    continuation_approval_sha = "93f451f458c5b4984f980049f5adadf73e52663c8a71ee9699939b7f85e727a1"
    continuation_reconciliation_sha = "420f525d160a1b95f6784da06a0ca95ddf8e6e8e37d7947925f6c865157d28a6"
    continuation_readiness_sha = "35bb375543dc2add5e66e80019ee7bc4eb70cee2f2cc3a4c8cf542c97369919a"
    continuation_first_superseded_readiness_sha = "86af300807b6db28e97deb6b8188d609f02bf0bed3044741e1eb124eddc28c48"
    continuation_superseded_readiness_sha = "f52d989352541a1fb28dacf858fd14408de28bde84fcb9355154ea623df48fad"
    continuation_publication_failure_sha = "17035284194fad3645f95d2162a6ff639f6743e2d849c67fce4e3505340cc2f0"
    if (
        sha256(continuation_approval_ref) != continuation_approval_sha
        or sha256(continuation_reconciliation_ref) != continuation_reconciliation_sha
        or sha256(continuation_readiness_ref) != continuation_readiness_sha
        or sha256(continuation_first_superseded_readiness_ref) != continuation_first_superseded_readiness_sha
        or sha256(continuation_superseded_readiness_ref) != continuation_superseded_readiness_sha
        or sha256(continuation_publication_failure_ref) != continuation_publication_failure_sha
    ):
        fail("M2 continuation-001 approval, reconciliation, or readiness identity differs")
    continuation_approval = json.loads((ROOT / continuation_approval_ref).read_text(encoding="utf-8"))
    continuation_reconciliation = json.loads((ROOT / continuation_reconciliation_ref).read_text(encoding="utf-8"))
    continuation_readiness = json.loads((ROOT / continuation_readiness_ref).read_text(encoding="utf-8"))
    continuation_publication_failure = json.loads((ROOT / continuation_publication_failure_ref).read_text(encoding="utf-8"))
    if (
        continuation_approval.get("status") != "approved_exact_bounded_continuation_only"
        or continuation_approval.get("review_bundle_manifest_sha256") != continuation_bundle_sha
        or continuation_approval.get("continuation_proposal_sha256") != continuation_proposal_sha
        or continuation_approval.get("review_reconciliation_sha256") != continuation_reconciliation_sha
        or continuation_approval.get("locked_response_sha256") != "add004d26f7a35ed1b657089dae1c1f68f01eba495c0c4edb35cee943a13cb39"
        or continuation_approval.get("human_decision_count") != 1
        or continuation_approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or continuation_approval.get("source_ids_in_exact_order") != ["M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010"]
        or continuation_approval.get("maximum_real_attempts_per_source") != 1
        or continuation_approval.get("stop_on_first_failure") is not True
        or continuation_approval.get("human_decisions_fabricated") is not False
        or continuation_reconciliation.get("status") != "reconciled_exact_human_response"
        or continuation_reconciliation.get("response_sha256") != "add004d26f7a35ed1b657089dae1c1f68f01eba495c0c4edb35cee943a13cb39"
        or continuation_reconciliation.get("human_decision_count") != 1
        or continuation_reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or continuation_reconciliation.get("notes_included") is not False
        or continuation_reconciliation.get("human_decisions_fabricated") is not False
    ):
        fail("M2 continuation-001 exact owner decision custody differs")
    # Once the approved continuation has completed, the fixed-hash readiness receipt
    # remains a historical snapshot. Current-state test and contract files may then
    # change only through the separately reconciled post-success control update.
    expected_continuation_bindings = (
        continuation_readiness.get("bindings", {})
        if continuation_completed
        else {
            key: sha256(path.relative_to(ROOT).as_posix())
            for key, path in CONTINUATION_001_IMPLEMENTATION_FILES.items()
        }
    )
    continuation_assertions = continuation_readiness.get("assertions", {})
    if (
        continuation_readiness.get("receipt_id") != "NEPAL-M2-SENTINEL-CONTINUATION-001-IMPLEMENTATION-READINESS-003"
        or continuation_readiness.get("status") != "pass_local_synthetic_ready_public_ci_pending"
        or continuation_readiness.get("supersedes", {}).get("sha256") != continuation_superseded_readiness_sha
        or continuation_readiness.get("bindings") != expected_continuation_bindings
        or continuation_readiness.get("tests", {}).get("focused_test_count") != 23
        or continuation_readiness.get("tests", {}).get("full_repository_test_count") != 317
        or continuation_readiness.get("tests", {}).get("windows_detached_process_tested") is not True
        or continuation_assertions.get("network_requests_performed") is not False
        or continuation_assertions.get("authentication_performed") is not False
        or continuation_assertions.get("credential_values_read_or_recorded") is not False
        or continuation_assertions.get("external_product_bytes_mutated") is not False
        or continuation_assertions.get("product_payload_requested") is not False
        or continuation_assertions.get("real_continuation_attempt_started") is not False
        or continuation_assertions.get("m1_src_004_requested") is not False
        or continuation_assertions.get("automatic_retry_authorized") is not False
        or continuation_assertions.get("pixel_processing_released") is not False
    ):
        fail("M2 continuation-001 local implementation readiness differs")
    if (
        continuation_publication_failure.get("status") != "failed_preserved"
        or continuation_publication_failure.get("commit_sha") != "114cb663dbaf13bd286d26f92167ea4a9b7ec420"
        or continuation_publication_failure.get("workflow", {}).get("run_id") != 33942595168
        or continuation_publication_failure.get("workflow", {}).get("conclusion") != "failure"
        or continuation_publication_failure.get("finding", {}).get("classification") != "synthetic_test_external_root_portability_defect"
        or continuation_publication_failure.get("finding", {}).get("production_control_failure_established") is not False
        or continuation_publication_failure.get("preservation", {}).get("implementation_readiness_sha256") != continuation_superseded_readiness_sha
        or continuation_publication_failure.get("preservation", {}).get("automatic_retry_performed") is not False
        or continuation_publication_failure.get("preservation", {}).get("token_requested") is not False
        or continuation_publication_failure.get("preservation", {}).get("credential_values_read_or_recorded") is not False
        or continuation_publication_failure.get("preservation", {}).get("payload_requested") is not False
        or continuation_publication_failure.get("preservation", {}).get("external_product_bytes_mutated") is not False
    ):
        fail("M2 continuation-001 failed implementation publication evidence differs")

    continuation_success_assertions = continuation_success.get("assertions", {})
    continuation_postsuccess_bindings = continuation_postsuccess.get("bindings", {})
    continuation_postsuccess_assertions = continuation_postsuccess.get("assertions", {})
    if (
        continuation_success.get("status") != "reconciled_all_eight_promoted_container_pass"
        or continuation_success_assertions.get("promoted_container_verified_source_count") != 8
        or continuation_success_assertions.get("continuation_source_order") != list(continuation_source_ids)
        or continuation_success_assertions.get("m1_src_004_requested_by_continuation") is not False
        or continuation_success_assertions.get("automatic_retry_performed") is not False
        or continuation_success_assertions.get("credential_values_read_or_recorded") is not False
        or continuation_success_assertions.get("archive_extraction_performed") is not False
        or continuation_success_assertions.get("pixel_usability_established") is not False
        or continuation_success_assertions.get("scientific_fitness_established") is not False
    ):
        fail("M2 continuation-001 success reconciliation differs or overclaims")
    if (
        continuation_postsuccess_failure.get("status") != "failed_preserved_control_state_lag"
        or continuation_postsuccess_failure.get("acquisition_outcome_affected") is not False
        or continuation_postsuccess_failure.get("classification") != "post_success_control_and_test_state_lag"
        or len(continuation_postsuccess_failure.get("observed_failures", [])) != 3
        or any(item.get("exit_code") != 1 for item in continuation_postsuccess_failure.get("observed_failures", []))
        or continuation_postsuccess_failure.get("credential_values_read_or_recorded") is not False
        or continuation_postsuccess_failure.get("product_bytes_mutated") is not False
        or continuation_postsuccess_failure.get("pixel_processing_performed") is not False
        or continuation_postsuccess_failure.get("failure_preserved") is not True
    ):
        fail("M2 continuation-001 preserved post-success validation failure differs")
    if (
        continuation_postsuccess_failure_002.get("status") != "failed_preserved_stale_cross_workstream_assertions"
        or continuation_postsuccess_failure_002.get("acquisition_outcome_affected") is not False
        or continuation_postsuccess_failure_002.get("repository_checker_status") != "pass_448_required_files"
        or continuation_postsuccess_failure_002.get("test_run") != {
            "tests_run": 319,
            "failures": 2,
            "errors": 0,
            "skipped": 2,
        }
        or len(continuation_postsuccess_failure_002.get("observed_failures", [])) != 2
        or continuation_postsuccess_failure_002.get("classification") != "post_success_cross_workstream_test_state_lag"
        or continuation_postsuccess_failure_002.get("credential_values_read_or_recorded") is not False
        or continuation_postsuccess_failure_002.get("network_requests_performed") is not False
        or continuation_postsuccess_failure_002.get("product_bytes_mutated") is not False
        or continuation_postsuccess_failure_002.get("pixel_processing_performed") is not False
        or continuation_postsuccess_failure_002.get("failure_preserved") is not True
    ):
        fail("M2 continuation-001 preserved second post-success validation failure differs")
    if (
        continuation_postsuccess.get("status") != "reconciled_eight_promoted_container_verified_transfer_cohort_complete"
        or continuation_postsuccess_bindings.get("success_reconciliation_sha256") != sha256("records/acquisition/sentinel-continuation-001-success-reconciliation.json")
        or continuation_postsuccess_bindings.get("postsuccess_validation_failure_sha256") != sha256("records/acquisition/sentinel-continuation-001-postsuccess-validation-attempt-001-failure.json")
        or continuation_postsuccess_bindings.get("active_intake_sha256_after_status_reconciliation") != sha256("contracts/m2-intake.json")
        or continuation_postsuccess_bindings.get("terminal_supervisor_id") != "m2-sentinel-continuation-001-20260905t041158z-ca2f8e75"
        or continuation_postsuccess_bindings.get("terminal_event_sha256") != "375be1e2c97e96504ecdc074cda2d66adaea58e05d7f8dc5b933e72a580707e9"
        or continuation_postsuccess_assertions.get("promoted_source_count") != 8
        or continuation_postsuccess_assertions.get("container_pass_source_count") != 8
        or continuation_postsuccess_assertions.get("continuation_source_order") != list(continuation_source_ids)
        or continuation_postsuccess_assertions.get("continuation_attempt_count") != 4
        or continuation_postsuccess_assertions.get("automatic_retry_performed") is not False
        or continuation_postsuccess_assertions.get("m1_src_004_requested_by_continuation") is not False
        or continuation_postsuccess_assertions.get("credential_values_read_or_recorded") is not False
        or continuation_postsuccess_assertions.get("archive_extraction_performed_by_continuation") is not False
        or continuation_postsuccess_assertions.get("materialization_source_count") != 3
        or continuation_postsuccess_assertions.get("pixel_usability_established") is not False
        or continuation_postsuccess_assertions.get("scientific_fitness_established") is not False
    ):
        fail("M2 continuation-001 post-success reconciliation differs or overclaims")
    postsuccess_sources = continuation_postsuccess_bindings.get("sources", {})
    success_sources = continuation_success.get("bindings", {}).get("sources", {})
    if set(postsuccess_sources) != set(current_by_source) or set(success_sources) != set(current_by_source):
        fail("M2 continuation-001 reconciliations do not bind the exact eight active sources")
    for source_id, asset in current_by_source.items():
        postsuccess_source = postsuccess_sources.get(source_id, {})
        success_source = success_sources.get(source_id, {})
        observed = asset.get("observed", {})
        if (
            asset.get("state") != "promoted"
            or postsuccess_source.get("attempt_id") != success_source.get("attempt_id")
            or postsuccess_source.get("container_receipt_ref") != success_source.get("container_receipt_ref")
            or postsuccess_source.get("container_receipt_sha256") != success_source.get("container_receipt_sha256")
            or postsuccess_source.get("promoted_size_bytes") != observed.get("promoted_size_bytes")
            or postsuccess_source.get("promoted_sha256") != observed.get("promoted_sha256")
            or sha256(postsuccess_source.get("attempt_receipt_ref")) != postsuccess_source.get("attempt_receipt_sha256")
            or sha256(postsuccess_source.get("container_receipt_ref")) != postsuccess_source.get("container_receipt_sha256")
        ):
            fail(f"M2 continuation-001 source reconciliation differs for {source_id}")
    retained_failures = continuation_postsuccess.get("retained_failures", [])
    if (
        [(item.get("label"), item.get("size_bytes"), item.get("sha256")) for item in retained_failures]
        != [
            ("original_partial", 561593598, "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"),
            ("recovery_001_partial", 1333788672, "c2d3a878f98615ddaa5e0bf21df5eb5f65c591719cb26b5f43b361aa4eac4cac"),
        ]
        or any(item.get("classification") != "retained_failed_partial_not_a_valid_product" for item in retained_failures)
    ):
        fail("M2 continuation-001 retained failed partial evidence differs")
    continuation_broker_text = (ROOT / "scripts/m2_sentinel_continuation_001_broker.py").read_text(encoding="utf-8")
    continuation_supervisor_text = (ROOT / "scripts/m2_sentinel_continuation_001_supervisor.py").read_text(encoding="utf-8")
    if (
        "run_recovery" in continuation_broker_text
        or "run_recovery" in continuation_supervisor_text
        or '"--token"' in continuation_broker_text
        or '"--token"' in continuation_supervisor_text
        or "CDSE_TOKEN" in continuation_broker_text
        or "CDSE_TOKEN" in continuation_supervisor_text
    ):
        fail("M2 continuation-001 implementation exposes a recovery or credential shortcut")

    recovery_outcome_evidence = ledger_by_id.get("EVID-0082")
    continuation_review_evidence = ledger_by_id.get("EVID-0084")
    continuation_approval_evidence = ledger_by_id.get("EVID-0085")
    continuation_readiness_evidence = ledger_by_id.get("EVID-0086")
    continuation_publication_failure_evidence = ledger_by_id.get("EVID-0087")
    continuation_portability_correction_evidence = ledger_by_id.get("EVID-0088")
    if (
        not isinstance(recovery_outcome_evidence, dict)
        or recovery_outcome_evidence.get("reconciliation_sha256") != sha256("records/acquisition/sentinel-recovery-002-supervisor-reconciliation-001.json")
        or recovery_outcome_evidence.get("result", {}).get("container_status") != "pass_container_only"
        or recovery_outcome_evidence.get("result", {}).get("exact_failure_cause_established") is not False
        or recovery_outcome_evidence.get("assertions", {}).get("continuation_attempt_count") != 0
        or recovery_outcome_evidence.get("assertions", {}).get("continuation_payload_request_count") != 0
        or recovery_outcome_evidence.get("assertions", {}).get("automatic_retry_authorized") is not False
    ):
        fail("EVID-0082 recovery-002 outcome differs")
    if (
        not isinstance(continuation_review_evidence, dict)
        or continuation_review_evidence.get("proposal_sha256") != continuation_proposal_sha
        or continuation_review_evidence.get("review_bundle_sha256") != continuation_bundle_sha
        or continuation_review_evidence.get("review_contract_sha256") != sha256(continuation_contract_ref)
        or continuation_review_evidence.get("blank_response_sha256") != sha256(continuation_blank_ref)
        or continuation_review_evidence.get("assertions", {}).get("human_decision_count") != 0
        or continuation_review_evidence.get("assertions", {}).get("continuation_transfer_authorized") is not False
        or continuation_review_evidence.get("assertions", {}).get("m1_src_004_transfer_authorized") is not False
    ):
        fail("EVID-0084 corrected continuation-001 review readiness differs or invents authority")
    if (
        not isinstance(continuation_approval_evidence, dict)
        or continuation_approval_evidence.get("proposal_sha256") != continuation_proposal_sha
        or continuation_approval_evidence.get("review_bundle_sha256") != continuation_bundle_sha
        or continuation_approval_evidence.get("approval_sha256") != continuation_approval_sha
        or continuation_approval_evidence.get("review_reconciliation_sha256") != continuation_reconciliation_sha
        or continuation_approval_evidence.get("locked_response_sha256") != "add004d26f7a35ed1b657089dae1c1f68f01eba495c0c4edb35cee943a13cb39"
        or continuation_approval_evidence.get("assertions", {}).get("human_decision_count") != 1
        or continuation_approval_evidence.get("assertions", {}).get("attestation") is not True
        or continuation_approval_evidence.get("assertions", {}).get("continuation_implementation_authorized") is not True
        or continuation_approval_evidence.get("assertions", {}).get("credential_access_authorized_before_public_ci_and_final_preflight") is not False
        or continuation_approval_evidence.get("assertions", {}).get("continuation_transfer_authorized_now") is not False
        or continuation_approval_evidence.get("assertions", {}).get("m1_src_004_transfer_authorized") is not False
        or continuation_approval_evidence.get("assertions", {}).get("automatic_retry_authorized") is not False
        or continuation_approval_evidence.get("assertions", {}).get("pixel_processing_released") is not False
    ):
        fail("EVID-0085 continuation-001 owner approval custody differs")
    if (
        not isinstance(continuation_readiness_evidence, dict)
        or continuation_readiness_evidence.get("readiness_sha256") != continuation_superseded_readiness_sha
        or continuation_readiness_evidence.get("superseded_readiness_sha256") != continuation_first_superseded_readiness_sha
        or continuation_readiness_evidence.get("assertions", {}).get("focused_test_count") != 23
        or continuation_readiness_evidence.get("assertions", {}).get("full_repository_test_count") != 317
        or continuation_readiness_evidence.get("assertions", {}).get("public_ci_passed") is True
        or continuation_readiness_evidence.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or continuation_readiness_evidence.get("assertions", {}).get("product_payload_requested") is not False
        or continuation_readiness_evidence.get("assertions", {}).get("m1_src_004_requested") is not False
        or continuation_readiness_evidence.get("assertions", {}).get("pixel_processing_released") is not False
    ):
        fail("EVID-0086 continuation-001 implementation readiness differs")
    if (
        not isinstance(continuation_publication_failure_evidence, dict)
        or continuation_publication_failure_evidence.get("failure_record_sha256") != continuation_publication_failure_sha
        or continuation_publication_failure_evidence.get("commit_sha") != "114cb663dbaf13bd286d26f92167ea4a9b7ec420"
        or continuation_publication_failure_evidence.get("public_ci_run_id") != 33942595168
        or continuation_publication_failure_evidence.get("assertions", {}).get("repository_validation_passed") is not True
        or continuation_publication_failure_evidence.get("assertions", {}).get("full_public_ci_passed") is not False
        or continuation_publication_failure_evidence.get("assertions", {}).get("activation_performed") is not False
        or continuation_publication_failure_evidence.get("assertions", {}).get("token_requested") is not False
        or continuation_publication_failure_evidence.get("assertions", {}).get("product_payload_requested") is not False
        or continuation_publication_failure_evidence.get("assertions", {}).get("external_product_bytes_mutated") is not False
    ):
        fail("EVID-0087 continuation-001 failed public run differs")
    if (
        not isinstance(continuation_portability_correction_evidence, dict)
        or continuation_portability_correction_evidence.get("readiness_sha256") != continuation_readiness_sha
        or continuation_portability_correction_evidence.get("superseded_readiness_sha256") != continuation_superseded_readiness_sha
        or continuation_portability_correction_evidence.get("failed_publication_sha256") != continuation_publication_failure_sha
        or continuation_portability_correction_evidence.get("assertions", {}).get("focused_test_count") != 23
        or continuation_portability_correction_evidence.get("assertions", {}).get("full_repository_test_count") != 317
        or continuation_portability_correction_evidence.get("assertions", {}).get("temporary_external_root_isolation_tested") is not True
        or continuation_portability_correction_evidence.get("assertions", {}).get("public_ci_passed") is not False
        or continuation_portability_correction_evidence.get("assertions", {}).get("activation_performed") is not False
        or continuation_portability_correction_evidence.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or continuation_portability_correction_evidence.get("assertions", {}).get("product_payload_requested") is not False
        or continuation_portability_correction_evidence.get("assertions", {}).get("m1_src_004_requested") is not False
        or continuation_portability_correction_evidence.get("assertions", {}).get("pixel_processing_released") is not False
    ):
        fail("EVID-0088 continuation-001 portable test correction differs")

    violations = []
    for relative in tracked_files():
        path = Path(relative)
        lower = relative.lower()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(relative)
        if any(part in lower for part in FORBIDDEN_NAME_PARTS):
            violations.append(relative)
        if ".safe/" in lower or ".gdb/" in lower:
            violations.append(relative)
    if violations:
        fail("forbidden tracked artifacts: " + ", ".join(sorted(set(violations))))

    print(f"PASS: {len(REQUIRED)} required files, JSON controls, and Git artifact boundaries validated.")


if __name__ == "__main__":
    main()
