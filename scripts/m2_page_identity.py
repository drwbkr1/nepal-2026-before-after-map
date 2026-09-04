#!/usr/bin/env python3
"""Stable identities for official pages used by the M2 Sentinel gate."""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from typing import Any


TERMS_SECTION_ID = "paragraph--1"
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class _SectionTextParser(HTMLParser):
    def __init__(self, section_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.section_id = section_id
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if self.depth:
            if tag not in VOID_ELEMENTS:
                self.depth += 1
            if tag == "a" and attributes.get("href"):
                self.parts.append(str(attributes["href"]))
        elif tag == "section" and attributes.get("id") == self.section_id:
            self.depth = 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.depth and tag == "a":
            attributes = dict(attrs)
            if attributes.get("href"):
                self.parts.append(str(attributes["href"]))

    def handle_endtag(self, tag: str) -> None:
        if self.depth:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.parts.append(data)


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def normalized_terms_identity(body: bytes) -> dict[str, Any]:
    text = body.decode("utf-8")
    parser = _SectionTextParser(TERMS_SECTION_ID)
    parser.feed(text)
    normalized = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    if not normalized:
        raise ValueError("official_terms_section_missing")
    date_match = re.search(r'"dateModified"\s*:\s*"([^"]+)"', text)
    if date_match is None:
        raise ValueError("official_terms_date_modified_missing")
    return {
        "section_id": TERMS_SECTION_ID,
        "normalized_text_length": len(normalized),
        "normalized_text_sha256": sha256_bytes(normalized.encode("utf-8")),
        "structured_date_modified": date_match.group(1),
        "normalized_text": normalized,
    }


def evaluate_page_body(expected: dict[str, Any], body: bytes) -> dict[str, Any]:
    raw_sha = sha256_bytes(body)
    mode = expected.get("comparison_mode", "raw_sha256")
    observation: dict[str, Any] = {
        "page_id": expected.get("page_id"),
        "url": expected.get("url"),
        "comparison_mode": mode,
        "rendered_page_sha256": raw_sha,
    }
    if mode == "raw_sha256":
        if raw_sha != expected.get("sha256"):
            raise ValueError("official_access_or_terms_page_changed")
        observation["unchanged_from_preflight"] = True
        return observation
    if mode != "normalized_terms_section_sha256":
        raise ValueError("unsupported_official_page_comparison_mode")

    identity = normalized_terms_identity(body)
    expected_identity = expected.get("terms_identity", {})
    if (
        identity["normalized_text_sha256"] != expected_identity.get("normalized_text_sha256")
        or identity["structured_date_modified"] != expected_identity.get("structured_date_modified")
    ):
        raise ValueError("official_access_or_terms_page_changed")
    folded = identity["normalized_text"].casefold()
    required_phrases = expected_identity.get("required_phrases", [])
    if not isinstance(required_phrases, list) or not required_phrases:
        raise ValueError("preflight_terms_binding_incomplete")
    if any(not isinstance(phrase, str) or phrase.casefold() not in folded for phrase in required_phrases):
        raise ValueError("official_access_or_terms_page_changed")
    observation.update({
        "terms_section_id": identity["section_id"],
        "normalized_terms_text_length": identity["normalized_text_length"],
        "normalized_terms_text_sha256": identity["normalized_text_sha256"],
        "structured_date_modified": identity["structured_date_modified"],
        "required_phrase_count": len(required_phrases),
        "terms_identity_unchanged_from_preflight_refresh": True,
    })
    return observation
