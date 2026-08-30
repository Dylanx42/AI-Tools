from __future__ import annotations

import os
from copy import copy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import range_boundaries
from openpyxl.workbook import Workbook as OpenpyxlWorkbook

from racktool.core.backup import create_backup, create_temp_copy
from racktool.core.project import rescan_workbook
from racktool.models.domain import Device, Placement, Rack
from racktool.models.project import IdentityConflict, RackProject, SourceMapping

WriteStatus = Literal["applied", "rejected", "failed"]


@dataclass(frozen=True, slots=True)
class WriteAction:
    device_id: str
    rack_id: str
    sheet_name: str
    old_range: str
    new_range: str
    start_u: int
    end_u: int
    display_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WritePlan:
    actions: tuple[WriteAction, ...]
    conflicts: tuple[IdentityConflict, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "actions": [item.to_dict() for item in self.actions],
            "conflicts": [item.to_dict() for item in self.conflicts],
        }


@dataclass(frozen=True, slots=True)
class WriteResult:
    status: WriteStatus
    plan: WritePlan
    backup_path: str | None = None
    output_path: str | None = None
    project: RackProject | None = None
    message: str = ""
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["plan"] = self.plan.to_dict()
        if self.project is not None:
            payload["project"] = self.project.to_dict()
        return payload


def _device(project: RackProject, device_id: str) -> Device:
    return next(item for item in project.devices if item.device_id == device_id)


def _rack(project: RackProject, rack_id: str) -> Rack:
    return next(item for item in project.racks if item.rack_id == rack_id)


def _placement(project: RackProject, device_id: str) -> Placement:
    return next(
        item
        for item in project.placements
        if item.device_id == device_id and item.status == "active"
    )


def _mapping(project: RackProject, device_id: str) -> SourceMapping:
    return next(
        item
        for item in project.mappings
        if item.mapping_kind == "device" and item.device_id == device_id
    )


def _u_range(start_u: int, end_u: int) -> range:
    return range(min(start_u, end_u), max(start_u, end_u) + 1)


def _occupied_units(project: RackProject, rack_id: str, exclude_device_id: str) -> set[int]:
    occupied: set[int] = set()
    for placement in project.placements:
        if placement.status != "active" or placement.rack_id != rack_id:
            continue
        if placement.device_id == exclude_device_id:
            continue
        occupied.update(_u_range(placement.start_u, placement.end_u))
    return occupied


def _range_from_u(rack: Rack, start_u: int, end_u: int) -> str:
    if not rack.device_columns:
        raise ValueError(f"Rack {rack.rack_id} has no device columns")
    column = rack.device_columns[0]
    rows = [rack.u_to_row[unit] for unit in _u_range(start_u, end_u)]
    min_row, max_row = min(rows), max(rows)
    start = f"{get_column_letter(column)}{min_row}"
    end = f"{get_column_letter(column)}{max_row}"
    return start if min_row == max_row else f"{start}:{end}"


def plan_device_move(
    project: RackProject,
    device_id: str,
    rack_id: str,
    start_u: int,
    end_u: int,
) -> WritePlan:
    conflicts: list[IdentityConflict] = []
    try:
        device = _device(project, device_id)
        rack = _rack(project, rack_id)
        mapping = _mapping(project, device_id)
    except StopIteration:
        conflicts.append(
            IdentityConflict(
                code="unknown-entity",
                severity="error",
                message="Device, rack, or mapping is missing",
                entity_ids=[device_id, rack_id],
            )
        )
        return WritePlan(actions=(), conflicts=tuple(conflicts))

    if start_u < 1 or end_u < 1 or start_u > rack.height_u or end_u > rack.height_u:
        conflicts.append(
            IdentityConflict(
                code="u-out-of-bounds",
                severity="error",
                message=f"Target U {start_u}-{end_u} is outside 1-{rack.height_u}",
                entity_ids=[device_id, rack_id],
            )
        )
    missing_u = [unit for unit in _u_range(start_u, end_u) if unit not in rack.u_to_row]
    if missing_u:
        conflicts.append(
            IdentityConflict(
                code="u-axis-gap",
                severity="error",
                message=f"Rack {rack_id} is missing U rows for {missing_u}",
                entity_ids=[device_id, rack_id],
            )
        )
    occupied = _occupied_units(project, rack_id, device_id)
    overlap = occupied.intersection(_u_range(start_u, end_u))
    if overlap:
        conflicts.append(
            IdentityConflict(
                code="target-u-occupied",
                severity="error",
                message=f"Target U {sorted(overlap)} is already occupied",
                entity_ids=[device_id, rack_id],
            )
        )
    if mapping.sheet_name != rack.source_sheet:
        conflicts.append(
            IdentityConflict(
                code="cross-sheet-move-unsupported",
                severity="error",
                message="V0.4 only writes moves inside the current source Sheet",
                entity_ids=[device_id, rack_id],
            )
        )
    if conflicts:
        return WritePlan(actions=(), conflicts=tuple(conflicts))

    action = WriteAction(
        device_id=device_id,
        rack_id=rack_id,
        sheet_name=mapping.sheet_name,
        old_range=mapping.source_range,
        new_range=_range_from_u(rack, start_u, end_u),
        start_u=min(start_u, end_u),
        end_u=max(start_u, end_u),
        display_text=device.display_text,
    )
    return WritePlan(actions=(action,), conflicts=())


def _copy_style(source_cell: Any, target_cell: Any) -> None:
    target_cell.font = copy(source_cell.font)
    target_cell.fill = copy(source_cell.fill)
    target_cell.alignment = copy(source_cell.alignment)
    target_cell.border = copy(source_cell.border)
    target_cell.number_format = source_cell.number_format
    target_cell.protection = copy(source_cell.protection)


def _apply_action(workbook: OpenpyxlWorkbook, action: WriteAction) -> None:
    sheet = workbook[action.sheet_name]
    old_min_col, old_min_row, old_max_col, old_max_row = range_boundaries(action.old_range)
    new_min_col, new_min_row, new_max_col, new_max_row = range_boundaries(action.new_range)
    if (
        old_min_col is None
        or old_min_row is None
        or old_max_col is None
        or old_max_row is None
        or new_min_col is None
        or new_min_row is None
        or new_max_col is None
        or new_max_row is None
    ):
        raise ValueError(f"Invalid write range: {action.old_range} -> {action.new_range}")

    old_anchor = sheet.cell(old_min_row, old_min_col)
    new_anchor = sheet.cell(new_min_row, new_min_col)
    value = old_anchor.value if old_anchor.value not in (None, "") else action.display_text

    old_merged = [
        item
        for item in list(sheet.merged_cells.ranges)
        if str(item) == action.old_range or str(item).replace("$", "") == action.old_range
    ]
    for item in old_merged:
        sheet.unmerge_cells(str(item))

    overlapping_new = [
        item
        for item in list(sheet.merged_cells.ranges)
        if not (
            item.max_col < new_min_col
            or item.min_col > new_max_col
            or item.max_row < new_min_row
            or item.min_row > new_max_row
        )
    ]
    for item in overlapping_new:
        sheet.unmerge_cells(str(item))

    _copy_style(old_anchor, new_anchor)
    new_anchor.value = value

    if new_min_row != new_max_row or new_min_col != new_max_col:
        sheet.merge_cells(
            start_row=new_min_row,
            start_column=new_min_col,
            end_row=new_max_row,
            end_column=new_max_col,
        )

    if action.old_range != action.new_range:
        for row in range(old_min_row, old_max_row + 1):
            for column in range(old_min_col, old_max_col + 1):
                if row == new_min_row and column == new_min_col:
                    continue
                cell = sheet.cell(row, column)
                cell.value = None


def _validate_written_workbook(path: Path, project: RackProject, plan: WritePlan) -> RackProject:
    rescanned = rescan_workbook(path, project).project
    error_conflicts = [item for item in rescanned.conflicts if item.severity == "error"]
    if error_conflicts:
        raise ValueError("; ".join(item.message for item in error_conflicts))
    for action in plan.actions:
        placement = _placement(rescanned, action.device_id)
        mapping = _mapping(rescanned, action.device_id)
        if placement.rack_id != action.rack_id:
            raise ValueError(f"Device {action.device_id} did not stay on the target rack")
        if placement.start_u != action.start_u or placement.end_u != action.end_u:
            raise ValueError(f"Device {action.device_id} did not land on the target U range")
        if mapping.source_range != action.new_range:
            raise ValueError(f"Device {action.device_id} mapping was not updated")
        device = _device(rescanned, action.device_id)
        if device.display_text != action.display_text:
            raise ValueError(f"Device {action.device_id} display text was not preserved")
    return rescanned


def apply_writeback(
    workbook_path: Path,
    project: RackProject,
    plan: WritePlan,
    *,
    replace_source: bool = True,
) -> WriteResult:
    source = workbook_path.expanduser().resolve()
    original = source.read_bytes()
    if plan.conflicts:
        return WriteResult(
            status="rejected",
            plan=plan,
            output_path=str(source),
            message="Write refused because the plan has conflicts",
            errors=tuple(item.message for item in plan.conflicts),
        )
    if not plan.actions:
        return WriteResult(
            status="applied",
            plan=plan,
            output_path=str(source),
            project=project,
            message="No workbook changes were required",
        )

    backup_path = create_backup(source)
    temp_path = create_temp_copy(source)
    try:
        workbook = load_workbook(temp_path)
        try:
            existing_sheets = [sheet.title for sheet in workbook.worksheets]
            for action in plan.actions:
                _apply_action(workbook, action)
            if [sheet.title for sheet in workbook.worksheets] != existing_sheets:
                raise ValueError("Write-back tried to change the workbook sheet list")
            workbook.save(temp_path)
        finally:
            workbook.close()

        reloaded = load_workbook(temp_path)
        reloaded.close()
        updated_project = _validate_written_workbook(temp_path, project, plan)
        if replace_source:
            os.replace(temp_path, source)
            output = source
        else:
            output = temp_path
        if source.read_bytes() == original and replace_source:
            raise ValueError("Write-back did not change the target after a non-empty plan")
        return WriteResult(
            status="applied",
            plan=plan,
            backup_path=str(backup_path),
            output_path=str(output),
            project=updated_project,
            message="Write-back applied after backup, temporary write, reload, and validation",
        )
    except Exception as error:  # noqa: BLE001
        if temp_path.exists() and temp_path != source:
            temp_path.unlink()
        if source.read_bytes() != original:
            source.write_bytes(original)
        return WriteResult(
            status="failed",
            plan=plan,
            backup_path=str(backup_path),
            output_path=str(source),
            message="Write-back aborted; the original workbook was left unchanged",
            errors=(str(error),),
        )
