from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from radar_input_readiness_core_amendment_001 import (  # noqa: E402
    parse_s1_annotation,
    validate_annotation,
    validate_contract,
)


def annotation_xml(expected: dict, label: str) -> bytes:
    start = datetime.fromisoformat(expected["acquisition_start_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
    end = datetime.fromisoformat(expected["acquisition_end_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
    orbit_start = (start - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    orbit_end = (end + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    return f"""<product>
  <adsHeader><missionId>S1D</missionId><productType>GRD</productType><polarisation>VV</polarisation>
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
    <pixelValue>{label}</pixelValue><outputPixels>16 bit Unsigned Integer</outputPixels>
    <rangePixelSpacing>10</rangePixelSpacing><azimuthPixelSpacing>10</azimuthPixelSpacing>
  </imageInformation></imageAnnotation>
</product>""".encode("utf-8")


class RadarInputReadinessAmendment001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "config/qa/radar-input-readiness-contract-amendment-001.json").read_text(encoding="utf-8")
        )
        cls.expected = cls.contract["sources"][0]

    def test_amended_contract_is_exact_and_preserves_downstream_blocks(self) -> None:
        self.assertEqual(validate_contract(self.contract), [])
        self.assertEqual(self.contract["metadata_checks"]["pixel_value"], "Detected")
        self.assertEqual(
            self.contract["amendment"]["only_observed_data_semantic_change"],
            "metadata_checks.pixel_value: AMPLITUDE -> Detected",
        )
        self.assertFalse(self.contract["decision_semantics"]["pass_releases_baseline_processing"])
        self.assertFalse(self.contract["claim_boundary"]["pixel_values_examined"])

    def test_detected_is_accepted(self) -> None:
        parsed = parse_s1_annotation(annotation_xml(self.expected, "Detected"))
        self.assertEqual(validate_annotation(parsed, self.expected, "VV", self.contract), [])

    def test_amplitude_is_refused_by_amended_contract(self) -> None:
        parsed = parse_s1_annotation(annotation_xml(self.expected, "AMPLITUDE"))
        errors = validate_annotation(parsed, self.expected, "VV", self.contract)
        self.assertEqual(errors, ["VV annotation pixel value is not Detected"])


if __name__ == "__main__":
    unittest.main()
