"""Explain and validate unfamiliar layouts using the existing deterministic parser.

Every operation uses one immutable input snapshot. Suggestions describe geometry,
never embed device text, and cannot mutate/import business workbooks themselves.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

from racktool.core.analyzer import analyze_workbook
from racktool.core.workbook import scan_workbook
from racktool.models.analysis import SheetAnalysis
from racktool.profiles.apply import analyze_profiled_workbook, apply_profile
from racktool.profiles.loader import load_profile, validate_profile_data
from racktool.profiles.schema import LayoutProfile, ProfileError
from racktool.profiles.storage import canonical_profile_payload, profile_payload_sha256


@contextmanager
def _snapshot(workbook: Path, expected_sha256: str | None) -> Iterator[tuple[Path, str]]:
    source = workbook.expanduser().resolve()
    if source.suffix.lower() != ".xlsx":
        raise ProfileError("Layout adaptation only supports .xlsx files")
    content = source.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if expected_sha256 is not None and expected_sha256 != digest:
        raise ProfileError("Source SHA256 changed; inspect the current workbook before adapting")
    with tempfile.TemporaryDirectory(prefix="racktool-layout-") as directory:
        path = Path(directory) / "source.xlsx"
        path.write_bytes(content)
        yield path, digest


def _uncertainty(sheet: SheetAnalysis, threshold: float = 0.8) -> list[str]:
    reasons: list[str] = []
    if not sheet.racks:
        reasons.append("no-rack-candidates: provide explicit geometry or exclude this sheet")
    if sheet.issues:
        reasons.append("unresolved-analysis-issues")
    for kind, candidates in (
        ("u-axis", sheet.u_axes), ("rack", sheet.racks),
        ("device", sheet.devices), ("placement", sheet.placements),
    ):
        if any(candidate.confidence < threshold for candidate in candidates):
            reasons.append(f"low-confidence-{kind}-candidates")
    return reasons


def _base_payload(profile_id: str, sheet_name: str) -> dict[str, Any]:
    return {
        "schema_version": 1, "profile_id": profile_id,
        "name": "Reviewed worksheet layout",
        "match": {
            "sheet_name_regex": "^" + re.escape(sheet_name) + "$",
            "min_confidence": 1.0, "review_confidence": 0.5,
            "allow_multiple_sheets": False, "require_issue_free": True,
        },
        "rack": {
            "title": {"mode": "merged_cell_above_u_axis"},
            "height": {"mode": "infer_from_u_axis"},
        },
        "u_axis": {"direction": "any", "pairing": "any", "max_missing_rows": 0},
        "device_area": {"mode": "between_or_edge"},
        "text": {"ignore_exact": []},
    }


def _structural_profile(sheet: SheetAnalysis, profile_id: str) -> LayoutProfile:
    if not sheet.racks:
        raise ProfileError("No rack candidates: supply the complete fixed-coordinate hints")
    payload = _base_payload(profile_id, sheet.name)
    paired = [rack.right_axis_column is not None for rack in sheet.racks]
    pairing = "paired" if all(paired) else "mixed" if any(paired) else "single_axis_edge"
    directions = {rack.direction for rack in sheet.racks}
    payload["u_axis"].update({
        "pairing": pairing, "direction": next(iter(directions)) if len(directions) == 1 else "any",
        "allowed_heights": sorted({rack.height_u for rack in sheet.racks}),
    })
    payload["device_area"]["mode"] = "between_u_axes" if pairing == "paired" else "between_or_edge"
    return validate_profile_data(payload)


def _checked(snapshot: Path, digest: str, profile: LayoutProfile) -> dict[str, Any]:
    application = apply_profile(snapshot, profile, dry_run=True)
    uncertainty: list[str] = []
    selected_analysis: dict[str, Any] | None = None
    if application.status == "applied":
        selected = analyze_profiled_workbook(snapshot, profile)
        selected_analysis = selected.to_dict()
        for sheet in selected.sheets:
            uncertainty.extend(f"{sheet.name}: {reason}" for reason in _uncertainty(sheet))
    else:
        uncertainty.append(application.message)
    ready = application.status == "applied" and not uncertainty
    payload = canonical_profile_payload(profile)
    return {
        "schema_version": 1, "status": "ready_for_import" if ready else "review_required",
        "source_sha256": digest, "profile_id": profile.profile_id,
        "profile_sha256": profile_payload_sha256(payload),
        "dry_run": application.to_dict(), "review_reasons": uncertainty,
        "selected_analysis": selected_analysis,
        "human_confirmation_required": True,
        "import_contract": {
            "command": (
                "project import <unchanged-workbook.xlsx> <new-project.sqlite>"
                " --profile <layout.yaml> --expected-sha256 <source-sha256>"
            ),
            "selected_sheets": list(application.selected_sheets),
            "source_sha256_must_equal": digest,
            "requires_reviewed_candidates": True,
            "persisted_profile": True,
            "heterogeneous_sheet_rules": "separate profiles and separate projects; not one combined project",
        },
    }


def inspect_layout(workbook: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    """Return per-sheet evidence and reusable profile candidates; never auto-select."""
    with _snapshot(workbook, expected_sha256) as (snapshot, digest):
        structure = scan_workbook(snapshot)
        analysis = analyze_workbook(snapshot)
        info = {sheet.name: sheet for sheet in structure.sheets}
        sheets: list[dict[str, Any]] = []
        for index, sheet in enumerate(analysis.sheets, 1):
            proposal: dict[str, Any] | None = None
            if sheet.racks:
                profile = _structural_profile(sheet, f"layout-sheet-{index}")
                proposal = _checked(snapshot, digest, profile)
                proposal["profile"] = canonical_profile_payload(profile)
            sheets.append({
                "name": sheet.name, "state": info[sheet.name].state,
                "used_range": info[sheet.name].used_range,
                "u_axes": [axis.to_dict() for axis in sheet.u_axes],
                "racks": [rack.to_dict() for rack in sheet.racks],
                "devices": [device.to_dict() for device in sheet.devices],
                "issues": [issue.to_dict() for issue in sheet.issues],
                "review_reasons": _uncertainty(sheet), "profile_candidate": proposal,
            })
        return {
            "schema_version": 1, "status": "review_required", "source_sha256": digest,
            "human_confirmation_required": True, "sheets": sheets,
            "batch_contract": {
                "one_rule_per_sheet": True,
                "import": "propose/check each selected sheet, then import to a separate SQLite project",
                "combined_heterogeneous_project_supported": False,
                "unrecognized_or_unselected_sheets": "must be explicitly reviewed or excluded",
            },
            "required_fixed_hints": [
                "sheet", "title_range", "left_axis", "start_row", "end_row", "device_range", "direction",
            ],
            "limitations": [
                "No automatic OCR, shapes, semantic color interpretation, or arbitrary XLSX compatibility",
                "Fixed-coordinate profiles describe one rack per selected sheet",
            ],
        }


def propose_layout(
    workbook: Path, output: Path, *, sheet_name: str, profile_id: str,
    hints: Mapping[str, object] | None = None, expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Persist a validated pure layout YAML, with match/dry-run evidence for review."""
    destination = output.expanduser().resolve()
    if destination.suffix.lower() not in {".yaml", ".yml"}:
        raise ProfileError("Proposed Profile must use .yaml or .yml")
    if destination.exists():
        raise FileExistsError("Profile destination exists; use a new filename")
    with _snapshot(workbook, expected_sha256) as (snapshot, digest):
        sheets = {sheet.name: sheet for sheet in analyze_workbook(snapshot).sheets}
        if sheet_name not in sheets:
            raise ProfileError("Requested room worksheet does not exist")
        if hints:
            required = {"title_range", "left_axis", "start_row", "end_row", "device_range", "direction"}
            if set(hints) - (required | {"right_axis"}) or required - set(hints):
                raise ProfileError("Fixed-coordinate hints must include the complete geometry")
            payload = _base_payload(profile_id, sheet_name)
            payload["rack"]["title"] = {"mode": "fixed_range", "range": hints["title_range"]}
            payload["device_area"] = {"mode": "fixed_range", "range": hints["device_range"]}
            payload["u_axis"] = {
                "direction": hints["direction"],
                "pairing": "paired" if hints.get("right_axis") is not None else "single_axis_edge",
                "left_column": hints["left_axis"], "start_row": hints["start_row"],
                "end_row": hints["end_row"], "max_missing_rows": 0,
            }
            if hints.get("right_axis") is not None:
                payload["u_axis"]["right_column"] = hints["right_axis"]
            profile = validate_profile_data(payload)
        else:
            profile = _structural_profile(sheets[sheet_name], profile_id)
        # Load the exact bytes that will be distributed, not only the in-memory object.
        temporary = snapshot.parent / "profile.yaml"
        temporary.write_text(yaml.safe_dump(
            canonical_profile_payload(profile), allow_unicode=True, sort_keys=False,
        ), encoding="utf-8")
        result = _checked(snapshot, digest, load_profile(temporary))
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".layout-", suffix=".yaml", dir=destination.parent)
        os.close(descriptor)
        staging = Path(name)
        try:
            staging.write_bytes(temporary.read_bytes())
            load_profile(staging)
            # Exclusive destination creation also protects against another process racing us.
            os.link(staging, destination)
        finally:
            staging.unlink(missing_ok=True)
        result["profile_path"] = str(destination)
        return result


def check_layout(
    workbook: Path, profile_path: Path, *, expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate/reload YAML and re-evaluate matches against one source snapshot."""
    profile = load_profile(profile_path)
    with _snapshot(workbook, expected_sha256) as (snapshot, digest):
        return _checked(snapshot, digest, profile)
