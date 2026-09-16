from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from racktool.core.backup import list_backups
from racktool.core.export import export_project_workbook
from racktool.core.identity import normalize_path
from racktool.core.service import (
    commit_write_plan,
    import_project,
    load_project_state,
    prepare_default_project_database,
    rescan_project,
    restore_project_backup,
)
from racktool.core.storage import (
    cleanup_application_storage,
    default_project_database_path,
    migrate_legacy_workbook_backups,
)
from racktool.core.sync import (
    MoveRequest,
    WritePlan,
    WriteResult,
    plan_device_move,
    plan_device_moves,
)
from racktool.core.workbook import scan_workbook
from racktool.gui.presentation import cell_display_text, friendly_issue
from racktool.models.project import IdentityConflict, RackProject
from racktool.models.workbook import WorkbookInfo

_A1_PATTERN = re.compile(r"^\$?([A-Za-z]+)\$?(\d+)(?::\$?([A-Za-z]+)\$?(\d+))?$")


def _natural_key(value: Any) -> tuple[tuple[int, Any], ...]:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", str(value))
        if part
    )


def _column_index(letters: str) -> int:
    value = 0
    for character in letters.upper():
        value = value * 26 + ord(character) - ord("A") + 1
    return value


def _a1_bounds(a1: str) -> tuple[int, int, int, int]:
    match = _A1_PATTERN.fullmatch(a1.strip())
    if match is None:
        raise ValueError(f"Unsupported cell range: {a1}")
    min_col = _column_index(match.group(1))
    min_row = int(match.group(2))
    max_col = _column_index(match.group(3) or match.group(1))
    max_row = int(match.group(4) or match.group(2))
    return min_col, min_row, max_col, max_row


def _bounds_overlap(
    left: tuple[int, int, int, int],
    right: tuple[int, int, int, int],
) -> bool:
    return not (
        left[2] < right[0] or right[2] < left[0] or left[3] < right[1] or right[3] < left[1]
    )


def default_database_path(workbook: Path) -> Path:
    return default_project_database_path(workbook)


@dataclass
class GuiSession:
    workbook_path: Path
    database_path: Path
    project: RackProject
    last_plan: WritePlan | None = None
    last_result: WriteResult | None = None
    last_rescan_conflicts: tuple[IdentityConflict, ...] = ()
    status_message: str = ""
    history: list[str] = field(default_factory=list)
    pending_moves: list[MoveRequest] = field(default_factory=list)
    workbook_info: WorkbookInfo | None = field(default=None, repr=False)

    @classmethod
    def open_workbook(cls, workbook: Path, database: Path | None = None) -> GuiSession:
        workbook_path = normalize_path(workbook)
        migration_message: str | None = None
        if database is None:
            database_path, migration_message = prepare_default_project_database(workbook_path)
        else:
            database_path = normalize_path(database)
        if database_path.is_file():
            session = cls.open_project(database_path, workbook_path)
            session.status_message = "已打开已有项目"
            if migration_message:
                session.status_message += f"；{migration_message}"
            session.history.append(session.status_message)
            return session
        project = import_project(workbook_path, database_path)
        session = cls(
            workbook_path, database_path, project, status_message="已打开工作簿并创建项目"
        )
        if migration_message:
            session.status_message += f"；{migration_message}"
        session.history.append(session.status_message)
        return session

    @classmethod
    def open_project(cls, database: Path, workbook: Path | None = None) -> GuiSession:
        try:
            cleanup_application_storage()
        except OSError:
            pass
        database_path = normalize_path(database)
        project = load_project_state(database_path)
        workbook_path = Path(workbook or project.source_workbook or "").expanduser()
        if workbook is not None:
            workbook_path = normalize_path(workbook)
        elif project.source_workbook:
            workbook_path = normalize_path(Path(project.source_workbook))
        else:
            raise ValueError("Project does not record a source workbook")
        if not workbook_path.is_file():
            raise FileNotFoundError(workbook_path)
        if project.source_workbook is None:
            raise ValueError("Project does not record a source workbook")
        bound_source = normalize_path(Path(project.source_workbook))
        if workbook_path != bound_source:
            raise ValueError("Selected workbook is not the source bound to this project")
        try:
            migrate_legacy_workbook_backups(workbook_path)
        except OSError:
            pass
        session = cls(workbook_path, database_path, project, status_message="已打开项目")
        session.history.append(session.status_message)
        return session

    def device_rows(self) -> list[dict[str, Any]]:
        racks = {rack.rack_id: rack for rack in self.project.racks}
        mappings = {
            item.device_id: item
            for item in self.project.mappings
            if item.mapping_kind == "device" and item.device_id is not None
        }
        placements = {item.device_id: item for item in self.project.placements}
        rows: list[dict[str, Any]] = []
        for source_index, device in enumerate(self.project.devices):
            placement = placements.get(device.device_id)
            mapping = mappings.get(device.device_id)
            rack = racks.get(placement.rack_id) if placement is not None else None
            display_text = cell_display_text(device.display_text)
            text_lines = [line.strip() for line in display_text.splitlines() if line.strip()]
            primary_label = device.canonical_name or (text_lines[0] if text_lines else "未命名设备")
            rows.append(
                {
                    "device_id": device.device_id,
                    "display_text": display_text,
                    "primary_label": primary_label,
                    "attributes": dict(device.attributes),
                    "rack_id": placement.rack_id if placement is not None else "",
                    "rack_name": rack.rack_name if rack is not None else "",
                    "start_u": placement.start_u if placement is not None else None,
                    "end_u": placement.end_u if placement is not None else None,
                    "height_u": placement.height_u if placement is not None else None,
                    "status": placement.status if placement is not None else "unplaced",
                    "sheet_name": mapping.sheet_name if mapping is not None else "",
                    "source_range": mapping.source_range if mapping is not None else "",
                    "style_signature": device.style_signature or "",
                    "source_index": source_index,
                }
            )
        return rows

    def device_page(
        self,
        query: str = "",
        *,
        rack_id: str | None = None,
        status_filter: str | None = None,
        height_filter: str | None = None,
        sort_by: str = "source",
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        if offset < 0:
            raise ValueError("Device page offset cannot be negative")
        if limit < 1 or limit > 100:
            raise ValueError("Device page limit must be between 1 and 100")
        needle = query.strip().casefold()
        rows = []
        for row in self.device_rows():
            if rack_id is not None and row["rack_id"] != rack_id:
                continue
            if status_filter not in (None, "", "all"):
                if status_filter == "active" and row["status"] != "active":
                    continue
                if status_filter == "attention" and row["status"] == "active":
                    continue
                if status_filter not in {"active", "attention"} and row["status"] != status_filter:
                    continue
            height = row["height_u"]
            if height_filter not in (None, "", "all"):
                if height_filter == "1u" and height != 1:
                    continue
                if height_filter == "2-4u" and not (isinstance(height, int) and 2 <= height <= 4):
                    continue
                if height_filter == "5u-plus" and not (isinstance(height, int) and height >= 5):
                    continue
            searchable = " ".join(
                str(row[key])
                for key in (
                    "display_text",
                    "primary_label",
                    "rack_name",
                    "sheet_name",
                    "start_u",
                    "end_u",
                )
            ).casefold()
            if needle and needle not in searchable:
                continue
            rows.append(row)
        if sort_by == "name":
            rows.sort(key=lambda row: (_natural_key(row["primary_label"]), row["source_index"]))
        elif sort_by == "rack-u":
            rows.sort(
                key=lambda row: (
                    _natural_key(row["rack_name"]),
                    -(int(row["end_u"]) if row["end_u"] is not None else -1),
                    row["source_index"],
                )
            )
        elif sort_by != "source":
            raise ValueError(f"Unsupported device sort: {sort_by}")
        return rows[offset : offset + limit], len(rows)

    def rack_rows(self, sort_by: str = "source") -> list[dict[str, Any]]:
        occupancy = {rack.rack_id: 0 for rack in self.project.racks}
        device_counts = {rack.rack_id: 0 for rack in self.project.racks}
        for placement in self.project.placements:
            if placement.status == "active":
                occupancy[placement.rack_id] = (
                    occupancy.get(placement.rack_id, 0) + placement.height_u
                )
                device_counts[placement.rack_id] = device_counts.get(placement.rack_id, 0) + 1
        sheet_order: dict[str, int] = {}
        for rack in self.project.racks:
            sheet_order.setdefault(rack.source_sheet or "", len(sheet_order))
        rows = [
            {
                "rack_id": rack.rack_id,
                "rack_name": rack.rack_name,
                "sheet_name": rack.source_sheet or "",
                "height_u": rack.height_u,
                "occupied_u": occupancy.get(rack.rack_id, 0),
                "available_u": max(rack.height_u - occupancy.get(rack.rack_id, 0), 0),
                "occupancy_percent": round(occupancy.get(rack.rack_id, 0) / rack.height_u * 100),
                "device_count": device_counts.get(rack.rack_id, 0),
                "title_range": rack.title_range or "",
                "status": rack.status,
                "source_row": rack.bounds.min_row if rack.bounds is not None else 10**9,
                "source_column": rack.bounds.min_col if rack.bounds is not None else 10**9,
                "source_index": index,
            }
            for index, rack in enumerate(self.project.racks)
        ]
        if sort_by == "source":
            rows.sort(
                key=lambda row: (
                    sheet_order.get(str(row["sheet_name"]), 10**9),
                    row["source_row"],
                    row["source_column"],
                    row["source_index"],
                )
            )
        elif sort_by == "name":
            rows.sort(key=lambda row: (_natural_key(row["rack_name"]), row["source_index"]))
        elif sort_by == "occupancy":
            rows.sort(
                key=lambda row: (
                    -int(str(row["occupancy_percent"])),
                    _natural_key(row["rack_name"]),
                )
            )
        else:
            raise ValueError(f"Unsupported rack sort: {sort_by}")
        return rows

    def occupancy_segments(self, rack_id: str) -> list[dict[str, Any]]:
        devices = {device.device_id: device for device in self.project.devices}
        segments: list[dict[str, Any]] = []
        for placement in self.project.placements:
            if placement.rack_id != rack_id or placement.status != "active":
                continue
            device = devices[placement.device_id]
            display_text = cell_display_text(device.display_text)
            text_lines = [line.strip() for line in display_text.splitlines() if line.strip()]
            segments.append(
                {
                    "device_id": device.device_id,
                    "display_text": display_text,
                    "primary_label": (
                        device.canonical_name or (text_lines[0] if text_lines else "未命名设备")
                    ),
                    "start_u": min(placement.start_u, placement.end_u),
                    "end_u": max(placement.start_u, placement.end_u),
                    "height_u": placement.height_u,
                    "style_signature": device.style_signature or "",
                }
            )
        return sorted(
            segments,
            key=lambda item: (-int(item["end_u"]), str(item["primary_label"])),
        )

    def occupancy_rows(self, rack_id: str) -> list[dict[str, Any]]:
        rack = next(item for item in self.project.racks if item.rack_id == rack_id)
        devices = {device.device_id: device for device in self.project.devices}
        by_u: dict[int, str] = {}
        for placement in self.project.placements:
            if placement.rack_id != rack_id or placement.status != "active":
                continue
            device = devices[placement.device_id]
            for unit in range(
                min(placement.start_u, placement.end_u), max(placement.start_u, placement.end_u) + 1
            ):
                by_u[unit] = device.display_text
        return [
            {"u": unit, "display_text": cell_display_text(by_u.get(unit, ""))}
            for unit in range(rack.height_u, 0, -1)
        ]

    def mapping_rows(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.project.mappings]

    def conflict_rows(self) -> list[dict[str, Any]]:
        rows = [item.to_dict() for item in self.project.conflicts]
        if self.last_plan is not None:
            rows.extend(item.to_dict() for item in self.last_plan.conflicts)
        if self.last_result is not None and self.last_result.plan != self.last_plan:
            rows.extend(item.to_dict() for item in self.last_result.plan.conflicts)
        rows.extend(item.to_dict() for item in self.last_rescan_conflicts)
        return rows

    def _issue_locations(self, row: dict[str, Any]) -> list[str]:
        locations: list[str] = []

        def add(sheet_name: str, source_range: str) -> None:
            cleaned_range = source_range.replace("$", "").strip()
            if not cleaned_range or _A1_PATTERN.fullmatch(cleaned_range) is None:
                return
            if sheet_name:
                if cleaned_range in locations:
                    locations.remove(cleaned_range)
                label = f"{sheet_name} · {cleaned_range}"
            else:
                if any(item.endswith(f" · {cleaned_range}") for item in locations):
                    return
                label = cleaned_range
            if label not in locations:
                locations.append(label)

        for evidence in row.get("evidence", []):
            text = str(evidence).strip()
            if "!" in text:
                sheet_name, source_range = text.rsplit("!", 1)
                add(sheet_name, source_range)
            else:
                add("", text)

        mapping_by_id = {item.mapping_id: item for item in self.project.mappings}
        mappings_by_device: dict[str, list[Any]] = {}
        mappings_by_rack: dict[str, list[Any]] = {}
        for mapping in self.project.mappings:
            if mapping.device_id is not None:
                mappings_by_device.setdefault(mapping.device_id, []).append(mapping)
            if mapping.rack_id is not None:
                mappings_by_rack.setdefault(mapping.rack_id, []).append(mapping)
        rack_by_id = {item.rack_id: item for item in self.project.racks}
        placement_by_id = {item.placement_id: item for item in self.project.placements}

        identifiers = [
            str(item)
            for item in (*row.get("entity_ids", []), *row.get("candidate_refs", []))
            if str(item)
        ]
        for identifier in identifiers:
            resolved_mapping = mapping_by_id.get(identifier)
            if resolved_mapping is not None:
                add(resolved_mapping.sheet_name, resolved_mapping.source_range)
            for device_mapping in mappings_by_device.get(identifier, []):
                add(device_mapping.sheet_name, device_mapping.source_range)
            for rack_mapping in mappings_by_rack.get(identifier, []):
                add(rack_mapping.sheet_name, rack_mapping.source_range)
            rack = rack_by_id.get(identifier)
            if rack is not None and rack.source_sheet and rack.title_range:
                add(rack.source_sheet, rack.title_range)
            placement = placement_by_id.get(identifier)
            if placement is not None:
                for device_mapping in mappings_by_device.get(placement.device_id, []):
                    add(device_mapping.sheet_name, device_mapping.source_range)
        return locations

    def issue_rows(self) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for row in self.conflict_rows():
            code = str(row.get("code", "unknown"))
            severity = str(row.get("severity", "warning"))
            message = str(row.get("message", ""))
            copy = friendly_issue(code, message, severity)
            key = (severity, code, copy["title"], copy["guidance"])
            group = grouped.setdefault(
                key,
                {
                    "severity": severity,
                    "level": copy["level"],
                    "title": copy["title"],
                    "guidance": copy["guidance"],
                    "item_count": 0,
                    "locations": [],
                    "technical_details": [],
                },
            )
            group["item_count"] += 1
            for location in self._issue_locations(row):
                if location not in group["locations"]:
                    group["locations"].append(location)
            technical = copy["technical_detail"]
            evidence = [str(item) for item in row.get("evidence", []) if str(item)]
            if evidence:
                technical += "\n来源位置: " + "；".join(evidence)
            group["technical_details"].append(technical)
        rows = []
        for group in grouped.values():
            locations = list(group["locations"])
            count = len(locations) or int(group["item_count"])
            title = str(group["title"])
            if count > 1:
                title = f"{title}（{count} 处）"
            technical_details = list(group["technical_details"])
            rows.append(
                {
                    "severity": group["severity"],
                    "level": group["level"],
                    "title": title,
                    "guidance": group["guidance"],
                    "count": count,
                    "locations": locations,
                    "location": (
                        "\n".join(locations)
                        if locations
                        else "项目级问题（没有单一单元格位置）"
                    ),
                    "technical_detail": "\n".join(technical_details),
                }
            )
        rows.sort(
            key=lambda row: (
                0 if row["severity"] == "error" else 1,
                _natural_key(row["title"]),
            )
        )
        return rows

    def _workbook_info(self) -> WorkbookInfo:
        if self.workbook_info is None:
            self.workbook_info = scan_workbook(self.workbook_path)
        return self.workbook_info

    def overview_sheet_names(self) -> list[str]:
        rack_sheets = {
            rack.source_sheet for rack in self.project.racks if rack.source_sheet is not None
        }
        return [sheet.name for sheet in self._workbook_info().sheets if sheet.name in rack_sheets]

    def overview_sheet(self, sheet_name: str) -> dict[str, Any]:
        sheet = next(
            (item for item in self._workbook_info().sheets if item.name == sheet_name),
            None,
        )
        if sheet is None:
            raise ValueError(f"Workbook does not contain sheet: {sheet_name}")

        cell_by_position = {}
        for cell in sheet.cells:
            try:
                cell_bounds = _a1_bounds(cell.coordinate)
            except ValueError:
                continue
            cell_by_position[(cell_bounds[0], cell_bounds[1])] = cell
        rack_models = [
            rack
            for rack in self.project.racks
            if rack.source_sheet == sheet_name and rack.bounds is not None
        ]
        rack_bounds = [
            (rack.bounds.min_col, rack.bounds.min_row, rack.bounds.max_col, rack.bounds.max_row)
            for rack in rack_models
            if rack.bounds is not None
        ]
        device_rows = [row for row in self.device_rows() if row["sheet_name"] == sheet_name]
        devices_by_rack: dict[str, list[dict[str, Any]]] = {}
        for row in device_rows:
            if not row["source_range"]:
                continue
            try:
                source_bounds = _a1_bounds(str(row["source_range"]))
            except ValueError:
                continue
            devices_by_rack.setdefault(str(row["rack_id"]), []).append(
                {**row, "source_bounds": source_bounds}
            )

        merged_anchors: set[str] = set()
        context_blocks: list[dict[str, Any]] = []
        for merged_range in sheet.merged_ranges:
            try:
                bounds = _a1_bounds(merged_range)
            except ValueError:
                continue
            min_col, min_row, _max_col, _max_row = bounds
            anchor = cell_by_position.get((min_col, min_row))
            if anchor is None or anchor.value in (None, ""):
                continue
            merged_anchors.add(anchor.coordinate)
            if any(_bounds_overlap(bounds, rack_bound) for rack_bound in rack_bounds):
                continue
            context_blocks.append(
                {
                    "source_range": merged_range,
                    "source_bounds": bounds,
                    "display_text": cell_display_text(str(anchor.value)),
                    "style_signature": anchor.style_signature,
                }
            )

        for cell in sheet.cells:
            if len(context_blocks) >= 500:
                break
            if cell.coordinate in merged_anchors or cell.value in (None, ""):
                continue
            try:
                bounds = _a1_bounds(cell.coordinate)
            except ValueError:
                continue
            if any(_bounds_overlap(bounds, rack_bound) for rack_bound in rack_bounds):
                continue
            context_blocks.append(
                {
                    "source_range": cell.coordinate,
                    "source_bounds": bounds,
                    "display_text": cell_display_text(str(cell.value)),
                    "style_signature": cell.style_signature,
                }
            )

        racks = []
        for rack in rack_models:
            assert rack.bounds is not None
            racks.append(
                {
                    "rack_id": rack.rack_id,
                    "rack_name": rack.rack_name,
                    "height_u": rack.height_u,
                    "status": rack.status,
                    "bounds": (
                        rack.bounds.min_col,
                        rack.bounds.min_row,
                        rack.bounds.max_col,
                        rack.bounds.max_row,
                    ),
                    "title_bounds": (_a1_bounds(rack.title_range) if rack.title_range else None),
                    "u_to_row": dict(rack.u_to_row),
                    "device_columns": list(rack.device_columns),
                    "devices": devices_by_rack.get(rack.rack_id, []),
                }
            )

        extent_bounds: list[tuple[int, int, int, int]] = list(rack_bounds)
        extent_bounds.extend(block["source_bounds"] for block in context_blocks)
        if sheet.used_range:
            try:
                extent_bounds.append(_a1_bounds(sheet.used_range))
            except ValueError:
                pass
        max_column = max((bounds[2] for bounds in extent_bounds), default=1)
        max_row = max((bounds[3] for bounds in extent_bounds), default=1)
        return {
            "name": sheet.name,
            "index": sheet.index,
            "max_column": max_column,
            "max_row": max_row,
            "default_row_height": float(sheet.default_row_height or 15.0),
            "default_column_width": float(sheet.default_column_width or 8.43),
            "row_heights": {int(key): value for key, value in sheet.row_heights.items()},
            "column_widths": {
                _column_index(key): value for key, value in sheet.column_widths.items()
            },
            "racks": racks,
            "context_blocks": context_blocks,
            "context_truncated": len(context_blocks) >= 500,
        }

    def preview_staged_move(
        self,
        device_id: str,
        rack_id: str,
        start_u: int,
        end_u: int,
    ) -> WritePlan:
        candidate = MoveRequest(
            device_id=device_id,
            rack_id=rack_id,
            start_u=min(start_u, end_u),
            end_u=max(start_u, end_u),
        )
        moves = [item for item in self.pending_moves if item.device_id != device_id]
        moves.append(candidate)
        plan = plan_device_moves(
            self.project,
            moves,
            workbook_path=self.workbook_path,
        )
        self.last_plan = plan
        return plan

    def stage_move(
        self,
        device_id: str,
        rack_id: str,
        start_u: int,
        end_u: int,
    ) -> WritePlan:
        plan = self.preview_staged_move(device_id, rack_id, start_u, end_u)
        if plan.conflicts:
            self.status_message = plan.conflicts[0].message
            self.history.append(self.status_message)
            return plan

        replacement = MoveRequest(
            device_id=device_id,
            rack_id=rack_id,
            start_u=min(start_u, end_u),
            end_u=max(start_u, end_u),
        )
        self.pending_moves = [item for item in self.pending_moves if item.device_id != device_id]
        if any(action.device_id == device_id for action in plan.actions):
            self.pending_moves.append(replacement)
            self.status_message = f"已加入待同步（共 {len(self.pending_moves)} 项）"
        else:
            self.status_message = "目标位置未变化，未加入待同步"
        self.history.append(self.status_message)
        return plan

    def remove_pending_move(self, device_id: str) -> None:
        before = len(self.pending_moves)
        self.pending_moves = [item for item in self.pending_moves if item.device_id != device_id]
        if len(self.pending_moves) != before:
            self.last_plan = None
            self.status_message = f"已移除待同步项（剩余 {len(self.pending_moves)} 项）"
            self.history.append(self.status_message)

    def clear_pending_moves(self) -> None:
        self.pending_moves.clear()
        self.last_plan = None
        self.status_message = "已清空待同步更改"
        self.history.append(self.status_message)

    def pending_rows(self) -> list[dict[str, Any]]:
        devices = {row["device_id"]: row for row in self.device_rows()}
        racks = {row["rack_id"]: row for row in self.rack_rows()}
        rows: list[dict[str, Any]] = []
        for move in self.pending_moves:
            device = devices.get(move.device_id, {})
            target_rack = racks.get(move.rack_id, {})
            rows.append(
                {
                    "device_id": move.device_id,
                    "primary_label": device.get("primary_label", "未知设备"),
                    "display_text": device.get("display_text", "未知设备"),
                    "source_rack_name": device.get("rack_name", ""),
                    "source_start_u": device.get("start_u"),
                    "source_end_u": device.get("end_u"),
                    "target_rack_id": move.rack_id,
                    "target_rack_name": target_rack.get("rack_name", "未知机柜"),
                    "target_start_u": move.start_u,
                    "target_end_u": move.end_u,
                }
            )
        return rows

    def apply_pending_moves(self) -> WriteResult:
        if not self.pending_moves:
            raise ValueError("No pending moves to apply")
        plan = plan_device_moves(
            self.project,
            self.pending_moves,
            workbook_path=self.workbook_path,
        )
        self.last_plan = plan
        if plan.conflicts:
            result = WriteResult(
                status="rejected",
                plan=plan,
                output_path=str(self.workbook_path),
                project=self.project,
                message="写回被拒绝：待同步计划存在冲突",
                errors=tuple(item.message for item in plan.conflicts),
            )
        else:
            result = commit_write_plan(
                self.workbook_path,
                self.database_path,
                plan,
            )
        self.last_result = result
        if result.status == "applied" and result.project is not None:
            self.project = result.project
            self.workbook_info = None
            self.pending_moves.clear()
            self.last_plan = None
            self.status_message = result.message
        else:
            self.status_message = result.message or "写回被拒绝"
        self.history.append(self.status_message)
        return result

    def plan_move(self, device_id: str, rack_id: str, start_u: int, end_u: int) -> WritePlan:
        plan = plan_device_move(
            self.project,
            device_id,
            rack_id,
            start_u,
            end_u,
            workbook_path=self.workbook_path,
        )
        self.last_plan = plan
        if plan.conflicts:
            self.status_message = plan.conflicts[0].message
        else:
            self.status_message = f"可以移动到 {start_u}-{end_u}U"
        self.history.append(self.status_message)
        return plan

    def apply_move(self) -> WriteResult:
        if self.last_plan is None:
            raise ValueError("No move has been planned")
        result = commit_write_plan(
            self.workbook_path,
            self.database_path,
            self.last_plan,
        )
        self.last_result = result
        if result.status == "applied" and result.project is not None:
            self.project = result.project
            self.workbook_info = None
            self.pending_moves.clear()
            self.last_plan = None
            self.status_message = result.message
        else:
            self.status_message = result.message or "写回被拒绝"
        self.history.append(self.status_message)
        return result

    def rescan(self) -> RackProject:
        result = rescan_project(self.workbook_path, self.database_path)
        self.workbook_info = None
        self.pending_moves.clear()
        self.last_plan = None
        self.last_result = None
        self.last_rescan_conflicts = result.conflicts
        if result.accepted:
            self.project = result.project
            self.status_message = "已重新扫描工作簿"
        else:
            self.status_message = (
                result.conflicts[0].message if result.conflicts else "重新扫描被拒绝"
            )
        self.history.append(self.status_message)
        return self.project

    def export_json(self, path: Path) -> Path:
        output = path.expanduser().resolve()
        output.write_text(
            json.dumps(self.project.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.status_message = f"已导出 {output.name}"
        self.history.append(self.status_message)
        return output

    def export_xlsx(self, path: Path) -> Path:
        output = export_project_workbook(self.project, path, overwrite=True)
        if self.pending_moves:
            self.status_message = (
                f"已导出 {output.name}（不含 {len(self.pending_moves)} 项待同步更改）"
            )
        else:
            self.status_message = f"已导出 {output.name}"
        self.history.append(self.status_message)
        return output

    def backups(self) -> list[Path]:
        return list_backups(self.workbook_path)

    def restore_backup(self, backup: Path) -> Path:
        self.project = restore_project_backup(
            self.workbook_path,
            self.database_path,
            backup,
        )
        self.last_plan = None
        self.last_result = None
        self.last_rescan_conflicts = ()
        self.pending_moves.clear()
        self.workbook_info = None
        self.status_message = f"已恢复备份 {backup.name}"
        self.history.append(self.status_message)
        return self.workbook_path
