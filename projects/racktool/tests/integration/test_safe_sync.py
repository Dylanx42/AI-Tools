from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from racktool.core.project import import_workbook
from racktool.core.sync import apply_writeback, plan_device_move


def _fill_descending_axis(sheet: Worksheet, column: int, start_row: int, height: int) -> None:
    for offset, u_number in enumerate(range(height, 0, -1)):
        sheet.cell(start_row + offset, column, u_number)


def _make_layout(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "机柜"
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "RACK-A"
    _fill_descending_axis(sheet, 1, 2, 12)
    _fill_descending_axis(sheet, 3, 2, 12)
    sheet.merge_cells("B2:B3")
    sheet["B2"] = "设备 A"
    sheet["B2"].font = Font(bold=True)
    sheet["B2"].fill = PatternFill("solid", fgColor="00FF00")
    sheet["B5"] = "设备 B"
    sheet["Z1"] = "保留备注"
    workbook.create_sheet("无关表").append(["不要删除"])
    workbook.save(path)


def _device(project, text: str):
    return next(item for item in project.devices if item.display_text == text)


def test_normal_move_updates_1u_and_preserves_unrelated_data(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    original = path.read_bytes()
    project = import_workbook(path)
    device = _device(project, "设备 B")
    rack_id = project.racks[0].rack_id

    plan = plan_device_move(project, device.device_id, rack_id, 4, 4)
    result = apply_writeback(path, project, plan)

    assert result.status == "applied"
    assert result.backup_path is not None
    assert Path(result.backup_path).read_bytes() == original
    workbook = load_workbook(path)
    try:
        assert workbook.active["B10"].value == "设备 B"
        assert workbook.active["Z1"].value == "保留备注"
        assert [sheet.title for sheet in workbook.worksheets] == ["机柜", "无关表"]
    finally:
        workbook.close()


def test_multi_u_move_merges_and_unmerges(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    project = import_workbook(path)
    device = _device(project, "设备 A")
    rack_id = project.racks[0].rack_id

    plan = plan_device_move(project, device.device_id, rack_id, 6, 8)
    result = apply_writeback(path, project, plan)

    assert result.status == "applied"
    workbook = load_workbook(path)
    try:
        merged = {str(item) for item in workbook.active.merged_cells.ranges}
        assert "B6:B8" in merged or "B6:B8" in {item.replace("$", "") for item in merged}
        assert workbook.active["B6"].value == "设备 A"
        assert workbook.active["B6"].font.bold is True
        assert workbook.active["B2"].value in (None, "")
    finally:
        workbook.close()


def test_occupied_target_is_rejected_without_changing_source(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    original = path.read_bytes()
    project = import_workbook(path)
    device = _device(project, "设备 B")
    rack_id = project.racks[0].rack_id

    plan = plan_device_move(project, device.device_id, rack_id, 11, 12)
    result = apply_writeback(path, project, plan)

    assert plan.conflicts
    assert result.status == "rejected"
    assert path.read_bytes() == original


def test_out_of_bounds_move_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    original = path.read_bytes()
    project = import_workbook(path)
    device = _device(project, "设备 B")
    rack_id = project.racks[0].rack_id

    plan = plan_device_move(project, device.device_id, rack_id, 12, 13)
    result = apply_writeback(path, project, plan)

    assert any(item.code == "u-out-of-bounds" for item in plan.conflicts)
    assert result.status == "rejected"
    assert path.read_bytes() == original


def test_failed_validation_leaves_original_file(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    original = path.read_bytes()
    project = import_workbook(path)
    device = _device(project, "设备 B")
    rack_id = project.racks[0].rack_id
    plan = plan_device_move(project, device.device_id, rack_id, 4, 4)

    def boom(*args, **kwargs):
        raise ValueError("forced validation failure")

    monkeypatch.setattr("racktool.core.sync._validate_written_workbook", boom)
    result = apply_writeback(path, project, plan)

    assert result.status == "failed"
    assert path.read_bytes() == original
