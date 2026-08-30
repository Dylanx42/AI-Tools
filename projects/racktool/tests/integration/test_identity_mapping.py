from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from racktool.core.project import import_workbook, rescan_workbook
from racktool.persistence import load_project, save_project


def _fill_descending_axis(sheet: Worksheet, column: int, start_row: int, height: int) -> None:
    for offset, u_number in enumerate(range(height, 0, -1)):
        sheet.cell(start_row + offset, column, u_number)


def _make_layout(path: Path, left_text: str, right_text: str, right_start: str = "B5") -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "机柜"
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "RACK-A"
    _fill_descending_axis(sheet, 1, 2, 12)
    _fill_descending_axis(sheet, 3, 2, 12)
    sheet.merge_cells("B2:B3")
    sheet["B2"] = left_text
    sheet[right_start] = right_text
    workbook.save(path)


def _device_by_text(project, text: str):
    return next(device for device in project.devices if device.display_text == text)


def _placement_for(project, device_id: str):
    return next(item for item in project.placements if item.device_id == device_id)


def test_rename_keeps_device_id(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path, "设备 A", "设备 B")
    imported = import_workbook(path)
    original = _device_by_text(imported, "设备 A")

    workbook = load_workbook(path)
    workbook.active["B2"] = "设备 A-改名"
    workbook.save(path)

    rescanned = rescan_workbook(path, imported).project
    renamed = next(device for device in rescanned.devices if device.device_id == original.device_id)
    assert renamed.display_text == "设备 A-改名"
    assert len(rescanned.devices) == len(imported.devices)


def test_move_updates_mapping_without_duplicating_device(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path, "设备 A", "设备 B", right_start="B5")
    imported = import_workbook(path)
    original = _device_by_text(imported, "设备 B")
    original_placement = _placement_for(imported, original.device_id)

    workbook = load_workbook(path)
    sheet = workbook.active
    sheet["B5"] = None
    sheet["B8"] = "设备 B"
    workbook.save(path)

    result = rescan_workbook(path, imported)
    moved = _placement_for(result.project, original.device_id)
    assert original.device_id not in result.created_device_ids
    assert moved.start_u != original_placement.start_u
    assert len(result.project.devices) == len(imported.devices)


def test_identical_rescan_does_not_create_devices(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path, "设备 A", "设备 B")
    imported = import_workbook(path)
    result = rescan_workbook(path, imported)
    assert result.created_device_ids == ()
    assert result.created_rack_ids == ()
    assert {device.device_id for device in result.project.devices} == {
        device.device_id for device in imported.devices
    }


def test_ambiguous_duplicate_text_is_not_silently_matched(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "RACK-A"
    _fill_descending_axis(sheet, 1, 2, 12)
    _fill_descending_axis(sheet, 3, 2, 12)
    sheet["B2"] = "同名设备"
    sheet["B5"] = "同名设备"
    workbook.save(path)

    imported = import_workbook(path)
    workbook = load_workbook(path)
    workbook.active["B2"] = None
    workbook.active["B8"] = "同名设备"
    workbook.active["B5"] = None
    workbook.active["B10"] = "同名设备"
    workbook.save(path)

    result = rescan_workbook(path, imported)
    assert any(item.code == "ambiguous-device-identity" for item in result.project.conflicts)


def test_sqlite_round_trip_preserves_identities(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    database = tmp_path / "project.sqlite"
    _make_layout(path, "设备 A", "设备 B")
    imported = import_workbook(path)
    save_project(database, imported)
    loaded = load_project(database)
    assert loaded.to_dict()["project_id"] == imported.project_id
    assert {device.device_id for device in loaded.devices} == {
        device.device_id for device in imported.devices
    }
