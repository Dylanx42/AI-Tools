from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

MatchStatus = Literal["matched", "review_required", "rejected"]
SelectionStatus = Literal["matched", "review_required", "ambiguous", "unmatched"]
ApplicationStatus = Literal["applied", "review_required", "ambiguous", "rejected"]
AxisDirectionRule = Literal["ascending", "descending", "any"]
AxisPairingRule = Literal["paired", "single_axis_edge", "mixed", "any"]
RackTitleMode = Literal["merged_cell_above_u_axis", "fixed_range"]
DeviceAreaMode = Literal["between_u_axes", "between_or_edge", "fixed_range"]


class ProfileError(ValueError):
    """Base error for invalid or inapplicable Profile input."""


class ProfileLoadError(ProfileError):
    """Raised when a Profile file cannot be safely loaded."""


class ProfileValidationError(ProfileError):
    """Raised when loaded Profile data violates the schema contract."""


@dataclass(frozen=True, slots=True)
class ProfileMatchRule:
    sheet_name_regex: str | None = None
    min_confidence: float = 1.0
    review_confidence: float = 0.5
    allow_multiple_sheets: bool = False
    require_issue_free: bool = True


@dataclass(frozen=True, slots=True)
class RackRule:
    title_mode: RackTitleMode
    height_mode: Literal["infer_from_u_axis"]
    title_range: str | None = None


@dataclass(frozen=True, slots=True)
class UAxisRule:
    direction: AxisDirectionRule = "any"
    pairing: AxisPairingRule = "any"
    allowed_heights: tuple[int, ...] = ()
    left_column: int | None = None
    right_column: int | None = None
    start_row: int | None = None
    end_row: int | None = None
    max_missing_rows: int = 1


@dataclass(frozen=True, slots=True)
class DeviceAreaRule:
    mode: DeviceAreaMode
    source_range: str | None = None


@dataclass(frozen=True, slots=True)
class TextRule:
    ignore_exact: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LayoutProfile:
    schema_version: int
    profile_id: str
    name: str
    match: ProfileMatchRule
    rack: RackRule
    u_axis: UAxisRule
    device_area: DeviceAreaRule
    text: TextRule = field(default_factory=TextRule)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProfileMatchResult:
    profile_id: str
    sheet_name: str
    score: float
    status: MatchStatus
    reasons: tuple[str, ...] = ()
    mismatches: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProfileSelection:
    status: SelectionStatus
    selected_profile_id: str | None
    selected_sheet_name: str | None
    score: float | None
    matches: tuple[ProfileMatchResult, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WorkbookFingerprint:
    schema_version: int
    workbook_sha256: str
    layout_sha256: str
    features: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProfileApplication:
    status: ApplicationStatus
    profile_id: str
    dry_run: bool
    fingerprint: WorkbookFingerprint
    matches: tuple[ProfileMatchResult, ...]
    selected_sheets: tuple[str, ...]
    ignored_device_candidate_ids: tuple[str, ...]
    analysis: dict[str, Any] | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
