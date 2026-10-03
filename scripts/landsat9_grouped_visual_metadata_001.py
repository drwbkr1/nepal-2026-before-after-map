#!/usr/bin/env python3
"""Exact Level-2 date/scaling adapter; identity checks remain frozen.

Different groups may reuse a field name. Required paths must each occur once
in both ODL and XML, and agree. No global first/last-value selection occurs.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

import landsat_l2_grouped_mtl_integrity_002 as identity
from landsat9_pixel_visual_core_001 import SCALE, OFFSET

ROOT = identity.ROOT
DATE_GROUP = "IMAGE_ATTRIBUTES"
SCALE_GROUP = "LEVEL2_SURFACE_REFLECTANCE_PARAMETERS"
SELECTED = {(ROOT, DATE_GROUP, key) for key in ("DATE_ACQUIRED", "SCENE_CENTER_TIME")}
SELECTED.update((ROOT, SCALE_GROUP, f"REFLECTANCE_{kind}_BAND_{band}")
                for kind in ("MULT", "ADD") for band in range(3, 8))


class MetadataError(ValueError):
    """Fixed reason code only; never include arbitrary source text."""


def odl_selected(raw: bytes):
    # Frozen structural validator checks every line, balanced groups and END.
    _, groups = identity._odl_fields(raw)
    fields = {}
    stack = []
    for line in raw.decode("utf-8-sig").splitlines():
        line = line.strip()
        if not line or line == "END":
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key == "GROUP":
            stack.append(value)
        elif key == "END_GROUP":
            stack.pop()
        elif (*stack, key) in SELECTED:
            if value.startswith('"') != value.endswith('"'):
                raise MetadataError("mtl_selected_value_syntax_invalid")
            value = value[1:-1] if value.startswith('"') else value
            fields.setdefault((*stack, key), []).append(value)
    return fields, groups


def xml_selected(raw: bytes):
    _, groups = identity._xml_fields(raw)
    fields = {}

    def visit(node, parents):
        path = (*parents, node.tag)
        if path in SELECTED:
            if list(node):
                raise MetadataError("mtl_selected_value_syntax_invalid")
            fields.setdefault(path, []).append((node.text or "").strip())
        for child in node:
            visit(child, path)

    visit(ET.fromstring(raw), ())
    return fields, groups


def inspect(text_raw: bytes, xml_raw: bytes, product: str, scene: str) -> dict:
    identity._verify_grouped_metadata(text_raw, xml_raw, product, scene)
    odl, odl_groups = odl_selected(text_raw)
    xml, xml_groups = xml_selected(xml_raw)
    for fields, groups in ((odl, odl_groups), (xml, xml_groups)):
        if any(groups.get((ROOT, group)) != 1 for group in (DATE_GROUP, SCALE_GROUP)):
            raise MetadataError("mtl_selected_group_missing_or_duplicate")
        if any(len(fields.get(path, [])) != 1 for path in SELECTED):
            raise MetadataError("mtl_selected_field_missing_or_duplicate")
    values = {}
    for path in sorted(SELECTED):
        key = path[-1]
        left, right = odl[path][0], xml[path][0]
        if path[1] == DATE_GROUP:
            if left != right:
                raise MetadataError("mtl_selected_text_xml_disagreement")
            values[key] = left
        else:
            try:
                a, b = Decimal(left), Decimal(right)
            except InvalidOperation:
                raise MetadataError("mtl_reflectance_scale_missing") from None
            if not a.is_finite() or not b.is_finite():
                raise MetadataError("mtl_reflectance_scale_mismatch")
            if a != b:
                raise MetadataError("mtl_selected_text_xml_disagreement")
            expected = SCALE if key.startswith("REFLECTANCE_MULT_") else OFFSET
            value = float(a)
            if not math.isclose(value, expected, rel_tol=0, abs_tol=1e-12):
                raise MetadataError("mtl_reflectance_scale_mismatch")
            values[key] = value
    if values["DATE_ACQUIRED"].replace("-", "") != product.split("_")[3]:
        raise MetadataError("mtl_acquisition_date_mismatch")
    if not re.fullmatch(r"[0-9:.]+Z", values["SCENE_CENTER_TIME"]):
        raise MetadataError("mtl_scene_center_time_invalid")
    return {"date_acquired": values["DATE_ACQUIRED"],
            "scene_center_time": values["SCENE_CENTER_TIME"],
            "reflectance_mult": SCALE, "reflectance_add": OFFSET,
            "selected_group_paths": [ROOT + "/" + g for g in (DATE_GROUP, SCALE_GROUP)],
            "validated_coefficients": {key: value for key, value in values.items()
                                       if key.startswith("REFLECTANCE_")},
            "text_xml_selected_values_agree": True}
