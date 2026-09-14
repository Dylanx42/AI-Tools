from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from racktool.gui.session import GuiSession
from racktool.gui.window import CockpitWindow, create_app
from racktool.models.domain import Device


def _fill_descending_axis(
    sheet: Worksheet,
    column: int,
    start_row: int,
    height: int,
) -> None:
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
    sheet["B2"] = "设备 A"
    sheet["B5"] = "设备 B"
    workbook.save(path)


@pytest.fixture(scope="module", autouse=True)
def qt_application() -> object:
    return create_app([])


def test_window_uses_navigable_pages_and_caps_visible_devices(tmp_path: Path) -> None:
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
    cockpit = CockpitWindow()
    try:
        cockpit.load_session(session)

        assert cockpit.content_stack.count() == 4
        assert [button.text().strip()[-2:] for button in cockpit.nav_buttons] == [
            "总览",
            "机柜",
            "设备",
            "异常",
        ]
        assert cockpit.device_table.rowCount() == 100
        headers = [
            cockpit.device_table.horizontalHeaderItem(index).text()
            for index in range(cockpit.device_table.columnCount())
        ]
        assert headers == ["设备", "机柜", "U 位", "高度", "状态"]
        assert "ID" not in "".join(headers)
        assert "仅显示前 100 条" in cockpit.device_count_label.text()
    finally:
        cockpit.widget().close()


def test_rack_scene_only_renders_the_selected_rack(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    session = GuiSession.open_workbook(path)
    first_rack = session.project.racks[0]
    second_rack = replace(first_rack, rack_id="rack-b", rack_name="RACK-B")
    placements = list(session.project.placements)
    placements[1] = replace(placements[1], rack_id=second_rack.rack_id)
    session.project = replace(
        session.project,
        racks=[first_rack, second_rack],
        placements=placements,
    )
    cockpit = CockpitWindow()
    try:
        cockpit.load_session(session)

        assert cockpit.rack_list.count() == 2
        assert cockpit._rack_scene_device_count == 1
        assert cockpit._rack_scene_device_count < len(session.project.placements)

        cockpit.rack_list.setCurrentRow(1)
        assert cockpit.rack_title.text() == "RACK-B"
        assert cockpit._rack_scene_device_count == 1
    finally:
        cockpit.widget().close()


def test_move_drawer_stages_without_writing_source(tmp_path: Path) -> None:
    path = tmp_path / "layout.xlsx"
    _make_layout(path)
    before = path.read_bytes()
    session = GuiSession.open_workbook(path)
    device = next(
        item for item in session.project.devices if item.display_text == "设备 B"
    )
    cockpit = CockpitWindow()
    try:
        cockpit.load_session(session)
        cockpit._selected_device = device.device_id
        cockpit._refresh_device_detail()
        cockpit._open_move_drawer()
        cockpit.target_start_u.setValue(4)
        cockpit._update_move_preview()

        assert cockpit.drawer_add_button.isEnabled()
        cockpit._stage_drawer_move()

        assert path.read_bytes() == before
        assert len(session.pending_moves) == 1
        assert cockpit.pending_table.rowCount() == 1
        assert cockpit.sync_button.isEnabled()
        assert not cockpit.move_drawer.isVisible()
    finally:
        cockpit.widget().close()


def test_global_sync_is_the_only_device_move_write_control() -> None:
    source = Path(__file__).parents[2] / "src" / "racktool" / "gui" / "window.py"
    text = source.read_text(encoding="utf-8")

    assert text.count("apply_pending_moves()") == 1
    assert 'setObjectName("globalSyncButton")' in text
    assert "openpyxl" not in text
