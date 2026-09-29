#!/usr/bin/env python3
"""Decode Landsat 8/9 Collection 2 QA words without choosing a mask.

This module interprets the USGS bit positions mechanically. It does not read
rasters, classify usable pixels, set scientific thresholds, or authorize a
Landsat route. See the USGS Collection 2 Quality Assessment Bands page:
https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _words(values: Any, maximum: int) -> np.ndarray:
    words = np.asarray(values)
    if words.dtype.kind not in "iu":
        raise ValueError("landsat_qa_words_must_be_integers")
    if np.any(words < 0) or np.any(words > maximum):
        raise ValueError("landsat_qa_word_out_of_range")
    return words.astype(np.uint16, copy=False)


def _flag(words: np.ndarray, bit: int) -> np.ndarray:
    return (words & (1 << bit)) != 0


def decode_qa_pixel(values: Any) -> dict[str, np.ndarray]:
    """Return flags and 2-bit confidences; `clear` is only the USGS bit value."""
    words = _words(values, 65535)
    return {
        "fill": _flag(words, 0),
        "dilated_cloud": _flag(words, 1),
        "high_confidence_cirrus": _flag(words, 2),
        "high_confidence_cloud": _flag(words, 3),
        "high_confidence_cloud_shadow": _flag(words, 4),
        "high_confidence_snow": _flag(words, 5),
        "clear_bit": _flag(words, 6),
        "water": _flag(words, 7),
        "cloud_confidence": (words >> 8) & 3,
        "cloud_shadow_confidence": (words >> 10) & 3,
        "snow_ice_confidence": (words >> 12) & 3,
        "cirrus_confidence": (words >> 14) & 3,
    }


def decode_qa_radsat(values: Any) -> dict[str, np.ndarray]:
    """Decode only the five proposed reflectance bands and terrain occlusion."""
    words = _words(values, 65535)
    return {
        "band3_saturated": _flag(words, 2),
        "band4_saturated": _flag(words, 3),
        "band5_saturated": _flag(words, 4),
        "band6_saturated": _flag(words, 5),
        "band7_saturated": _flag(words, 6),
        "terrain_occlusion": _flag(words, 11),
    }


def decode_sr_qa_aerosol(values: Any) -> dict[str, np.ndarray]:
    """Return retrieval flags and the 0..3 aerosol level; no exclusion rule."""
    words = _words(values, 255)
    return {
        "fill": _flag(words, 0),
        "valid_retrieval": _flag(words, 1),
        "water": _flag(words, 2),
        "interpolated": _flag(words, 5),
        "aerosol_level": (words >> 6) & 3,
    }
