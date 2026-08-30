from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from racktool.models.domain import Device, Placement, Rack

MappingKind = Literal["rack_title", "device"]
ConflictSeverity = Literal["warning", "error"]


@dataclass(frozen=True, slots=True)
class SourceMapping:
    mapping_id: str
    workbook_fingerprint: str
    sheet_name: str
    source_range: str
    mapping_kind: MappingKind
    device_id: str | None = None
    rack_id: str | None = None
    style_signature: str | None = None
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IdentityConflict:
    code: str
    severity: ConflictSeverity
    message: str
    entity_ids: list[str] = field(default_factory=list)
    candidate_refs: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RackProject:
    project_id: str
    source_workbook: str | None
    workbook_fingerprint: str | None
    layout_fingerprint: str | None
    profile_id: str | None
    racks: list[Rack] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)
    placements: list[Placement] = field(default_factory=list)
    mappings: list[SourceMapping] = field(default_factory=list)
    conflicts: list[IdentityConflict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RescanResult:
    project: RackProject
    created_rack_ids: tuple[str, ...] = ()
    created_device_ids: tuple[str, ...] = ()
    updated_device_ids: tuple[str, ...] = ()
    unchanged_device_ids: tuple[str, ...] = ()
    missing_device_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["project"] = self.project.to_dict()
        return payload
