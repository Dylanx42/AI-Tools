from __future__ import annotations

import re

from racktool.models.analysis import SheetAnalysis, WorkbookAnalysis
from racktool.profiles.schema import (
    LayoutProfile,
    MatchStatus,
    ProfileMatchResult,
    ProfileSelection,
)


def _score(hits: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(hits / total, 4)


def _sheet_pairing(sheet: SheetAnalysis) -> str:
    paired = sum(1 for rack in sheet.racks if rack.right_axis_column is not None)
    edge = sum(1 for rack in sheet.racks if rack.right_axis_column is None)
    if paired and edge:
        return "mixed"
    if paired:
        return "paired"
    if edge:
        return "single_axis_edge"
    return "none"


def match_profile_to_sheet(profile: LayoutProfile, sheet: SheetAnalysis) -> ProfileMatchResult:
    reasons: list[str] = []
    hard_mismatches: list[str] = []
    soft_mismatches: list[str] = []
    checks = 0
    hits = 0

    checks += 1
    if profile.match.sheet_name_regex is None:
        hits += 1
        reasons.append("no sheet-name filter")
    elif re.search(profile.match.sheet_name_regex, sheet.name) is not None:
        hits += 1
        reasons.append("sheet name matches regex")
    else:
        hard_mismatches.append("sheet name does not match regex")

    checks += 1
    if sheet.racks:
        hits += 1
        reasons.append("sheet has rack candidates")
    else:
        hard_mismatches.append("sheet has no rack candidates")

    checks += 1
    expected_title_evidence = (
        "Profile fixed rack coordinates"
        if profile.rack.title_mode == "fixed_range"
        else "merged rack title immediately above U axis"
    )
    if sheet.racks and all(expected_title_evidence in rack.evidence for rack in sheet.racks):
        hits += 1
        reasons.append(f"rack title mode is {profile.rack.title_mode}")
    else:
        hard_mismatches.append(f"rack titles do not satisfy {profile.rack.title_mode}")

    checks += 1
    if sheet.racks and all(
        rack.height_u == max(rack.u_to_row) - min(rack.u_to_row) + 1 for rack in sheet.racks
    ):
        hits += 1
        reasons.append("rack height is inferred from U axis")
    else:
        hard_mismatches.append("rack height is not inferred from U axis")

    checks += 1
    directions = {rack.direction for rack in sheet.racks}
    if sheet.racks and (
        profile.u_axis.direction == "any" or directions == {profile.u_axis.direction}
    ):
        hits += 1
        reasons.append(f"U-axis direction is {profile.u_axis.direction}")
    else:
        hard_mismatches.append(
            f"U-axis direction {sorted(directions)} does not match {profile.u_axis.direction}"
        )

    checks += 1
    pairing = _sheet_pairing(sheet)
    if sheet.racks and (profile.u_axis.pairing == "any" or pairing == profile.u_axis.pairing):
        hits += 1
        reasons.append(f"axis pairing is {pairing}")
    else:
        hard_mismatches.append(
            f"axis pairing {pairing} does not match {profile.u_axis.pairing}"
        )

    checks += 1
    heights = {rack.height_u for rack in sheet.racks}
    allowed = set(profile.u_axis.allowed_heights)
    if sheet.racks and (not allowed or heights <= allowed):
        hits += 1
        reasons.append("rack heights are within the allowed set")
    else:
        hard_mismatches.append(
            f"rack heights {sorted(heights)} are outside {sorted(allowed)}"
        )

    checks += 1
    if profile.device_area.mode == "fixed_range":
        if sheet.racks and all("Profile fixed device area" in rack.evidence for rack in sheet.racks):
            hits += 1
            reasons.append("device area uses validated fixed coordinates")
        else:
            hard_mismatches.append("device area does not use the Profile fixed range")
    elif profile.device_area.mode == "between_u_axes":
        if pairing == "paired":
            hits += 1
            reasons.append("device area sits between paired U axes")
        else:
            hard_mismatches.append("device area is not strictly between paired U axes")
    elif pairing in {"paired", "single_axis_edge", "mixed"}:
        hits += 1
        reasons.append("device area is between U axes or at a single-axis edge")
    else:
        hard_mismatches.append(
            "device area cannot be located between or at the edge of U axes"
        )

    if profile.match.require_issue_free:
        checks += 1
        if not sheet.issues:
            hits += 1
            reasons.append("sheet has no unresolved analysis issues")
        else:
            soft_mismatches.append("sheet still has unresolved analysis issues")

    score = _score(hits, checks)
    mismatches = tuple(hard_mismatches + soft_mismatches)
    status: MatchStatus
    if hard_mismatches:
        status = "rejected"
    elif soft_mismatches:
        status = (
            "review_required"
            if score >= profile.match.review_confidence
            else "rejected"
        )
    elif score >= profile.match.min_confidence:
        status = "matched"
    elif score >= profile.match.review_confidence:
        status = "review_required"
    else:
        status = "rejected"
    return ProfileMatchResult(
        profile_id=profile.profile_id,
        sheet_name=sheet.name,
        score=score,
        status=status,
        reasons=tuple(reasons),
        mismatches=mismatches,
    )


def match_profile(
    profile: LayoutProfile, analysis: WorkbookAnalysis
) -> tuple[ProfileMatchResult, ...]:
    return tuple(match_profile_to_sheet(profile, sheet) for sheet in analysis.sheets)


def select_profile(
    profile: LayoutProfile, analysis: WorkbookAnalysis
) -> ProfileSelection:
    matches = match_profile(profile, analysis)
    accepted = [item for item in matches if item.status == "matched"]
    review = [item for item in matches if item.status == "review_required"]

    if len(accepted) == 1:
        selected = accepted[0]
        return ProfileSelection(
            status="matched",
            selected_profile_id=profile.profile_id,
            selected_sheet_name=selected.sheet_name,
            score=selected.score,
            matches=matches,
            message=f"Profile matched Sheet {selected.sheet_name}",
        )

    if len(accepted) > 1:
        if profile.match.allow_multiple_sheets and not review:
            return ProfileSelection(
                status="matched",
                selected_profile_id=profile.profile_id,
                selected_sheet_name=None,
                score=min(item.score for item in accepted),
                matches=matches,
                message="Profile matched multiple Sheets by explicit permission",
            )
        return ProfileSelection(
            status="ambiguous",
            selected_profile_id=None,
            selected_sheet_name=None,
            score=None,
            matches=matches,
            message="Multiple Sheets matched the same Profile; refuse to guess",
        )

    if len(review) > 1 and not profile.match.allow_multiple_sheets:
        return ProfileSelection(
            status="ambiguous",
            selected_profile_id=None,
            selected_sheet_name=None,
            score=max(item.score for item in review),
            matches=matches,
            message="Multiple Sheets require review; refuse to guess",
        )

    if review:
        return ProfileSelection(
            status="review_required",
            selected_profile_id=None,
            selected_sheet_name=None,
            score=max(item.score for item in review),
            matches=matches,
            message="Profile is close enough to review, but not confident enough to auto-apply",
        )

    return ProfileSelection(
        status="unmatched",
        selected_profile_id=None,
        selected_sheet_name=None,
        score=max((item.score for item in matches), default=0.0),
        matches=matches,
        message="Profile does not match this workbook",
    )
