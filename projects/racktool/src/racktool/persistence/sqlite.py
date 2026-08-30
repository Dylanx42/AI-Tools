from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from racktool.models.domain import CellRange, Device, Placement, Rack
from racktool.models.project import IdentityConflict, RackProject, SourceMapping

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    source_workbook TEXT,
    workbook_fingerprint TEXT,
    layout_fingerprint TEXT,
    profile_id TEXT,
    metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS racks (
    rack_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS placements (
    placement_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mappings (
    mapping_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conflicts (
    conflict_index INTEGER NOT NULL,
    project_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (project_id, conflict_index)
);
"""


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(_SCHEMA)
    return connection


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("Persisted payload must be an object")
    return payload


def _u_to_row(raw: Any) -> dict[int, int]:
    if not isinstance(raw, dict):
        return {}
    return {int(key): int(value) for key, value in raw.items()}


def _cell_range(raw: Any) -> CellRange | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError("Invalid CellRange payload")
    return CellRange(
        int(raw["min_row"]),
        int(raw["max_row"]),
        int(raw["min_col"]),
        int(raw["max_col"]),
        str(raw["a1"]),
    )


def _rack(payload: dict[str, Any]) -> Rack:
    return Rack(
        rack_id=str(payload["rack_id"]),
        rack_name=str(payload["rack_name"]),
        height_u=int(payload["height_u"]),
        source_sheet=payload.get("source_sheet"),
        bounds=_cell_range(payload.get("bounds")),
        profile_id=payload.get("profile_id"),
        confidence=payload.get("confidence"),
        start_row=payload.get("start_row"),
        end_row=payload.get("end_row"),
        left_axis_column=payload.get("left_axis_column"),
        right_axis_column=payload.get("right_axis_column"),
        device_columns=list(payload.get("device_columns") or []),
        direction=payload.get("direction"),
        u_to_row=_u_to_row(payload.get("u_to_row", {})),
        title_range=payload.get("title_range"),
    )


def _device(payload: dict[str, Any]) -> Device:
    attributes = payload.get("attributes") or {}
    if not isinstance(attributes, dict):
        raise TypeError("Device attributes must be an object")
    return Device(
        device_id=str(payload["device_id"]),
        display_text=str(payload["display_text"]),
        canonical_name=payload.get("canonical_name"),
        attributes=attributes,
        confidence=payload.get("confidence"),
        style_signature=payload.get("style_signature"),
    )


def _placement(payload: dict[str, Any]) -> Placement:
    return Placement(
        placement_id=str(payload["placement_id"]),
        device_id=str(payload["device_id"]),
        rack_id=str(payload["rack_id"]),
        start_u=int(payload["start_u"]),
        end_u=int(payload["end_u"]),
        status=str(payload.get("status", "active")),
    )


def _mapping(payload: dict[str, Any]) -> SourceMapping:
    return SourceMapping(
        mapping_id=str(payload["mapping_id"]),
        workbook_fingerprint=str(payload["workbook_fingerprint"]),
        sheet_name=str(payload["sheet_name"]),
        source_range=str(payload["source_range"]),
        mapping_kind=payload["mapping_kind"],
        device_id=payload.get("device_id"),
        rack_id=payload.get("rack_id"),
        style_signature=payload.get("style_signature"),
        confidence=payload.get("confidence"),
    )


def _conflict(payload: dict[str, Any]) -> IdentityConflict:
    return IdentityConflict(
        code=str(payload["code"]),
        severity=payload["severity"],
        message=str(payload["message"]),
        entity_ids=list(payload.get("entity_ids", [])),
        candidate_refs=list(payload.get("candidate_refs", [])),
        evidence=list(payload.get("evidence", [])),
    )


def save_project(path: Path, project: RackProject) -> None:
    connection = _connect(path)
    try:
        connection.execute("DELETE FROM conflicts WHERE project_id = ?", (project.project_id,))
        connection.execute("DELETE FROM mappings WHERE project_id = ?", (project.project_id,))
        connection.execute("DELETE FROM placements WHERE project_id = ?", (project.project_id,))
        connection.execute("DELETE FROM devices WHERE project_id = ?", (project.project_id,))
        connection.execute("DELETE FROM racks WHERE project_id = ?", (project.project_id,))
        connection.execute("DELETE FROM projects WHERE project_id = ?", (project.project_id,))
        connection.execute(
            """
            INSERT INTO projects (
                project_id, source_workbook, workbook_fingerprint, layout_fingerprint,
                profile_id, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                project.source_workbook,
                project.workbook_fingerprint,
                project.layout_fingerprint,
                project.profile_id,
                _dump(project.metadata),
            ),
        )
        connection.executemany(
            "INSERT INTO racks (rack_id, project_id, payload_json) VALUES (?, ?, ?)",
            [(item.rack_id, project.project_id, _dump(item.to_dict())) for item in project.racks],
        )
        connection.executemany(
            "INSERT INTO devices (device_id, project_id, payload_json) VALUES (?, ?, ?)",
            [
                (item.device_id, project.project_id, _dump(item.to_dict()))
                for item in project.devices
            ],
        )
        connection.executemany(
            "INSERT INTO placements (placement_id, project_id, payload_json) VALUES (?, ?, ?)",
            [
                (item.placement_id, project.project_id, _dump(item.to_dict()))
                for item in project.placements
            ],
        )
        connection.executemany(
            "INSERT INTO mappings (mapping_id, project_id, payload_json) VALUES (?, ?, ?)",
            [
                (item.mapping_id, project.project_id, _dump(item.to_dict()))
                for item in project.mappings
            ],
        )
        connection.executemany(
            "INSERT INTO conflicts (conflict_index, project_id, payload_json) VALUES (?, ?, ?)",
            [
                (index, project.project_id, _dump(item.to_dict()))
                for index, item in enumerate(project.conflicts)
            ],
        )
        connection.commit()
    finally:
        connection.close()


def load_project(path: Path) -> RackProject:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = _connect(path)
    try:
        project_row = connection.execute(
            """
            SELECT project_id, source_workbook, workbook_fingerprint, layout_fingerprint,
                   profile_id, metadata_json
            FROM projects
            """
        ).fetchall()
        if len(project_row) != 1:
            raise ValueError("SQLite project file must contain exactly one project")
        (
            project_id,
            source_workbook,
            workbook_fingerprint,
            layout_fingerprint,
            profile_id,
            metadata_json,
        ) = project_row[0]
        racks = [
            _rack(_load(payload))
            for (_, payload,) in connection.execute(
                "SELECT rack_id, payload_json FROM racks WHERE project_id = ? ORDER BY rack_id",
                (project_id,),
            )
        ]
        devices = [
            _device(_load(payload))
            for (_, payload,) in connection.execute(
                "SELECT device_id, payload_json FROM devices WHERE project_id = ? ORDER BY device_id",
                (project_id,),
            )
        ]
        placements = [
            _placement(_load(payload))
            for (_, payload,) in connection.execute(
                "SELECT placement_id, payload_json FROM placements WHERE project_id = ? ORDER BY placement_id",
                (project_id,),
            )
        ]
        mappings = [
            _mapping(_load(payload))
            for (_, payload,) in connection.execute(
                "SELECT mapping_id, payload_json FROM mappings WHERE project_id = ? ORDER BY mapping_id",
                (project_id,),
            )
        ]
        conflicts = [
            _conflict(_load(payload))
            for (_, payload,) in connection.execute(
                "SELECT conflict_index, payload_json FROM conflicts WHERE project_id = ? ORDER BY conflict_index",
                (project_id,),
            )
        ]
        metadata = json.loads(metadata_json)
        if not isinstance(metadata, dict):
            raise TypeError("Project metadata must be an object")
        return RackProject(
            project_id=str(project_id),
            source_workbook=source_workbook,
            workbook_fingerprint=workbook_fingerprint,
            layout_fingerprint=layout_fingerprint,
            profile_id=profile_id,
            racks=racks,
            devices=devices,
            placements=placements,
            mappings=mappings,
            conflicts=conflicts,
            metadata=metadata,
        )
    finally:
        connection.close()
