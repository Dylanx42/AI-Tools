from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from racktool.gui.session import GuiSession


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
    sheet["B5"] = "设备 B"
    workbook.save(path)


def test_session_lists_devices_racks_mappings_and_occupancy(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    session = GuiSession.open_workbook(path)

    assert len(session.device_rows()) == 2
    assert session.rack_rows()[0]["rack_name"] == "RACK-A"
    assert session.mapping_rows()
    occupancy = session.occupancy_rows(session.project.racks[0].rack_id)
    assert occupancy[0]["u"] == 12
    assert any(row["display_text"] == "设备 B" for row in occupancy)


def test_session_preview_rejects_occupied_target(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    session = GuiSession.open_workbook(path)
    device = next(item for item in session.project.devices if item.display_text == "设备 B")
    rack_id = session.project.racks[0].rack_id

    plan = session.plan_move(device.device_id, rack_id, 11, 12)

    assert plan.conflicts
    assert session.conflict_rows()


def test_session_move_export_and_restore_backup(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    original = path.read_bytes()
    session = GuiSession.open_workbook(path)
    device = next(item for item in session.project.devices if item.display_text == "设备 B")
    rack_id = session.project.racks[0].rack_id

    plan = session.plan_move(device.device_id, rack_id, 4, 4)
    assert not plan.conflicts
    result = session.apply_move()
    assert result.status == "applied"
    workbook = load_workbook(path)
    try:
        assert workbook.active["B10"].value == "设备 B"
    finally:
        workbook.close()

    export_path = session.export_json(tmp_path / "project.json")
    assert export_path.is_file()
    backups = session.backups()
    assert backups
    session.restore_backup(backups[0])
    assert path.read_bytes() == original
