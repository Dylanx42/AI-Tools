from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from racktool.cli.main import main
from racktool.core import analyze_workbook
from racktool.profiles import apply_profile, load_profile, select_profile

PROFILE_ROOT = Path(__file__).resolve().parents[2] / "src/racktool/profiles"
DUAL_PROFILE = PROFILE_ROOT / "generic-dual-axis.yaml"
MIXED_PROFILE = PROFILE_ROOT / "generic-mixed-axis.yaml"


def _fill_descending_axis(sheet: Worksheet, column: int, start_row: int, height: int) -> None:
    for offset, u_number in enumerate(range(height, 0, -1)):
        sheet.cell(start_row + offset, column, u_number)


def _make_dual_axis_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "双轴"
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "RACK-A"
    _fill_descending_axis(sheet, 1, 2, 12)
    _fill_descending_axis(sheet, 3, 2, 12)
    sheet.merge_cells("B2:B3")
    sheet["B2"] = "设备 A"
    sheet["B5"] = "空闲"
    workbook.save(path)


def _make_mixed_axis_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "共享轴"
    sheet.merge_cells("A1:B1")
    sheet["A1"] = "RACK-1"
    sheet.merge_cells("C1:D1")
    sheet["C1"] = "RACK-2"
    _fill_descending_axis(sheet, 1, 2, 10)
    _fill_descending_axis(sheet, 3, 2, 10)
    sheet["B2"] = "共享轴左侧设备"
    sheet.merge_cells("D2:D6")
    sheet["D2"] = "边缘机柜设备"
    workbook.save(path)


def test_generic_dual_axis_profile_matches_and_dry_runs(tmp_path: Path) -> None:
    path = tmp_path / "dual-axis.xlsx"
    _make_dual_axis_workbook(path)
    profile = load_profile(DUAL_PROFILE)
    source_bytes = path.read_bytes()

    selection = select_profile(profile, analyze_workbook(path))
    dry_run = apply_profile(path, profile, dry_run=True)
    applied = apply_profile(path, profile, dry_run=False)

    assert selection.status == "matched"
    assert dry_run.status == "applied"
    assert dry_run.dry_run is True
    assert dry_run.analysis is None
    assert applied.status == "applied"
    assert applied.dry_run is False
    assert applied.selected_sheets == ("双轴",)
    assert applied.ignored_device_candidate_ids
    assert path.read_bytes() == source_bytes


def test_wrong_profile_is_rejected_instead_of_guessing(tmp_path: Path) -> None:
    path = tmp_path / "mixed-axis.xlsx"
    _make_mixed_axis_workbook(path)
    dual = load_profile(DUAL_PROFILE)
    mixed = load_profile(MIXED_PROFILE)

    assert select_profile(mixed, analyze_workbook(path)).status == "matched"
    rejected = apply_profile(path, dual, dry_run=True)
    assert rejected.status == "rejected"
    assert rejected.analysis is None


def test_ambiguous_multi_sheet_match_is_not_auto_applied(tmp_path: Path) -> None:
    path = tmp_path / "two-layouts.xlsx"
    workbook = Workbook()
    first = workbook.active
    assert first is not None
    first.title = "布局A"
    first.merge_cells("A1:C1")
    first["A1"] = "RACK-A"
    _fill_descending_axis(first, 1, 2, 12)
    _fill_descending_axis(first, 3, 2, 12)
    first["B2"] = "设备A"
    second = workbook.create_sheet("布局B")
    second.merge_cells("A1:C1")
    second["A1"] = "RACK-B"
    _fill_descending_axis(second, 1, 2, 12)
    _fill_descending_axis(second, 3, 2, 12)
    second["B2"] = "设备B"
    workbook.save(path)

    result = apply_profile(path, load_profile(DUAL_PROFILE), dry_run=True)
    assert result.status == "ambiguous"
    assert result.analysis is None


def test_review_required_profile_needs_explicit_force(tmp_path: Path) -> None:
    path = tmp_path / "numeric-device.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "RACK-NUMERIC"
    _fill_descending_axis(sheet, 1, 2, 12)
    _fill_descending_axis(sheet, 3, 2, 12)
    sheet["B2"] = 10001
    workbook.save(path)

    profile = load_profile(DUAL_PROFILE)
    blocked = apply_profile(path, profile, dry_run=True)
    forced = apply_profile(path, profile, dry_run=True, force=True)

    assert blocked.status == "review_required"
    assert forced.status == "applied"


def test_profile_cli_validate_match_and_dry_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "cli-profile.xlsx"
    _make_dual_axis_workbook(path)

    assert main(["profile", "validate", str(DUAL_PROFILE)]) == 0
    validate_out = capsys.readouterr().out
    assert main(["profile", "match", str(path), str(DUAL_PROFILE)]) == 0
    match_out = capsys.readouterr().out
    assert main(["profile", "apply", str(path), str(DUAL_PROFILE)]) == 0
    apply_out = capsys.readouterr().out
    assert json.loads(validate_out)["profile_id"] == "generic-dual-axis"
    assert json.loads(match_out)["status"] == "matched"
    applied = json.loads(apply_out)
    assert applied["status"] == "applied"
    assert applied["dry_run"] is True
