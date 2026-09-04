from __future__ import annotations

import copy
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_radar_input_readiness_contract import build_contract  # noqa: E402
from radar_input_readiness_core import (  # noqa: E402
    ROLE_PATTERNS,
    decide_source_readiness,
    parse_s1_annotation,
    select_required_members,
    summarize_partial_readiness,
    validate_annotation,
    validate_contract,
    validate_raster_description,
)


def annotation_xml(expected: dict, polarization: str = "VV", *, mission: str = "S1D") -> bytes:
    acquisition_start = datetime.fromisoformat(expected["acquisition_start_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
    acquisition_end = datetime.fromisoformat(expected["acquisition_end_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
    orbit_start = (acquisition_start - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    orbit_end = (acquisition_end + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    return f"""<product>
  <adsHeader><missionId>{mission}</missionId><productType>GRD</productType><polarisation>{polarization}</polarisation>
    <mode>IW</mode><swath>IW</swath><startTime>{expected['acquisition_start_utc']}</startTime>
    <stopTime>{expected['acquisition_end_utc']}</stopTime><absoluteOrbitNumber>{expected['absolute_orbit_number']}</absoluteOrbitNumber>
  </adsHeader>
  <generalAnnotation><productInformation><pass>{expected['orbit_direction'].title()}</pass></productInformation>
    <orbitList count="2">
      <orbit><time>{orbit_start}</time><position><x>1</x><y>2</y><z>3</z></position><velocity><x>4</x><y>5</y><z>6</z></velocity></orbit>
      <orbit><time>{orbit_end}</time><position><x>2</x><y>3</y><z>4</z></position><velocity><x>5</x><y>6</y><z>7</z></velocity></orbit>
    </orbitList>
  </generalAnnotation>
  <imageAnnotation><imageInformation><numberOfSamples>12</numberOfSamples><numberOfLines>8</numberOfLines>
    <pixelValue>AMPLITUDE</pixelValue><outputPixels>16 bit Unsigned Integer</outputPixels>
    <rangePixelSpacing>10</rangePixelSpacing><azimuthPixelSpacing>10</azimuthPixelSpacing>
  </imageInformation></imageAnnotation>
</product>""".encode()


def complete_manifest() -> dict:
    concrete = {
        "manifest_safe": "manifest.safe",
        "annotation_vv": "annotation/s1d-iw-grd-vv-test.xml",
        "annotation_vh": "annotation/s1d-iw-grd-vh-test.xml",
        "calibration_vv": "annotation/calibration/calibration-s1d-iw-grd-vv-test.xml",
        "calibration_vh": "annotation/calibration/calibration-s1d-iw-grd-vh-test.xml",
        "noise_vv": "annotation/calibration/noise-s1d-iw-grd-vv-test.xml",
        "noise_vh": "annotation/calibration/noise-s1d-iw-grd-vh-test.xml",
        "measurement_vv": "measurement/s1d-iw-grd-vv-test.tiff",
        "measurement_vh": "measurement/s1d-iw-grd-vh-test.tiff",
    }
    return {
        "status": "complete",
        "files": [
            {"relative_path": relative, "size_bytes": index, "sha256": f"{index:064x}"}
            for index, relative in enumerate(concrete.values(), start=1)
        ],
    }


def raster_description(width: int = 12, height: int = 8) -> dict:
    return {
        "format": "TIFF",
        "band_count": 1,
        "width": width,
        "height": height,
        "pixel_type": "U16",
        "spatial_reference_wkid": 0,
    }


class RadarInputReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = build_contract("2026-09-04T18:00:00Z")
        cls.expected = cls.contract["sources"][0]

    def test_contract_is_exact_and_read_only(self) -> None:
        self.assertEqual(validate_contract(self.contract), [])
        self.assertEqual([item["source_id"] for item in self.contract["sources"]], ["M1-SRC-001", "M1-SRC-002", "M1-SRC-003"])
        self.assertEqual(self.contract["execution_boundary"]["external_data_mutation"], "prohibited")
        self.assertFalse(self.contract["decision_semantics"]["pass_releases_baseline_processing"])

    def test_contract_rejects_broadened_source_or_pixel_claim(self) -> None:
        changed = copy.deepcopy(self.contract)
        changed["sources"][0]["source_id"] = "M1-SRC-004"
        changed["claim_boundary"]["pixel_values_examined"] = True
        self.assertGreaterEqual(len(validate_contract(changed)), 2)

    def test_required_inventory_passes_exactly_once(self) -> None:
        result = select_required_members(complete_manifest(), self.contract)
        self.assertEqual(result["status"], "pass_inventory_only")
        self.assertEqual(set(result["members"]), set(ROLE_PATTERNS))

    def test_required_inventory_blocks_missing_and_duplicate_member(self) -> None:
        missing = complete_manifest()
        missing["files"] = missing["files"][:-1]
        self.assertEqual(select_required_members(missing, self.contract)["status"], "block")
        duplicate = complete_manifest()
        duplicate["files"].append(copy.deepcopy(duplicate["files"][-1]))
        self.assertEqual(select_required_members(duplicate, self.contract)["status"], "block")

    def test_required_inventory_blocks_unsafe_path(self) -> None:
        manifest = complete_manifest()
        manifest["files"].append({"relative_path": "../escape", "size_bytes": 1, "sha256": "a" * 64})
        result = select_required_members(manifest, self.contract)
        self.assertEqual(result["status"], "block")
        self.assertTrue(any("unsafe path" in item for item in result["errors"]))

    def test_annotation_parse_and_validation_pass(self) -> None:
        parsed = parse_s1_annotation(annotation_xml(self.expected))
        self.assertEqual(parsed["orbit_vector_count_observed"], 2)
        self.assertEqual(validate_annotation(parsed, self.expected, "VV", self.contract), [])

    def test_annotation_rejects_dtd_and_wrong_mission(self) -> None:
        dtd = parse_s1_annotation(b'<!DOCTYPE x [<!ENTITY e "x">]><x>&e;</x>')
        self.assertTrue(dtd["errors"])
        parsed = parse_s1_annotation(annotation_xml(self.expected, mission="S1A"))
        self.assertTrue(any("mission_id" in item for item in validate_annotation(parsed, self.expected, "VV", self.contract)))

    def test_annotation_rejects_nonincreasing_orbit_times(self) -> None:
        payload = annotation_xml(self.expected)
        parsed_once = parse_s1_annotation(payload)
        payload = payload.replace(parsed_once["orbit_time_end"].encode(), b"2026-08-16T12:19:00Z")
        parsed = parse_s1_annotation(payload)
        self.assertTrue(any("strictly increasing" in item for item in validate_annotation(parsed, self.expected, "VV", self.contract)))

    def test_annotation_rejects_orbit_vectors_that_do_not_bracket_acquisition(self) -> None:
        payload = annotation_xml(self.expected)
        parsed_once = parse_s1_annotation(payload)
        payload = payload.replace(parsed_once["orbit_time_start"].encode(), self.expected["acquisition_start_utc"].replace("16.058226", "17.058226").encode())
        parsed = parse_s1_annotation(payload)
        self.assertTrue(any("do not bracket" in item for item in validate_annotation(parsed, self.expected, "VV", self.contract)))

    def test_raster_description_must_match_annotation(self) -> None:
        parsed = parse_s1_annotation(annotation_xml(self.expected))
        self.assertEqual(validate_raster_description(raster_description(), parsed, "VV", self.contract), [])
        changed = raster_description(width=13)
        self.assertTrue(any("width" in item for item in validate_raster_description(changed, parsed, "VV", self.contract)))

    def test_source_decision_passes_headers_only(self) -> None:
        annotations = {
            key: parse_s1_annotation(annotation_xml(self.expected, polarization))
            for key, polarization in (("vv", "VV"), ("vh", "VH"))
        }
        descriptions = {"vv": raster_description(), "vh": raster_description()}
        decision = decide_source_readiness("pass_inventory_only", annotations, descriptions, self.expected, self.contract)
        self.assertEqual(decision["status"], "pass_header_readability_only")
        self.assertFalse(decision["baseline_processing_released"])

    def test_source_decision_blocks_cross_polarization_mismatch(self) -> None:
        annotations = {
            key: parse_s1_annotation(annotation_xml(self.expected, polarization))
            for key, polarization in (("vv", "VV"), ("vh", "VH"))
        }
        descriptions = {"vv": raster_description(), "vh": raster_description(width=13)}
        decision = decide_source_readiness("pass_inventory_only", annotations, descriptions, self.expected, self.contract)
        self.assertEqual(decision["status"], "block")

    def test_source_decision_blocks_cross_polarization_metadata_mismatch(self) -> None:
        annotations = {
            key: parse_s1_annotation(annotation_xml(self.expected, polarization))
            for key, polarization in (("vv", "VV"), ("vh", "VH"))
        }
        annotations["vh"]["range_pixel_spacing"] = 11.0
        descriptions = {"vv": raster_description(), "vh": raster_description()}
        decision = decide_source_readiness("pass_inventory_only", annotations, descriptions, self.expected, self.contract)
        self.assertEqual(decision["status"], "block")
        self.assertTrue(any("range_pixel_spacing" in item for item in decision["errors"]))

    def test_aggregate_pass_is_partial_and_releases_nothing(self) -> None:
        decisions = {
            source_id: {"status": "pass_header_readability_only"}
            for source_id in ("M1-SRC-001", "M1-SRC-002", "M1-SRC-003")
        }
        summary = summarize_partial_readiness(decisions)
        self.assertEqual(summary["status"], "pass_partial_pre_event_header_readiness_only")
        self.assertFalse(summary["complete_before_after_pair"])
        self.assertFalse(summary["baseline_processing_released"])


if __name__ == "__main__":
    unittest.main()
