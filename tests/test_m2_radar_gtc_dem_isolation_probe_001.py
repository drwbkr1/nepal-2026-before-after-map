import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m2_radar_gtc_dem_isolation_probe_001 as probe  # noqa: E402


class Raster:
    def __init__(self, source=None):
        self.source = source
        self.save_calls = 0

    def save(self, destination):
        self.save_calls += 1
        Path(destination).mkdir()


class FakeIA:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []
        self.result = Raster()

    def ApplyGeometricTerrainCorrection(self, in_radar_data, polarization_bands="#", in_dem_raster="#", geoid="#"):
        self.calls.append((in_radar_data, polarization_bands, in_dem_raster, geoid))
        if self.fail:
            raise RuntimeError("ERROR 000425: deliberately sensitive fake error eyJprivate")
        return self.result


class FakeArcPy:
    Raster = Raster

    def __init__(self, fail=False):
        self.ia = FakeIA(fail)
        self.env = SimpleNamespace(overwriteOutput=None, scratchWorkspace=None)
        self.checkout_count = 0
        self.checkin_count = 0

    def CheckExtension(self, _name):
        return "Available"

    def CheckOutExtension(self, _name):
        self.checkout_count += 1
        return "CheckedOut"

    def CheckInExtension(self, _name):
        self.checkin_count += 1
        return "CheckedIn"

    def GetInstallInfo(self):
        return {"ProductName": "Synthetic", "Version": "0"}


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "preserved.crf"
        self.source.mkdir()
        self.attempt = self.root / "d2"
        preflight = self.root / probe.PREFLIGHT_REF
        preflight.parent.mkdir(parents=True)
        preflight.write_text(json.dumps({"status": "pass_final_no_content_preflight_one_attempt_ready", "bindings": {"execution_gate_sha256": "gate"}}), encoding="utf-8")
        patches = [
            mock.patch.object(probe, "ROOT", self.root),
            mock.patch.object(probe, "SOURCE", self.source),
            mock.patch.object(probe, "ATTEMPT_ROOT", self.attempt),
            mock.patch.object(probe, "OUTPUT", self.attempt / "gtc_no_dem_diagnostic.crf"),
            mock.patch.object(probe, "MIN_FREE_BYTES", 0),
            mock.patch.object(probe, "verified_authority", return_value={}),
            mock.patch.object(probe, "verified_gates", return_value=({}, {})),
            mock.patch.object(probe, "sha256", return_value="gate"),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_one_exact_two_argument_call_one_save_and_second_run_stops(self):
        fake = FakeArcPy()
        result = probe.run_probe(lambda: fake)
        self.assertEqual(result["status"], "pass_no_dem_gtc_diagnostic_only_output_quarantined")
        self.assertEqual(len(fake.ia.calls), 1)
        self.assertEqual(fake.ia.calls[0][1:], ("VV;VH", "#", "#"))
        self.assertEqual(fake.ia.result.save_calls, 1)
        self.assertEqual(fake.checkin_count, 1)
        self.assertIs(fake.env.overwriteOutput, False)
        self.assertEqual(fake.env.scratchWorkspace, str(self.attempt))
        self.assertTrue((self.attempt / "terminal.json").is_file())
        self.assertTrue((self.attempt / "cleanup.json").is_file())
        with self.assertRaisesRegex(probe.ProbeError, "attempt_root_collision"):
            probe.run_probe(lambda: self.fail("second ArcPy import"))

    def test_gtc_failure_is_terminal_sanitized_and_no_save(self):
        fake = FakeArcPy(fail=True)
        result = probe.run_probe(lambda: fake)
        self.assertEqual(result["status"], "block_no_dem_gtc_or_runtime_failure_no_retry")
        self.assertEqual(result["arcgis_error_code"], "000425")
        self.assertEqual(len(fake.ia.calls), 1)
        self.assertFalse(result["output_save_started"])
        self.assertFalse((self.attempt / "gtc_no_dem_diagnostic.crf").exists())
        self.assertNotIn("eyJprivate", (self.attempt / "terminal.json").read_text())
        self.assertTrue((self.attempt / "terminal-reservation.json").is_file())
        self.assertTrue((self.attempt / "cleanup.json").is_file())

    def test_missing_input_stops_before_attempt_reservation(self):
        self.source.rmdir()
        with self.assertRaisesRegex(probe.ProbeError, "exact_preserved_input_missing_or_unsafe"):
            probe.run_probe(lambda: self.fail("ArcPy import after missing input"))
        self.assertFalse(self.attempt.exists())

    def test_terminal_receipt_write_failure_preserves_fallback_and_cleanup(self):
        fake = FakeArcPy()
        original = probe.write_new_json

        def fail_terminal(path, value):
            if path.name == "terminal.json":
                raise OSError("synthetic terminal persistence failure")
            return original(path, value)

        with mock.patch.object(probe, "write_new_json", side_effect=fail_terminal):
            result = probe.run_probe(lambda: fake)
        self.assertEqual(result["status"], "indeterminate_terminal_persistence_failure_no_retry")
        self.assertIn("terminal_write_failed", (self.attempt / "fallback.jsonl").read_text())
        self.assertTrue((self.attempt / "cleanup.json").is_file())

    def test_no_content_runtime_signature_check_does_not_construct_raster(self):
        fake = FakeArcPy()
        with mock.patch.object(fake, "Raster", side_effect=AssertionError("raster constructed")):
            runtime = probe.inspect_no_content(fake)
        self.assertEqual(runtime["gtc_parameters"], list(probe.GTC_PARAMETERS))
        self.assertEqual(fake.ia.calls, [])


if __name__ == "__main__":
    unittest.main()
