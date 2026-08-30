from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CellInfo:
    coordinate: str
    value: Any
    data_type: str
    style_signature: str


@dataclass(frozen=True, slots=True)
class SheetInfo:
    name: str
    index: int
    state: str
    reported_dimension: str
    used_range: str | None
    cells: list[CellInfo] = field(default_factory=list)
    merged_ranges: list[str] = field(default_factory=list)
    row_heights: dict[str, float] = field(default_factory=dict)
    column_widths: dict[str, float] = field(default_factory=dict)
    default_row_height: float | None = None
    default_column_width: float | None = None


@dataclass(frozen=True, slots=True)
class WorkbookInfo:
    format: str
    sheets: list[SheetInfo]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
