from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from racktool.core.analyzer import analyze_workbook
from racktool.core.workbook import scan_workbook
from racktool.models.analysis import SheetAnalysis, WorkbookAnalysis
from racktool.profiles.schema import WorkbookFingerprint


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pairing(sheet: SheetAnalysis) -> str:
    paired = sum(1 for rack in sheet.racks if rack.right_axis_column is not None)
    edge = sum(1 for rack in sheet.racks if rack.right_axis_column is None)
    if paired and edge:
        return "mixed"
    if paired:
        return "paired"
    if edge:
        return "single_axis_edge"
    return "none"


def _sheet_features(sheet: SheetAnalysis) -> dict[str, Any]:
    heights = sorted({rack.height_u for rack in sheet.racks})
    directions = sorted({rack.direction for rack in sheet.racks})
    issue_codes = sorted({issue.code for issue in sheet.issues})
    return {
        "name": sheet.name,
        "u_axis_count": len(sheet.u_axes),
        "rack_count": len(sheet.racks),
        "device_count": len(sheet.devices),
        "placement_count": len(sheet.placements),
        "issue_count": len(sheet.issues),
        "issue_codes": issue_codes,
        "rack_heights": heights,
        "u_directions": directions,
        "pairing": _pairing(sheet),
        "has_merged_title_above_axis": all(
            "merged rack title immediately above U axis" in rack.evidence
            for rack in sheet.racks
        )
        if sheet.racks
        else False,
        "height_inferred_from_u_axis": all(
            rack.height_u == max(rack.u_to_row) - min(rack.u_to_row) + 1
            for rack in sheet.racks
        )
        if sheet.racks
        else False,
    }


def _layout_payload(analysis: WorkbookAnalysis) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sheets": [_sheet_features(sheet) for sheet in analysis.sheets],
        "totals": {
            "sheets": len(analysis.sheets),
            "racks": sum(len(sheet.racks) for sheet in analysis.sheets),
            "devices": sum(len(sheet.devices) for sheet in analysis.sheets),
            "placements": sum(len(sheet.placements) for sheet in analysis.sheets),
            "issues": sum(len(sheet.issues) for sheet in analysis.sheets),
            "issue_codes": sorted(
                {
                    issue.code
                    for sheet in analysis.sheets
                    for issue in sheet.issues
                }
            ),
            "rack_heights": sorted(
                {
                    rack.height_u
                    for sheet in analysis.sheets
                    for rack in sheet.racks
                }
            ),
            "pairings": dict(
                sorted(Counter(_pairing(sheet) for sheet in analysis.sheets).items())
            ),
        },
    }


def fingerprint_workbook(
    path: Path, analysis: WorkbookAnalysis | None = None
) -> WorkbookFingerprint:
    workbook_path = path.expanduser()
    if analysis is None:
        analysis = analyze_workbook(workbook_path)
    else:
        scan_workbook(workbook_path)
    payload = _layout_payload(analysis)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return WorkbookFingerprint(
        schema_version=1,
        workbook_sha256=_sha256(workbook_path),
        layout_sha256=hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        features=payload,
    )
