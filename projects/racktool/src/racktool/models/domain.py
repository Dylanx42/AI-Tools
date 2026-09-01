from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CellRange:
    min_row: int
    max_row: int
    min_col: int
    max_col: int
    a1: str

    def __post_init__(self) -> None:
        if min(self.min_row, self.min_col) < 1:
            raise ValueError("Cell range indices must be positive")
        if self.max_row < self.min_row or self.max_col < self.min_col:
            raise ValueError("Cell range bounds are inverted")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Rack:
    rack_id: str
    rack_name: str
    height_u: int

    def __post_init__(self) -> None:
        if self.height_u < 1:
            raise ValueError("Rack height must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Device:
    device_id: str
    display_text: str
    canonical_name: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Placement:
    placement_id: str
    device_id: str
    rack_id: str
    start_u: int
    end_u: int
    status: str = "active"

    def __post_init__(self) -> None:
        if self.start_u < 1 or self.end_u < 1:
            raise ValueError("Placement U values must be positive")

    @property
    def height_u(self) -> int:
        return abs(self.end_u - self.start_u) + 1

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["height_u"] = self.height_u
        return result
