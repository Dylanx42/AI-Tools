from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from racktool.gui.session import GuiSession
from racktool.models.domain import Device
from racktool.models.project import IdentityConflict
from racktool.persistence import load_project


def _fill_descending_axis(
    sheet: Worksheet,
    column: int,
    start_row: int,
    height: int,
) -> None:
    for offset, u_number in enumerate(range(height, 0, -1)):
        sheet.cell(start_row + offset, column, u_number)


def _make_layout(path: Path, *, duplicate_names: bool = False) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "机柜"
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "RACK-A"
    _fill_descending_axis(sheet, 1, 2, 12)
    _fill_descending_axis(sheet, 3, 2, 12)
    sheet["B2"] = "同名设备" if duplicate_names else "设备 A"
    sheet["B5"] = "同名设备" if duplicate_names else "设备 B"
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
    device = next(
        item for item in session.project.devices if item.display_text == "设备 B"
    )
    rack_id = session.project.racks[0].rack_id

    plan = session.plan_move(device.device_id, rack_id, 12, 12)

    assert any(item.code == "target-u-occupied" for item in plan.conflicts)
    assert session.conflict_rows()


def test_staging_does_not_write_until_global_apply(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    session = GuiSession.open_workbook(path)
    before = path.read_bytes()
    device = next(
        item for item in session.project.devices if item.display_text == "设备 B"
    )
    rack_id = session.project.racks[0].rack_id

    plan = session.stage_move(device.device_id, rack_id, 4, 4)

    assert not plan.conflicts
    assert len(session.pending_moves) == 1
    assert path.read_bytes() == before

    result = session.apply_pending_moves()

    assert result.status == "applied"
    assert not session.pending_moves
    assert path.read_bytes() != before
    workbook = load_workbook(path)
    try:
        assert workbook["机柜"]["B10"].value == "设备 B"
        assert workbook["机柜"]["B5"].value is None
    finally:
        workbook.close()


def test_staging_rejects_pending_target_overlap_without_losing_queue(
    tmp_path: Path,
) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    session = GuiSession.open_workbook(path)
    rack_id = session.project.racks[0].rack_id
    device_a = next(
        item for item in session.project.devices if item.display_text == "设备 A"
    )
    device_b = next(
        item for item in session.project.devices if item.display_text == "设备 B"
    )
    session.stage_move(device_a.device_id, rack_id, 11, 11)

    rejected = session.stage_move(device_b.device_id, rack_id, 11, 11)

    assert any(item.code == "plan-target-overlap" for item in rejected.conflicts)
    assert [item.device_id for item in session.pending_moves] == [device_a.device_id]


def test_two_pending_moves_commit_in_one_safe_sync(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    session = GuiSession.open_workbook(path)
    rack_id = session.project.racks[0].rack_id
    devices = {item.display_text: item for item in session.project.devices}
    session.stage_move(devices["设备 A"].device_id, rack_id, 11, 11)
    session.stage_move(devices["设备 B"].device_id, rack_id, 8, 8)

    result = session.apply_pending_moves()

    assert result.status == "applied"
    assert len(result.plan.actions) == 2
    assert result.backup_path is not None
    assert not session.pending_moves


def test_device_page_is_searchable_and_capped_at_one_hundred(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    session = GuiSession.open_workbook(path)
    session.project = replace(
        session.project,
        devices=[
            Device(device_id=f"device-{index}", display_text=f"设备 {index}")
            for index in range(110)
        ],
        placements=[],
        mappings=[],
    )

    rows, total = session.device_page(limit=100)
    matches, match_total = session.device_page("设备 109")

    assert total == 110
    assert len(rows) == 100
    assert match_total == 1
    assert matches[0]["primary_label"] == "设备 109"


def test_session_move_can_reopen_export_and_restore_atomically(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    original = path.read_bytes()
    session = GuiSession.open_workbook(path)
    device = next(
        item for item in session.project.devices if item.display_text == "设备 B"
    )
    rack_id = session.project.racks[0].rack_id

    plan = session.plan_move(device.device_id, rack_id, 4, 4)
    assert not plan.conflicts
    result = session.apply_move()
    assert result.status == "applied"
    assert session.project.source_workbook == str(path.resolve())

    reopened = GuiSession.open_project(session.database_path)
    reopened_mapping = next(
        item
        for item in reopened.project.mappings
        if item.mapping_kind == "device" and item.device_id == device.device_id
    )
    assert reopened_mapping.source_range == "B10"
    export_path = reopened.export_json(tmp_path / "project.json")
    assert export_path.is_file()

    backups = reopened.backups()
    assert backups
    reopened.restore_backup(backups[0])
    assert path.read_bytes() == original
    restored = GuiSession.open_project(reopened.database_path)
    restored_mapping = next(
        item
        for item in restored.project.mappings
        if item.mapping_kind == "device" and item.device_id == device.device_id
    )
    assert restored_mapping.source_range == "B5"


def test_session_ambiguous_rescan_keeps_memory_and_database_unchanged(
    tmp_path: Path,
) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path, duplicate_names=True)
    session = GuiSession.open_workbook(path)
    original_project = session.project

    workbook = load_workbook(path)
    sheet = workbook.active
    sheet["B2"] = None
    sheet["B5"] = None
    sheet["B8"] = "同名设备"
    sheet["B10"] = "同名设备"
    workbook.save(path)

    returned = session.rescan()

    assert returned == original_project
    assert session.project == original_project
    assert any(
        item.code == "ambiguous-device-identity"
        for item in session.last_rescan_conflicts
    )
    assert load_project(session.database_path).to_dict() == original_project.to_dict()


def _make_sorted_layout(path: Path, *, multiline: bool = False) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "机柜"
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "RACK-B"
    _fill_descending_axis(sheet, 1, 2, 12)
    _fill_descending_axis(sheet, 3, 2, 12)
    sheet["B2"] = "交换机\n核心\n管理口" if multiline else "设备 A"
    sheet["B5"] = "设备 B"
    sheet.merge_cells("E1:G1")
    sheet["E1"] = "RACK-A"
    _fill_descending_axis(sheet, 5, 2, 12)
    _fill_descending_axis(sheet, 7, 2, 12)
    sheet["F2"] = "设备 C"
    sheet["F3"] = "设备 D"
    sheet["F4"] = "设备 E"
    workbook.save(path)


def test_session_preserves_multiline_device_text(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_sorted_layout(path, multiline=True)
    session = GuiSession.open_workbook(path)

    device = next(row for row in session.device_rows() if "交换机" in str(row["display_text"]))
    assert device["display_text"] == "交换机\n核心\n管理口"
    rack_id = str(device["rack_id"])
    segment = next(
        item for item in session.occupancy_segments(rack_id) if item["device_id"] == device["device_id"]
    )
    assert segment["display_text"] == "交换机\n核心\n管理口"


def test_rack_rows_sort_by_source_name_and_occupancy(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_sorted_layout(path)
    session = GuiSession.open_workbook(path)

    source_names = [row["rack_name"] for row in session.rack_rows("source")]
    name_order = [row["rack_name"] for row in session.rack_rows("name")]
    occupancy = session.rack_rows("occupancy")

    assert source_names[0] == "RACK-B"
    assert name_order[0] == "RACK-A"
    assert occupancy[0]["rack_name"] == "RACK-A"
    assert occupancy[0]["occupancy_percent"] >= occupancy[1]["occupancy_percent"]


def test_device_page_filters_and_sorts(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_sorted_layout(path)
    session = GuiSession.open_workbook(path)
    rack_a = next(row for row in session.rack_rows() if row["rack_name"] == "RACK-A")

    rows, total = session.device_page(rack_id=str(rack_a["rack_id"]), sort_by="name")
    by_name = [row["primary_label"] for row in rows]
    _, active_total = session.device_page(status_filter="active")
    _, one_u_total = session.device_page(height_filter="1u")

    assert total == 3
    assert by_name == sorted(by_name)
    assert active_total == 5
    assert one_u_total == 5


def test_issue_rows_group_similar_items_in_chinese(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    session = GuiSession.open_workbook(path)
    session.project = replace(
        session.project,
        conflicts=[
            IdentityConflict(
                code="unresolved-u-axis",
                severity="warning",
                message="U axis at column 9 has no title",
            ),
            IdentityConflict(
                code="unresolved-u-axis",
                severity="warning",
                message="U axis at column 12 has no title",
            ),
            IdentityConflict(
                code="target-u-occupied",
                severity="error",
                message="Target U is occupied",
            ),
        ],
    )

    rows = session.issue_rows()
    titles = [row["title"] for row in rows]

    assert any("2 处" in title for title in titles)
    assert all("unresolved-u-axis" not in row["title"] for row in rows)
    assert all("Target U" not in row["guidance"] for row in rows)
    grouped = next(row for row in rows if "2 处" in row["title"])
    assert "unresolved-u-axis" in grouped["technical_detail"]
    assert "重新扫描" in grouped["guidance"]


def test_overview_sheet_uses_readonly_scan_layout(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_sorted_layout(path, multiline=True)
    session = GuiSession.open_workbook(path)

    names = session.overview_sheet_names()
    sheet = session.overview_sheet(names[0])
    device_texts = [
        str(device["display_text"])
        for rack in sheet["racks"]
        for device in rack["devices"]
    ]

    assert names == ["机柜"]
    assert {rack["rack_name"] for rack in sheet["racks"]} == {"RACK-A", "RACK-B"}
    assert "交换机\n核心\n管理口" in device_texts
    assert all("source_bounds" in device for rack in sheet["racks"] for device in rack["devices"])


def test_session_database_failure_does_not_adopt_half_written_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    original_workbook = path.read_bytes()
    session = GuiSession.open_workbook(path)
    original_project = session.project
    device = next(
        item for item in session.project.devices if item.display_text == "设备 B"
    )
    rack_id = session.project.racks[0].rack_id
    session.plan_move(device.device_id, rack_id, 4, 4)

    def fail_save(*args, **kwargs):
        raise OSError("forced database save failure")

    monkeypatch.setattr("racktool.core.service.save_project", fail_save)
    result = session.apply_move()

    assert result.status == "failed"
    assert session.project == original_project
    assert path.read_bytes() == original_workbook
    assert load_project(session.database_path).to_dict() == original_project.to_dict()
