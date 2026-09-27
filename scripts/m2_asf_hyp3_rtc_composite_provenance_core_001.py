"""Receipt-only composite provenance rule for the first exact HyP3 RTC ZIP.

This does not replace the terminal README result or establish pixel fitness.
Callers must independently bind the immutable receipt and implementation bytes.
"""

from __future__ import annotations

from m2_asf_hyp3_rtc_core_001 import RouteStop


SOURCE_ID = "M1-SRC-002"
JOB_ID = "dad53076-78fc-42e8-a58e-ad17efb88a7e"
PRODUCT_FILENAME = "S1D_IW_20260816T122141_DVP_RTC10_G_gpuned_944C.zip"
ARCHIVE_SIZE = 9574123274
ARCHIVE_SHA256 = "82ca5a9e7c77dd1e28c15eb64f93e5a408ec53b81b5df3fda64bf47c286dc6d3"
README_SHA256 = "1c387e54051d6d585a49ed9f09342c1d85e2f038ef9b7af5b7d01eb1ea295fad"


def evaluate_composite(
    submission: dict, descriptor: dict, acquisition: dict, readme: dict,
    approved_job: dict,
) -> dict:
    """Accept only the exact preserved, internally consistent receipt chain."""
    if not all(isinstance(value, dict) for value in (
        submission, descriptor, acquisition, readme, approved_job,
    )):
        raise RouteStop("rtc_composite_evidence_invalid")
    if (
        approved_job.get("source_id") != SOURCE_ID
        or submission.get("source_id") != SOURCE_ID
        or descriptor.get("source_id") != SOURCE_ID
        or acquisition.get("source_id") != SOURCE_ID
        or readme.get("source_id") != SOURCE_ID
        or any(value.get("job_id") != JOB_ID for value in (
            submission, descriptor, acquisition, readme,
        ))
        or submission.get("status") != "submitted_product_unverified"
        or submission.get("job_type") != approved_job.get("job_type")
        or submission.get("job_parameters") != approved_job.get("job_parameters")
        or submission.get("name") != approved_job.get("name")
        or submission.get("credentials_recorded") is not False
        or descriptor.get("status") != "pass_exact_zip_descriptor_transfer_not_started"
        or descriptor.get("product_filename") != PRODUCT_FILENAME
        or descriptor.get("expected_size_bytes") != ARCHIVE_SIZE
        or descriptor.get("provider_url_recorded_publicly") is not False
        or acquisition.get("status") != "pass_local_zip_promoted_no_replace"
        or acquisition.get("product_filename") != PRODUCT_FILENAME
        or acquisition.get("archive_size_bytes") != ARCHIVE_SIZE
        or acquisition.get("archive_sha256") != ARCHIVE_SHA256
        or acquisition.get("archive_integrity_verified") is not True
        or acquisition.get("credentials_recorded") is not False
        or acquisition.get("geotiff_headers_or_pixels_read") is not False
        or acquisition.get("raster_pixel_values_decoded") is not False
        or readme.get("status") != "defer_readme_source_text_review"
        or readme.get("product_filename") != PRODUCT_FILENAME
        or readme.get("readme_sha256") != README_SHA256
        or readme.get("readme_member_size_bytes") != 16540
        or readme.get("archive_sha256_verified_current") is not True
        or readme.get("exact_source_granule_text_present") is not True
        or readme.get("exact_product_base_text_present") is not False
        or readme.get("archive_bytes_mutated") is not False
        or readme.get("raster_pixels_read") is not False
    ):
        raise RouteStop("rtc_composite_evidence_conflict")
    return {
        "status": "pass_composite_provenance_for_local_qa_only",
        "source_id": SOURCE_ID,
        "job_id": JOB_ID,
        "product_filename": PRODUCT_FILENAME,
        "archive_sha256": ARCHIVE_SHA256,
        "readme_sha256": README_SHA256,
        "old_readme_status_preserved": "defer_readme_source_text_review",
        "missing_readme_product_base_warning": True,
        "product_payload_read_by_evaluation": False,
        "raster_pixels_read": False,
        "pixel_qa_pass": False,
        "arcgis_map_ready": False,
    }
