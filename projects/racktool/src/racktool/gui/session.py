from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from racktool.core.backup import list_backups, restore_backup
from racktool.core.project import import_workbook, rescan_workbook
from racktool.core.sync import WritePlan, WriteResult, apply_writeback, plan_device_move
from racktool.models.project import RackProject
from racktool.persistence import load_project, save_project


def default_database_path(workbook: Path) -> Path:
    return workbook.with_suffix(workbook.suffix + ".sqlite")


@dataclass
class GuiSession:
    workbook_path: Path
    database_path: Path
    project: RackProject
    last_plan: WritePlan | None = None
    last_result: WriteResult | None = None
    status_message: str = ""
    history: list[str] = field(default_factory=list)

    @classmethod
    def open_workbook(cls, workbook: Path, database: Path | None = None) -> GuiSession:
        workbook_path = workbook.expanduser().resolve()
        database_path = (database or default_database_path(workbook_path)).expanduser().resolve()
        if database_path.is_file():
            session = cls.open_project(database_path, workbook_path)
            session.status_message = "已打开已有项目"
            session.history.append(session.status_message)
            return session
        project = import_workbook(workbook_path)
        save_project(database_path, project)
        session = cls(workbook_path, database_path, project, status_message="已打开工作簿并创建项目")
        session.history.append(session.status_message)
        return session

    @classmethod
    def open_project(cls, database: Path, workbook: Path | None = None) -> GuiSession:
        database_path = database.expanduser().resolve()
        project = load_project(database_path)
        workbook_path = Path(workbook or project.source_workbook or "").expanduser()
        if workbook is not None:
            workbook_path = workbook.expanduser().resolve()
        elif project.source_workbook:
            workbook_path = Path(project.source_workbook).expanduser().resolve()
        else:
            raise ValueError("Project does not record a source workbook")
        if not workbook_path.is_file():
            raise FileNotFoundError(workbook_path)
        session = cls(workbook_path, database_path, project, status_message="已打开项目")
        session.history.append(session.status_message)
        return session

    def _persist(self) -> None:
        save_project(self.database_path, self.project)

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
            rows.append(
                {
                    "device_id": device.device_id,
                    "display_text": device.display_text,
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

    def rack_rows(self) -> list[dict[str, Any]]:
        occupancy = {rack.rack_id: 0 for rack in self.project.racks}
        for placement in self.project.placements:
            if placement.status == "active":
                occupancy[placement.rack_id] = occupancy.get(placement.rack_id, 0) + placement.height_u
        return [
            {
                "rack_id": rack.rack_id,
                "rack_name": rack.rack_name,
                "sheet_name": rack.source_sheet or "",
                "height_u": rack.height_u,
                "occupied_u": occupancy.get(rack.rack_id, 0),
                "title_range": rack.title_range or "",
            }
            for rack in self.project.racks
        ]

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
        return rows

    def plan_move(self, device_id: str, rack_id: str, start_u: int, end_u: int) -> WritePlan:
        plan = plan_device_move(self.project, device_id, rack_id, start_u, end_u)
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
        result = apply_writeback(self.workbook_path, self.project, self.last_plan)
        self.last_result = result
        if result.status == "applied" and result.project is not None:
            self.project = result.project
            self._persist()
            self.status_message = result.message
        else:
            self.status_message = result.message or "写回被拒绝"
        self.history.append(self.status_message)
        return result

    def rescan(self) -> RackProject:
        result = rescan_workbook(self.workbook_path, self.project)
        self.project = result.project
        self._persist()
        self.status_message = "已重新扫描工作簿"
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
        restored = restore_backup(backup, self.workbook_path)
        self.rescan()
        self.status_message = f"已恢复备份 {backup.name}"
        self.history.append(self.status_message)
        return restored
