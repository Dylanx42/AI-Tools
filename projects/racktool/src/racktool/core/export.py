from __future__ import annotations

import hashlib
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet

from racktool.core.identity import normalize_path
from racktool.core.project import project_error_conflicts
from racktool.models.domain import Device, Placement, Rack
from racktool.models.project import RackProject

_RACK_SHEET = "机柜图"
_POSITION_SHEET = "设备位置表"
_POSITION_HEADERS = (
    "序号",
    "设备",
    "机柜",
    "起始 U",
    "结束 U",
    "高度（U）",
    "工作表",
    "来源单元格",
    "状态",
    "设备 ID",
    "机柜 ID",
)
_RACKS_PER_BAND = 4
_RACK_BLOCK_COLUMNS = 4
_RACK_GUTTER_COLUMNS = 1
_DIAGRAM_MAX_COLUMN = (
    _RACKS_PER_BAND * (_RACK_BLOCK_COLUMNS + _RACK_GUTTER_COLUMNS)
    - _RACK_GUTTER_COLUMNS
)
_FONT_NAME = "Arial"
_DEVICE_FILLS = (
    "D9EAF7",
    "E2F0D9",
    "FFF2CC",
    "FCE4D6",
    "E4DFEC",
    "DDEBF7",
    "F4CCCC",
)

_THIN_GRAY = Side(style="thin", color="AAB4C3")
_MEDIUM_BLUE = Side(style="medium", color="5B7699")
_GRID_BORDER = Border(
    left=_THIN_GRAY,
    right=_THIN_GRAY,
    top=_THIN_GRAY,
    bottom=_THIN_GRAY,
)
_DEVICE_BORDER = Border(
    left=_MEDIUM_BLUE,
    right=_MEDIUM_BLUE,
    top=_MEDIUM_BLUE,
    bottom=_MEDIUM_BLUE,
)


@dataclass(frozen=True, slots=True)
class _PositionRow:
    device_id: str
    display_text: str
    rack_id: str
    rack_name: str
    start_u: int | None
    end_u: int | None
    height_u: int | None
    sheet_name: str
    source_range: str
    status: str
    source_index: int
    rack_index: int


@dataclass(frozen=True, slots=True)
class _ExportManifest:
    rack_titles: tuple[tuple[str, str], ...]
    position_rows: tuple[_PositionRow, ...]


def _literal_text(cell: Cell, value: str) -> None:
    if len(value) > 32_767:
        raise ValueError("导出失败：有单元格文字超过 Excel 可保存的长度上限。")
    cell.value = value
    if value.startswith("="):
        cell.data_type = "s"


def _cell(sheet: Worksheet, row: int, column: int) -> Cell:
    return cast(Cell, sheet.cell(row, column))


def _normalise_display_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _device_fill(device: Device) -> PatternFill:
    seed = device.style_signature or device.device_id
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
    return PatternFill("solid", fgColor=_DEVICE_FILLS[index % len(_DEVICE_FILLS)])


def _normalise_destination(path: Path, project: RackProject) -> Path:
    candidate = path.expanduser()
    if not candidate.suffix:
        candidate = candidate.with_suffix(".xlsx")
    if candidate.suffix.casefold() != ".xlsx":
        raise ValueError("导出文件必须使用 .xlsx 扩展名。")
    destination = candidate.resolve()
    if project.source_workbook is not None:
        source = normalize_path(Path(project.source_workbook))
        if destination == source:
            raise ValueError("导出文件不能覆盖当前源工作簿，请选择另一个文件名。")
    return destination


def _ordered_racks(project: RackProject) -> list[Rack]:
    sheet_order: dict[str, int] = {}
    for rack in project.racks:
        sheet_order.setdefault(rack.source_sheet or "", len(sheet_order))
    source_order = {rack.rack_id: index for index, rack in enumerate(project.racks)}
    return sorted(
        project.racks,
        key=lambda rack: (
            sheet_order.get(rack.source_sheet or "", 10**9),
            rack.bounds.min_row if rack.bounds is not None else 10**9,
            rack.bounds.min_col if rack.bounds is not None else 10**9,
            source_order[rack.rack_id],
        ),
    )


def _position_rows(project: RackProject) -> list[_PositionRow]:
    racks = {rack.rack_id: rack for rack in project.racks}
    rack_order = {rack.rack_id: index for index, rack in enumerate(_ordered_racks(project))}
    placements = {placement.device_id: placement for placement in project.placements}
    mappings = {
        mapping.device_id: mapping
        for mapping in project.mappings
        if mapping.mapping_kind == "device" and mapping.device_id is not None
    }
    rows: list[_PositionRow] = []
    for source_index, device in enumerate(project.devices):
        placement = placements.get(device.device_id)
        mapping = mappings.get(device.device_id)
        rack = racks.get(placement.rack_id) if placement is not None else None
        if placement is None:
            status = "未放置"
        elif placement.status == "active" and rack is not None and rack.status == "active":
            status = "在位"
        elif placement.status == "missing" or (rack is not None and rack.status == "missing"):
            status = "源文件中已缺失"
        else:
            status = placement.status
        start_u = (
            min(placement.start_u, placement.end_u) if placement is not None else None
        )
        end_u = max(placement.start_u, placement.end_u) if placement is not None else None
        rows.append(
            _PositionRow(
                device_id=device.device_id,
                display_text=_normalise_display_text(device.display_text),
                rack_id=placement.rack_id if placement is not None else "",
                rack_name=rack.rack_name if rack is not None else "",
                start_u=start_u,
                end_u=end_u,
                height_u=placement.height_u if placement is not None else None,
                sheet_name=(
                    mapping.sheet_name
                    if mapping is not None
                    else (rack.source_sheet or "" if rack is not None else "")
                ),
                source_range=mapping.source_range if mapping is not None else "",
                status=status,
                source_index=source_index,
                rack_index=rack_order.get(placement.rack_id, 10**9)
                if placement is not None
                else 10**9,
            )
        )
    rows.sort(
        key=lambda row: (
            row.rack_index,
            -(row.end_u if row.end_u is not None else -1),
            row.source_index,
        )
    )
    return rows


def _active_placements(project: RackProject) -> dict[str, list[tuple[Placement, Device]]]:
    devices = {device.device_id: device for device in project.devices}
    by_rack: dict[str, list[tuple[Placement, Device]]] = defaultdict(list)
    for placement in project.placements:
        device = devices.get(placement.device_id)
        if placement.status == "active" and device is not None:
            by_rack[placement.rack_id].append((placement, device))
    for items in by_rack.values():
        items.sort(
            key=lambda item: (
                -max(item[0].start_u, item[0].end_u),
                item[1].device_id,
            )
        )
    return by_rack


def _style_diagram_header(sheet: Worksheet) -> None:
    _literal_text(sheet["A1"], _RACK_SHEET)
    sheet["A1"].font = Font(name=_FONT_NAME, size=16, bold=True, color="172033")
    _literal_text(
        sheet["A2"],
        "按源工作表和源位置顺序排列；设备文字保留原换行；颜色仅用于区分设备。",
    )
    sheet["A2"].font = Font(name=_FONT_NAME, size=10, italic=True, color="667085")
    sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=12)
    sheet.row_dimensions[1].height = 24
    sheet.row_dimensions[2].height = 20


def _style_rack_base(
    sheet: Worksheet,
    rack: Rack,
    *,
    start_column: int,
    title_row: int,
    max_height: int,
) -> str:
    end_column = start_column + _RACK_BLOCK_COLUMNS - 1
    sheet.merge_cells(
        start_row=title_row,
        start_column=start_column,
        end_row=title_row,
        end_column=end_column,
    )
    title = _cell(sheet, title_row, start_column)
    _literal_text(title, rack.rack_name)
    title.font = Font(name=_FONT_NAME, size=11, bold=True, color="172033")
    title.fill = PatternFill("solid", fgColor="F6C88F")
    title.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    title.border = _DEVICE_BORDER
    sheet.row_dimensions[title_row].height = max(
        float(sheet.row_dimensions[title_row].height or 0), 24.0
    )

    body_start = title_row + 1
    for offset in range(max_height):
        row = body_start + offset
        for column in range(start_column, end_column + 1):
            cell = _cell(sheet, row, column)
            cell.border = _GRID_BORDER
            cell.font = Font(name=_FONT_NAME, size=8, color="172033")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        sheet.row_dimensions[row].height = max(
            float(sheet.row_dimensions[row].height or 0), 22.0
        )

    for unit in range(rack.height_u, 0, -1):
        row = body_start + rack.height_u - unit
        for column in (start_column, end_column):
            cell = _cell(sheet, row, column)
            cell.value = unit
            cell.fill = PatternFill("solid", fgColor="FCE0B8")
            cell.font = Font(name=_FONT_NAME, size=8, color="172033")
            cell.alignment = Alignment(horizontal="center", vertical="center")
    if rack.height_u < max_height:
        for row in range(body_start + rack.height_u, body_start + max_height):
            for column in range(start_column, end_column + 1):
                _cell(sheet, row, column).fill = PatternFill("solid", fgColor="EEF1F5")
    return title.coordinate


def _render_rack_devices(
    sheet: Worksheet,
    rack: Rack,
    placements: list[tuple[Placement, Device]],
    *,
    start_column: int,
    body_start: int,
) -> None:
    for placement, device in placements:
        low = min(placement.start_u, placement.end_u)
        high = max(placement.start_u, placement.end_u)
        top_row = body_start + rack.height_u - high
        bottom_row = body_start + rack.height_u - low
        left_column = start_column + 1
        right_column = start_column + 2
        sheet.merge_cells(
            start_row=top_row,
            start_column=left_column,
            end_row=bottom_row,
            end_column=right_column,
        )
        anchor = _cell(sheet, top_row, left_column)
        text = _normalise_display_text(device.display_text)
        _literal_text(anchor, text)
        anchor.fill = _device_fill(device)
        anchor.border = _DEVICE_BORDER
        anchor.font = Font(name=_FONT_NAME, size=8, color="172033")
        anchor.alignment = Alignment(
            horizontal="left",
            vertical="center",
            wrap_text=True,
            shrink_to_fit=True,
        )
        if top_row == bottom_row:
            line_count = max(text.count("\n") + 1, 1)
            sheet.row_dimensions[top_row].height = max(
                float(sheet.row_dimensions[top_row].height or 0),
                min(72.0, line_count * 10.0 + 4.0),
            )


def _write_rack_sheet(
    workbook: Workbook,
    project: RackProject,
) -> tuple[tuple[str, str], ...]:
    sheet = workbook.active
    if sheet is None:
        raise RuntimeError("无法创建机柜图工作表。")
    sheet.title = _RACK_SHEET
    sheet.sheet_view.showGridLines = False
    sheet.sheet_properties.tabColor = "4472C4"
    _style_diagram_header(sheet)

    for block_index in range(_RACKS_PER_BAND):
        start_column = block_index * (_RACK_BLOCK_COLUMNS + _RACK_GUTTER_COLUMNS) + 1
        sheet.column_dimensions[get_column_letter(start_column)].width = 5
        sheet.column_dimensions[get_column_letter(start_column + 1)].width = 15
        sheet.column_dimensions[get_column_letter(start_column + 2)].width = 15
        sheet.column_dimensions[get_column_letter(start_column + 3)].width = 5
        if block_index < _RACKS_PER_BAND - 1:
            sheet.column_dimensions[get_column_letter(start_column + 4)].width = 2

    active_racks = [rack for rack in _ordered_racks(project) if rack.status == "active"]
    placements = _active_placements(project)
    groups: dict[str, list[Rack]] = {}
    for rack in active_racks:
        groups.setdefault(rack.source_sheet or "未命名工作表", []).append(rack)

    title_cells: list[tuple[str, str]] = []
    current_row = 4
    if not groups:
        empty_cell = _cell(sheet, current_row, 1)
        _literal_text(empty_cell, "当前项目没有可导出的在位机柜。")
        empty_cell.font = Font(name=_FONT_NAME, size=11, color="667085")
        current_row += 1
    for sheet_name, racks in groups.items():
        sheet.merge_cells(
            start_row=current_row,
            start_column=1,
            end_row=current_row,
            end_column=_DIAGRAM_MAX_COLUMN,
        )
        group_cell = _cell(sheet, current_row, 1)
        _literal_text(group_cell, f"来源工作表：{sheet_name}")
        group_cell.font = Font(name=_FONT_NAME, size=11, bold=True, color="344054")
        group_cell.fill = PatternFill("solid", fgColor="E9EEF5")
        group_cell.alignment = Alignment(horizontal="left", vertical="center")
        group_cell.border = Border(bottom=Side(style="thin", color="AAB4C3"))
        sheet.row_dimensions[current_row].height = 22
        current_row += 2

        for batch_start in range(0, len(racks), _RACKS_PER_BAND):
            batch = racks[batch_start : batch_start + _RACKS_PER_BAND]
            max_height = max(rack.height_u for rack in batch)
            title_row = current_row
            for block_index, rack in enumerate(batch):
                start_column = (
                    block_index * (_RACK_BLOCK_COLUMNS + _RACK_GUTTER_COLUMNS) + 1
                )
                coordinate = _style_rack_base(
                    sheet,
                    rack,
                    start_column=start_column,
                    title_row=title_row,
                    max_height=max_height,
                )
                title_cells.append((coordinate, rack.rack_name))
                _render_rack_devices(
                    sheet,
                    rack,
                    placements.get(rack.rack_id, []),
                    start_column=start_column,
                    body_start=title_row + 1,
                )
            current_row += max_height + 3

    sheet.freeze_panes = "A4"
    sheet.print_area = (
        f"A1:{get_column_letter(_DIAGRAM_MAX_COLUMN)}{max(current_row - 1, 4)}"
    )
    sheet.print_title_rows = "1:2"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    return tuple(title_cells)


def _write_position_sheet(
    workbook: Workbook,
    project: RackProject,
    rows: list[_PositionRow],
) -> None:
    sheet = workbook.create_sheet(_POSITION_SHEET)
    sheet.sheet_view.showGridLines = False
    sheet.sheet_properties.tabColor = "70AD47"
    _literal_text(sheet["A1"], _POSITION_SHEET)
    sheet["A1"].font = Font(name=_FONT_NAME, size=16, bold=True, color="172033")
    warning_count = len(project.conflicts)
    note = "按源工作表、机柜和 U 位排序；可直接使用标题行筛选。"
    if warning_count:
        note += f" 当前项目另有 {warning_count} 条异常提示，请在 RackTool 中核对。"
    _literal_text(sheet["A2"], note)
    sheet["A2"].font = Font(name=_FONT_NAME, size=10, italic=True, color="667085")

    header_row = 4
    for column, header in enumerate(_POSITION_HEADERS, start=1):
        cell = _cell(sheet, header_row, column)
        _literal_text(cell, header)
        cell.fill = PatternFill("solid", fgColor="344054")
        cell.font = Font(name=_FONT_NAME, size=10, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(right=Side(style="thin", color="FFFFFF"))
    sheet.row_dimensions[header_row].height = 24

    for output_index, row in enumerate(rows, start=1):
        excel_row = header_row + output_index
        values: tuple[str | int | None, ...] = (
            output_index,
            row.display_text,
            row.rack_name,
            row.start_u,
            row.end_u,
            row.height_u,
            row.sheet_name,
            row.source_range,
            row.status,
            row.device_id,
            row.rack_id,
        )
        for column, value in enumerate(values, start=1):
            cell = _cell(sheet, excel_row, column)
            if isinstance(value, str):
                _literal_text(cell, value)
            else:
                cell.value = value
            cell.font = Font(name=_FONT_NAME, size=10, color="172033")
            cell.alignment = Alignment(
                horizontal="left" if column in {2, 3, 7, 8, 9} else "center",
                vertical="top" if column == 2 else "center",
                wrap_text=True,
            )
            cell.border = Border(bottom=Side(style="thin", color="E4E8EF"))
        line_count = max(row.display_text.count("\n") + 1, 1)
        sheet.row_dimensions[excel_row].height = min(90.0, max(20.0, line_count * 15.0))

    last_row = header_row + max(len(rows), 1)
    if rows:
        table = Table(displayName="DevicePositionsTable", ref=f"A4:K{last_row}")
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        sheet.add_table(table)
    else:
        sheet.auto_filter.ref = "A4:K4"
        _literal_text(sheet["A5"], "当前项目没有设备记录。")
        sheet.merge_cells("A5:I5")
        sheet["A5"].font = Font(name=_FONT_NAME, size=10, italic=True, color="667085")

    widths = (7, 38, 18, 10, 10, 11, 18, 16, 18, 25, 25)
    for column, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    sheet.column_dimensions["J"].hidden = True
    sheet.column_dimensions["K"].hidden = True
    sheet.freeze_panes = "A5"
    sheet.print_title_rows = "4:4"
    sheet.print_area = f"A1:I{last_row}"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


def _build_workbook(project: RackProject) -> tuple[Workbook, _ExportManifest]:
    workbook = Workbook()
    try:
        workbook.properties.creator = "RackTool"
        workbook.properties.title = "RackTool 机柜图与设备位置表"
        workbook.properties.subject = "RackTool 标准导出"
        rows = _position_rows(project)
        rack_titles = _write_rack_sheet(workbook, project)
        _write_position_sheet(workbook, project, rows)
        workbook.active = 0
        return workbook, _ExportManifest(rack_titles, tuple(rows))
    except Exception:
        workbook.close()
        raise


def _validate_export(path: Path, manifest: _ExportManifest) -> None:
    workbook = load_workbook(path, read_only=False, data_only=False)
    try:
        if workbook.sheetnames != [_RACK_SHEET, _POSITION_SHEET]:
            raise ValueError("导出验证失败：工作表结构不完整。")
        rack_sheet = workbook[_RACK_SHEET]
        position_sheet = workbook[_POSITION_SHEET]
        headers = tuple(position_sheet.cell(4, column).value for column in range(1, 12))
        if headers != _POSITION_HEADERS:
            raise ValueError("导出验证失败：设备位置表标题不完整。")
        exported_text = tuple(
            position_sheet.cell(row, 2).value
            for row in range(5, 5 + len(manifest.position_rows))
        )
        expected_text = tuple(row.display_text for row in manifest.position_rows)
        if exported_text != expected_text:
            raise ValueError("导出验证失败：设备文字在保存后发生变化。")
        for coordinate, rack_name in manifest.rack_titles:
            if rack_sheet[coordinate].value != rack_name:
                raise ValueError("导出验证失败：机柜名称在保存后发生变化。")
        for sheet in workbook.worksheets:
            if any(cell.data_type == "f" for row in sheet.iter_rows() for cell in row):
                raise ValueError("导出验证失败：导出表中出现了意外公式。")
    finally:
        workbook.close()


def export_project_workbook(
    project: RackProject,
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Create a validated two-sheet XLSX export without touching the source workbook."""
    errors = project_error_conflicts(project)
    if errors:
        raise ValueError("项目数据仍有未解决错误，请先在“异常”页处理后再导出。")
    destination = _normalise_destination(path, project)
    if destination.exists():
        if destination.is_dir():
            raise IsADirectoryError(destination)
        if not overwrite:
            raise FileExistsError("导出文件已存在；请换一个文件名，或明确允许覆盖。")
    destination.parent.mkdir(parents=True, exist_ok=True)
    workbook, manifest = _build_workbook(project)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{destination.stem}.tmp-",
        suffix=".xlsx",
        dir=destination.parent,
        delete=False,
    ) as temp_handle:
        temp_path = Path(temp_handle.name)
    try:
        workbook.save(temp_path)
        workbook.close()
        _validate_export(temp_path, manifest)
        os.replace(temp_path, destination)
    except Exception:
        workbook.close()
        if temp_path.exists():
            temp_path.unlink()
        raise
    return destination
