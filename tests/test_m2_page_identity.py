from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_page_identity import evaluate_page_body, normalized_terms_identity  # noqa: E402


def terms_html(legal_text: str, related_news: str) -> bytes:
    return f'''<!doctype html>
<html><head><script type="application/ld+json">{{"dateModified":"2026-05-05T08:04:39+0200"}}</script></head>
<body><nav>changing shell</nav><section class="paragraph" id="paragraph--1"><h2>Terms</h2><p>{legal_text}</p><a href="https://sentinels.copernicus.eu/legal">Legal</a></section><aside>{related_news}</aside></body></html>'''.encode()


class M2PageIdentityTests(unittest.TestCase):
    def test_terms_identity_ignores_page_shell_and_related_news(self) -> None:
        first = terms_html("Sentinel data are free, full and open basis.", "old news")
        second = terms_html("Sentinel data are free, full and open basis.", "new news")
        self.assertNotEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())
        self.assertEqual(
            normalized_terms_identity(first)["normalized_text_sha256"],
            normalized_terms_identity(second)["normalized_text_sha256"],
        )

    def test_terms_comparison_accepts_shell_drift(self) -> None:
        first = terms_html("Sentinel data are free, full and open basis.", "old news")
        expected_identity = normalized_terms_identity(first)
        expected = {
            "page_id": "terms-and-conditions",
            "url": "https://example.invalid/terms",
            "comparison_mode": "normalized_terms_section_sha256",
            "terms_identity": {
                "normalized_text_sha256": expected_identity["normalized_text_sha256"],
                "structured_date_modified": expected_identity["structured_date_modified"],
                "required_phrases": ["free, full and open basis"],
            },
        }
        observation = evaluate_page_body(expected, terms_html("Sentinel data are free, full and open basis.", "new news"))
        self.assertTrue(observation["terms_identity_unchanged_from_preflight_refresh"])

    def test_terms_comparison_rejects_legal_section_change(self) -> None:
        first = terms_html("Sentinel data are free, full and open basis.", "old news")
        expected_identity = normalized_terms_identity(first)
        expected = {
            "comparison_mode": "normalized_terms_section_sha256",
            "terms_identity": {
                "normalized_text_sha256": expected_identity["normalized_text_sha256"],
                "structured_date_modified": expected_identity["structured_date_modified"],
                "required_phrases": ["free, full and open basis"],
            },
        }
        with self.assertRaisesRegex(ValueError, "official_access_or_terms_page_changed"):
            evaluate_page_body(expected, terms_html("Sentinel data are restricted.", "old news"))

    def test_raw_page_comparison_remains_exact(self) -> None:
        body = b"exact official bytes"
        expected = {"comparison_mode": "raw_sha256", "sha256": hashlib.sha256(body).hexdigest()}
        self.assertTrue(evaluate_page_body(expected, body)["unchanged_from_preflight"])
        with self.assertRaisesRegex(ValueError, "official_access_or_terms_page_changed"):
            evaluate_page_body(expected, body + b" changed")


if __name__ == "__main__":
    unittest.main()
