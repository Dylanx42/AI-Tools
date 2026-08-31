from __future__ import annotations

from pathlib import Path

from racktool.core.analyzer import (
    AnalysisOptions,
    CoordinateRackRule,
    analyze_workbook,
    recompute_analysis_issues,
)
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
    filtered = SheetAnalysis(
        name=sheet.name,
        u_axes=list(sheet.u_axes),
        racks=list(sheet.racks),
        devices=devices,
        placements=placements,
        issues=[],
    )
    filtered.issues.extend(recompute_analysis_issues(filtered))
    return filtered


def _analysis_options(profile: LayoutProfile) -> AnalysisOptions:
    coordinate_rack = None
    if profile.rack.title_mode == "fixed_range":
        title_range = profile.rack.title_range
        device_range = profile.device_area.source_range
        left_column = profile.u_axis.left_column
        start_row = profile.u_axis.start_row
        end_row = profile.u_axis.end_row
        if (
            title_range is None
            or device_range is None
            or left_column is None
            or start_row is None
            or end_row is None
        ):
            raise ValueError("Validated fixed-range Profile is missing coordinate fields")
        coordinate_rack = CoordinateRackRule(
            title_range=title_range,
            left_axis_column=left_column,
            right_axis_column=profile.u_axis.right_column,
            start_row=start_row,
            end_row=end_row,
            device_range=device_range,
        )
    direction = profile.u_axis.direction
    return AnalysisOptions(
        axis_direction=None if direction == "any" else direction,
        axis_pairing=(
            None
            if coordinate_rack is None or profile.u_axis.pairing in {"any", "mixed"}
            else profile.u_axis.pairing
        ),
        allowed_heights=profile.u_axis.allowed_heights,
        max_missing_rows=profile.u_axis.max_missing_rows,
        coordinate_rack=coordinate_rack,
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
    analysis = analyze_workbook(workbook_path, _analysis_options(profile))
    fingerprint = fingerprint_workbook(workbook_path, analysis)
    all_ignored_ids = _ignored_devices(profile, tuple(analysis.sheets))
    filtered_analysis = WorkbookAnalysis(
        format=analysis.format,
        sheets=[_filter_sheet(sheet, set(all_ignored_ids)) for sheet in analysis.sheets],
    )
    matches = match_profile(profile, filtered_analysis)
    selection = select_profile(profile, filtered_analysis)

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
        review_sheets = tuple(
            item.sheet_name for item in matches if item.status == "review_required"
        )
        if len(review_sheets) > 1 and not profile.match.allow_multiple_sheets:
            return ProfileApplication(
                status="ambiguous",
                profile_id=profile.profile_id,
                dry_run=dry_run,
                fingerprint=fingerprint,
                matches=matches,
                selected_sheets=(),
                ignored_device_candidate_ids=(),
                analysis=None,
                message="Multiple Sheets require review; refuse to force a single-Sheet Profile",
            )
        selected_sheets = review_sheets
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
