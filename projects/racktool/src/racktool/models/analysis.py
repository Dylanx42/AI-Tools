from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AxisDirection = Literal["ascending", "descending"]
IssueSeverity = Literal["info", "warning", "error"]


@dataclass(frozen=True, slots=True)
class AnalysisIssue:
    code: str
    severity: IssueSeverity
    message: str
    candidate_ids: list[str] = field(default_factory=list)
    source_ranges: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class UAxisCandidate:
    sheet_name: str
    column_index: int
    column_letter: str
    start_row: int
    end_row: int
    min_u: int
    max_u: int
    direction: AxisDirection
    u_to_row: dict[int, int]
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RackCandidate:
    candidate_id: str
    sheet_name: str
    rack_name: str
    title_range: str
    left_axis_column: int
    right_axis_column: int | None
    device_columns: list[int]
    start_row: int
    end_row: int
    height_u: int
    direction: AxisDirection
    u_to_row: dict[int, int]
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DeviceCandidate:
    candidate_id: str
    sheet_name: str
    display_text: str
    value_type: str
    source_range: str
    style_signature: str
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PlacementCandidate:
    candidate_id: str
    device_candidate_id: str
    rack_candidate_id: str
    start_u: int
    end_u: int
    height_u: int
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SheetAnalysis:
    name: str
    u_axes: list[UAxisCandidate] = field(default_factory=list)
    racks: list[RackCandidate] = field(default_factory=list)
    devices: list[DeviceCandidate] = field(default_factory=list)
    placements: list[PlacementCandidate] = field(default_factory=list)
    issues: list[AnalysisIssue] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WorkbookAnalysis:
    format: str
    sheets: list[SheetAnalysis]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
