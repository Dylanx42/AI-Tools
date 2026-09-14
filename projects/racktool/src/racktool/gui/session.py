from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from racktool.core.backup import list_backups
from racktool.core.identity import normalize_path
from racktool.core.service import (
    commit_write_plan,
    import_project,
    load_project_state,
    rescan_project,
    restore_project_backup,
)
from racktool.core.sync import (
    MoveRequest,
    WritePlan,
    WriteResult,
    plan_device_move,
    plan_device_moves,
)
from racktool.models.project import IdentityConflict, RackProject


def default_database_path(workbook: Path) -> Path:
    return workbook.with_suffix(workbook.suffix + ".sqlite")


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

    @classmethod
    def open_workbook(cls, workbook: Path, database: Path | None = None) -> GuiSession:
        workbook_path = normalize_path(workbook)
        database_path = normalize_path(database or default_database_path(workbook_path))
        if database_path.is_file():
            session = cls.open_project(database_path, workbook_path)
            session.status_message = "已打开已有项目"
            session.history.append(session.status_message)
            return session
        project = import_project(workbook_path, database_path)
        session = cls(workbook_path, database_path, project, status_message="已打开工作簿并创建项目")
        session.history.append(session.status_message)
        return session

    @classmethod
    def open_project(cls, database: Path, workbook: Path | None = None) -> GuiSession:
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
        for device in self.project.devices:
            placement = placements.get(device.device_id)
            mapping = mappings.get(device.device_id)
            rack = racks.get(placement.rack_id) if placement is not None else None
            text_lines = [line.strip() for line in device.display_text.splitlines() if line.strip()]
            primary_label = device.canonical_name or (text_lines[0] if text_lines else "未命名设备")
            rows.append(
                {
                    "device_id": device.device_id,
                    "display_text": device.display_text,
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
                }
            )
        return rows

    def device_page(
        self,
        query: str = "",
        *,
        rack_id: str | None = None,
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
        return rows[offset : offset + limit], len(rows)

    def rack_rows(self) -> list[dict[str, Any]]:
        occupancy = {rack.rack_id: 0 for rack in self.project.racks}
        device_counts = {rack.rack_id: 0 for rack in self.project.racks}
        for placement in self.project.placements:
            if placement.status == "active":
                occupancy[placement.rack_id] = occupancy.get(placement.rack_id, 0) + placement.height_u
                device_counts[placement.rack_id] = device_counts.get(placement.rack_id, 0) + 1
        return [
            {
                "rack_id": rack.rack_id,
                "rack_name": rack.rack_name,
                "sheet_name": rack.source_sheet or "",
                "height_u": rack.height_u,
                "occupied_u": occupancy.get(rack.rack_id, 0),
                "available_u": max(rack.height_u - occupancy.get(rack.rack_id, 0), 0),
                "occupancy_percent": round(
                    occupancy.get(rack.rack_id, 0) / rack.height_u * 100
                ),
                "device_count": device_counts.get(rack.rack_id, 0),
                "title_range": rack.title_range or "",
                "status": rack.status,
            }
            for rack in self.project.racks
        ]

    def occupancy_segments(self, rack_id: str) -> list[dict[str, Any]]:
        devices = {device.device_id: device for device in self.project.devices}
        segments: list[dict[str, Any]] = []
        for placement in self.project.placements:
            if placement.rack_id != rack_id or placement.status != "active":
                continue
            device = devices[placement.device_id]
            text_lines = [line.strip() for line in device.display_text.splitlines() if line.strip()]
            segments.append(
                {
                    "device_id": device.device_id,
                    "display_text": device.display_text,
                    "primary_label": (
                        device.canonical_name
                        or (text_lines[0] if text_lines else "未命名设备")
                    ),
                    "start_u": min(placement.start_u, placement.end_u),
                    "end_u": max(placement.start_u, placement.end_u),
                    "height_u": placement.height_u,
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
            for unit in range(min(placement.start_u, placement.end_u), max(placement.start_u, placement.end_u) + 1):
                by_u[unit] = device.display_text
        return [
            {"u": unit, "display_text": by_u.get(unit, "")}
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
        self.pending_moves = [
            item for item in self.pending_moves if item.device_id != device_id
        ]
        if any(action.device_id == device_id for action in plan.actions):
            self.pending_moves.append(replacement)
            self.status_message = f"已加入待同步（共 {len(self.pending_moves)} 项）"
        else:
            self.status_message = "目标位置未变化，未加入待同步"
        self.history.append(self.status_message)
        return plan

    def remove_pending_move(self, device_id: str) -> None:
        before = len(self.pending_moves)
        self.pending_moves = [
            item for item in self.pending_moves if item.device_id != device_id
        ]
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
            self.pending_moves.clear()
            self.last_plan = None
            self.status_message = result.message
        else:
            self.status_message = result.message or "写回被拒绝"
        self.history.append(self.status_message)
        return result

    def rescan(self) -> RackProject:
        result = rescan_project(self.workbook_path, self.database_path)
        self.pending_moves.clear()
        self.last_plan = None
        self.last_result = None
        self.last_rescan_conflicts = result.conflicts
        if result.accepted:
            self.project = result.project
            self.status_message = "已重新扫描工作簿"
        else:
            self.status_message = (
                result.conflicts[0].message
                if result.conflicts
                else "重新扫描被拒绝"
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
        self.status_message = f"已恢复备份 {backup.name}"
        self.history.append(self.status_message)
        return self.workbook_path
