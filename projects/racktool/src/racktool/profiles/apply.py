from __future__ import annotations

from pathlib import Path

from racktool.core import analyze_workbook
from racktool.models.analysis import SheetAnalysis, WorkbookAnalysis
from racktool.profiles.fingerprint import fingerprint_workbook
from racktool.profiles.matcher import match_profile, select_profile
from racktool.profiles.schema import LayoutProfile, ProfileApplication


def _ignored_devices(
    profile: LayoutProfile, sheets: tuple[SheetAnalysis, ...]
) -> tuple[str, ...]:
    ignored = {
        item.casefold() for item in profile.text.ignore_exact
    }
    if not ignored:
        return ()
    selected: list[str] = []
    for sheet in sheets:
        for device in sheet.devices:
            if device.display_text.strip().casefold() in ignored:
                selected.append(device.candidate_id)
    return tuple(selected)


def _filter_sheet(sheet: SheetAnalysis, ignored_ids: set[str]) -> SheetAnalysis:
    devices = [device for device in sheet.devices if device.candidate_id not in ignored_ids]
    device_ids = {device.candidate_id for device in devices}
    placements = [
        placement
        for placement in sheet.placements
        if placement.device_candidate_id in device_ids
    ]
    return SheetAnalysis(
        name=sheet.name,
        u_axes=list(sheet.u_axes),
        racks=list(sheet.racks),
        devices=devices,
        placements=placements,
        issues=list(sheet.issues),
    )


def _analysis_dict(
    analysis: WorkbookAnalysis, selected_names: tuple[str, ...], ignored_ids: tuple[str, ...]
) -> dict[str, object]:
    ignored = set(ignored_ids)
    selected = set(selected_names)
    sheets = [
        _filter_sheet(sheet, ignored) if sheet.name in selected else sheet
        for sheet in analysis.sheets
    ]
    return WorkbookAnalysis(format=analysis.format, sheets=sheets).to_dict()


def apply_profile(
    workbook_path: Path,
    profile: LayoutProfile,
    *,
    dry_run: bool = True,
    force: bool = False,
) -> ProfileApplication:
    analysis = analyze_workbook(workbook_path)
    fingerprint = fingerprint_workbook(workbook_path, analysis)
    matches = match_profile(profile, analysis)
    selection = select_profile(profile, analysis)

    if selection.status == "unmatched":
        return ProfileApplication(
            status="rejected",
            profile_id=profile.profile_id,
            dry_run=dry_run,
            fingerprint=fingerprint,
            matches=matches,
            selected_sheets=(),
            ignored_device_candidate_ids=(),
            analysis=None,
            message=selection.message,
        )
    if selection.status == "ambiguous":
        return ProfileApplication(
            status="ambiguous",
            profile_id=profile.profile_id,
            dry_run=dry_run,
            fingerprint=fingerprint,
            matches=matches,
            selected_sheets=(),
            ignored_device_candidate_ids=(),
            analysis=None,
            message=selection.message,
        )
    if selection.status == "review_required" and not force:
        return ProfileApplication(
            status="review_required",
            profile_id=profile.profile_id,
            dry_run=dry_run,
            fingerprint=fingerprint,
            matches=matches,
            selected_sheets=(),
            ignored_device_candidate_ids=(),
            analysis=None,
            message=selection.message,
        )

    selected_sheets = tuple(
        item.sheet_name for item in matches if item.status == "matched"
    )
    if not selected_sheets and force:
        selected_sheets = tuple(
            item.sheet_name for item in matches if item.status == "review_required"
        )
    ignored_ids = _ignored_devices(
        profile,
        tuple(sheet for sheet in analysis.sheets if sheet.name in selected_sheets),
    )
    payload = None if dry_run else _analysis_dict(analysis, selected_sheets, ignored_ids)
    action = "Dry-run selected" if dry_run else "Applied"
    return ProfileApplication(
        status="applied",
        profile_id=profile.profile_id,
        dry_run=dry_run,
        fingerprint=fingerprint,
        matches=matches,
        selected_sheets=selected_sheets,
        ignored_device_candidate_ids=ignored_ids,
        analysis=payload,
        message=f"{action} Profile {profile.profile_id} on {', '.join(selected_sheets)}",
    )
