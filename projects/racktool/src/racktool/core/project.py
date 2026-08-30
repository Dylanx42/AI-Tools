from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import range_boundaries

from racktool.core.analyzer import analyze_workbook
from racktool.core.identity import IdFactory, default_id_factory
from racktool.models.analysis import (
    DeviceCandidate,
    PlacementCandidate,
    RackCandidate,
    SheetAnalysis,
    WorkbookAnalysis,
)
from racktool.models.domain import CellRange, Device, Placement, Rack
from racktool.models.project import IdentityConflict, RackProject, RescanResult, SourceMapping
from racktool.profiles.fingerprint import fingerprint_workbook


def _cell_range(a1: str) -> CellRange:
    min_col, min_row, max_col, max_row = range_boundaries(a1)
    if min_col is None or min_row is None or max_col is None or max_row is None:
        raise ValueError(f"Invalid cell range: {a1}")
    return CellRange(min_row, max_row, min_col, max_col, a1)


def _a1(min_row: int, max_row: int, min_col: int, max_col: int) -> str:
    start = f"{get_column_letter(min_col)}{min_row}"
    end = f"{get_column_letter(max_col)}{max_row}"
    return start if start == end else f"{start}:{end}"


def _rack_bounds(rack: RackCandidate) -> CellRange:
    title = _cell_range(rack.title_range)
    right = rack.right_axis_column or max(rack.device_columns + [rack.left_axis_column])
    min_row = min(title.min_row, rack.start_row)
    max_row = max(title.max_row, rack.end_row)
    min_col = min(title.min_col, rack.left_axis_column)
    max_col = max(title.max_col, right)
    return CellRange(min_row, max_row, min_col, max_col, _a1(min_row, max_row, min_col, max_col))


def _occupancy_conflicts(project: RackProject) -> list[IdentityConflict]:
    conflicts: list[IdentityConflict] = []
    by_rack: dict[str, dict[int, list[Placement]]] = defaultdict(lambda: defaultdict(list))
    for placement in project.placements:
        if placement.status != "active":
            continue
        start = min(placement.start_u, placement.end_u)
        end = max(placement.start_u, placement.end_u)
        for unit in range(start, end + 1):
            by_rack[placement.rack_id][unit].append(placement)
    for rack_id, occupied in by_rack.items():
        overlapping = sorted(
            {
                placement.placement_id
                for placements in occupied.values()
                if len(placements) > 1
                for placement in placements
            }
        )
        if overlapping:
            conflicts.append(
                IdentityConflict(
                    code="overlapping-active-placements",
                    severity="error",
                    message=f"Active placements overlap in rack {rack_id}",
                    entity_ids=overlapping,
                )
            )
    return conflicts


def _with_occupancy(project: RackProject) -> RackProject:
    return RackProject(
        project_id=project.project_id,
        source_workbook=project.source_workbook,
        workbook_fingerprint=project.workbook_fingerprint,
        layout_fingerprint=project.layout_fingerprint,
        profile_id=project.profile_id,
        racks=project.racks,
        devices=project.devices,
        placements=project.placements,
        mappings=project.mappings,
        conflicts=project.conflicts + _occupancy_conflicts(project),
        metadata=project.metadata,
    )


def _make_rack(rack: RackCandidate, rack_id: str, sheet_name: str, profile_id: str | None) -> Rack:
    return Rack(
        rack_id=rack_id,
        rack_name=rack.rack_name,
        height_u=rack.height_u,
        source_sheet=sheet_name,
        bounds=_rack_bounds(rack),
        profile_id=profile_id,
        confidence=rack.confidence,
        start_row=rack.start_row,
        end_row=rack.end_row,
        left_axis_column=rack.left_axis_column,
        right_axis_column=rack.right_axis_column,
        device_columns=list(rack.device_columns),
        direction=rack.direction,
        u_to_row=dict(rack.u_to_row),
        title_range=rack.title_range,
    )


def _make_device(device: DeviceCandidate, device_id: str, existing: Device | None = None) -> Device:
    return Device(
        device_id=device_id,
        display_text=device.display_text,
        canonical_name=existing.canonical_name if existing is not None else None,
        attributes=dict(existing.attributes) if existing is not None else {},
        confidence=device.confidence,
        style_signature=device.style_signature,
    )


def _make_mapping(
    mapping_id: str,
    fingerprint: str,
    sheet_name: str,
    source_range: str,
    mapping_kind: str,
    *,
    device_id: str | None = None,
    rack_id: str | None = None,
    style_signature: str | None = None,
    confidence: float | None = None,
) -> SourceMapping:
    return SourceMapping(
        mapping_id=mapping_id,
        workbook_fingerprint=fingerprint,
        sheet_name=sheet_name,
        source_range=source_range,
        mapping_kind=mapping_kind,  # type: ignore[arg-type]
        device_id=device_id,
        rack_id=rack_id,
        style_signature=style_signature,
        confidence=confidence,
    )


def _build_from_analysis(
    workbook_path: Path,
    analysis: WorkbookAnalysis,
    *,
    project_id: str,
    profile_id: str | None,
    id_factory: IdFactory,
) -> RackProject:
    fingerprint = fingerprint_workbook(workbook_path, analysis)
    racks: list[Rack] = []
    devices: list[Device] = []
    placements: list[Placement] = []
    mappings: list[SourceMapping] = []
    conflicts: list[IdentityConflict] = []

    for sheet in analysis.sheets:
        rack_ids = {rack.candidate_id: id_factory("RACK") for rack in sheet.racks}
        device_ids = {device.candidate_id: id_factory("DEV") for device in sheet.devices}
        racks_by_candidate = {rack.candidate_id: rack for rack in sheet.racks}
        devices_by_candidate = {device.candidate_id: device for device in sheet.devices}

        for rack in sheet.racks:
            rack_id = rack_ids[rack.candidate_id]
            racks.append(_make_rack(rack, rack_id, sheet.name, profile_id))
            mappings.append(
                _make_mapping(
                    id_factory("MAP"),
                    fingerprint.workbook_sha256,
                    sheet.name,
                    rack.title_range,
                    "rack_title",
                    rack_id=rack_id,
                    confidence=rack.confidence,
                )
            )

        for device in sheet.devices:
            device_id = device_ids[device.candidate_id]
            devices.append(_make_device(device, device_id))
            mappings.append(
                _make_mapping(
                    id_factory("MAP"),
                    fingerprint.workbook_sha256,
                    sheet.name,
                    device.source_range,
                    "device",
                    device_id=device_id,
                    confidence=device.confidence,
                    style_signature=device.style_signature,
                )
            )

        for placement in sheet.placements:
            rack = racks_by_candidate[placement.rack_candidate_id]
            device = devices_by_candidate[placement.device_candidate_id]
            placements.append(
                Placement(
                    placement_id=id_factory("PLC"),
                    device_id=device_ids[device.candidate_id],
                    rack_id=rack_ids[rack.candidate_id],
                    start_u=placement.start_u,
                    end_u=placement.end_u,
                    status="active",
                )
            )

        if any(issue.code == "duplicate-rack-title" for issue in sheet.issues):
            conflicts.append(
                IdentityConflict(
                    code="duplicate-rack-title",
                    severity="warning",
                    message=f"Duplicate rack titles were imported as distinct identities on {sheet.name}",
                    candidate_refs=[rack.candidate_id for rack in sheet.racks],
                    evidence=["titles are not unique; identity is bound to source ranges"],
                )
            )

    return _with_occupancy(
        RackProject(
            project_id=project_id,
            source_workbook=str(workbook_path),
            workbook_fingerprint=fingerprint.workbook_sha256,
            layout_fingerprint=fingerprint.layout_sha256,
            profile_id=profile_id,
            racks=racks,
            devices=devices,
            placements=placements,
            mappings=mappings,
            conflicts=conflicts,
            metadata={"schema_version": 1},
        )
    )


def import_workbook(
    workbook_path: Path,
    *,
    profile_id: str | None = None,
    id_factory: IdFactory | None = None,
) -> RackProject:
    factory = id_factory or default_id_factory
    return _build_from_analysis(
        workbook_path,
        analyze_workbook(workbook_path),
        project_id=factory("PRJ"),
        profile_id=profile_id,
        id_factory=factory,
    )


def _mapping_lookup(project: RackProject, kind: str) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for mapping in project.mappings:
        if mapping.mapping_kind != kind:
            continue
        entity_id = mapping.rack_id if kind == "rack_title" else mapping.device_id
        if entity_id is None:
            continue
        result[(mapping.sheet_name, mapping.source_range)] = entity_id
    return result


def _rack_id_for_candidate(racks: list[Rack], sheet_name: str, title_range: str) -> str | None:
    for rack in racks:
        if rack.source_sheet == sheet_name and rack.title_range == title_range:
            return rack.rack_id
    return None


def _bind_device(
    *,
    old_device: Device | None,
    device: DeviceCandidate,
    placement: PlacementCandidate,
    rack_id: str,
    sheet_name: str,
    fingerprint: str,
    factory: IdFactory,
    old_placements: dict[str, Placement],
    new_devices: list[Device],
    new_placements: list[Placement],
    new_mappings: list[SourceMapping],
    created_devices: list[str],
    updated_devices: list[str],
    unchanged_devices: list[str],
) -> str:
    if old_device is None:
        device_id = factory("DEV")
        created_devices.append(device_id)
        new_devices.append(_make_device(device, device_id))
        placement_id = factory("PLC")
    else:
        device_id = old_device.device_id
        new_devices.append(_make_device(device, device_id, old_device))
        old_placement = old_placements.get(device_id)
        placement_id = old_placement.placement_id if old_placement is not None else factory("PLC")
        changed = (
            old_device.display_text != device.display_text
            or old_placement is None
            or old_placement.rack_id != rack_id
            or old_placement.start_u != placement.start_u
            or old_placement.end_u != placement.end_u
        )
        (updated_devices if changed else unchanged_devices).append(device_id)
    new_placements.append(
        Placement(
            placement_id=placement_id,
            device_id=device_id,
            rack_id=rack_id,
            start_u=placement.start_u,
            end_u=placement.end_u,
            status="active",
        )
    )
    new_mappings.append(
        _make_mapping(
            factory("MAP"),
            fingerprint,
            sheet_name,
            device.source_range,
            "device",
            device_id=device_id,
            rack_id=rack_id,
            confidence=device.confidence,
            style_signature=device.style_signature,
        )
    )
    return device_id


def rescan_workbook(
    workbook_path: Path,
    project: RackProject,
    *,
    id_factory: IdFactory | None = None,
) -> RescanResult:
    factory = id_factory or default_id_factory
    analysis = analyze_workbook(workbook_path)
    fingerprint = fingerprint_workbook(workbook_path, analysis)
    old_racks = {rack.rack_id: rack for rack in project.racks}
    old_devices = {device.device_id: device for device in project.devices}
    old_placements = {placement.device_id: placement for placement in project.placements if placement.status == "active"}
    rack_by_range = _mapping_lookup(project, "rack_title")
    device_by_range = _mapping_lookup(project, "device")

    new_racks: list[Rack] = []
    new_devices: list[Device] = []
    new_placements: list[Placement] = []
    new_mappings: list[SourceMapping] = []
    conflicts: list[IdentityConflict] = []
    created_racks: list[str] = []
    created_devices: list[str] = []
    updated_devices: list[str] = []
    unchanged_devices: list[str] = []
    assigned_rack_ids: set[str] = set()
    assigned_device_ids: set[str] = set()
    unmatched_devices: list[tuple[SheetAnalysis, DeviceCandidate, PlacementCandidate]] = []

    for sheet in analysis.sheets:
        for rack in sheet.racks:
            mapped = rack_by_range.get((sheet.name, rack.title_range))
            if mapped is not None and mapped in old_racks and mapped not in assigned_rack_ids:
                rack_id = mapped
            else:
                rack_id = factory("RACK")
                created_racks.append(rack_id)
            assigned_rack_ids.add(rack_id)
            new_racks.append(_make_rack(rack, rack_id, sheet.name, project.profile_id))
            new_mappings.append(
                _make_mapping(
                    factory("MAP"),
                    fingerprint.workbook_sha256,
                    sheet.name,
                    rack.title_range,
                    "rack_title",
                    rack_id=rack_id,
                    confidence=rack.confidence,
                )
            )

        placement_by_device = {item.device_candidate_id: item for item in sheet.placements}
        for device in sheet.devices:
            unmatched_devices.append((sheet, device, placement_by_device[device.candidate_id]))

    still_unmatched: list[tuple[SheetAnalysis, DeviceCandidate, PlacementCandidate]] = []
    for sheet, device, placement in unmatched_devices:
        title_range = next(
            rack.title_range for rack in sheet.racks if rack.candidate_id == placement.rack_candidate_id
        )
        matched_rack_id = _rack_id_for_candidate(new_racks, sheet.name, title_range)
        mapped = device_by_range.get((sheet.name, device.source_range))
        if (
            mapped is not None
            and mapped in old_devices
            and mapped not in assigned_device_ids
            and matched_rack_id is not None
        ):
            assigned_device_ids.add(
                _bind_device(
                    old_device=old_devices[mapped],
                    device=device,
                    placement=placement,
                    rack_id=matched_rack_id,
                    sheet_name=sheet.name,
                    fingerprint=fingerprint.workbook_sha256,
                    factory=factory,
                    old_placements=old_placements,
                    new_devices=new_devices,
                    new_placements=new_placements,
                    new_mappings=new_mappings,
                    created_devices=created_devices,
                    updated_devices=updated_devices,
                    unchanged_devices=unchanged_devices,
                )
            )
        else:
            still_unmatched.append((sheet, device, placement))

    leftover_old = [device_id for device_id in old_devices if device_id not in assigned_device_ids]
    old_by_text: dict[str, list[str]] = defaultdict(list)
    for device_id in leftover_old:
        old_by_text[old_devices[device_id].display_text.casefold()].append(device_id)
    new_by_text: dict[str, list[tuple[SheetAnalysis, DeviceCandidate, PlacementCandidate]]] = defaultdict(list)
    for item in still_unmatched:
        new_by_text[item[1].display_text.casefold()].append(item)

    matched_candidates: set[str] = set()
    for text, new_items in new_by_text.items():
        old_ids = old_by_text.get(text, [])
        if len(new_items) == 1 and len(old_ids) == 1:
            sheet, device, placement = new_items[0]
            title_range = next(
                rack.title_range for rack in sheet.racks if rack.candidate_id == placement.rack_candidate_id
            )
            matched_rack_id = _rack_id_for_candidate(new_racks, sheet.name, title_range)
            if matched_rack_id is None:
                continue
            assigned_device_ids.add(
                _bind_device(
                    old_device=old_devices[old_ids[0]],
                    device=device,
                    placement=placement,
                    rack_id=matched_rack_id,
                    sheet_name=sheet.name,
                    fingerprint=fingerprint.workbook_sha256,
                    factory=factory,
                    old_placements=old_placements,
                    new_devices=new_devices,
                    new_placements=new_placements,
                    new_mappings=new_mappings,
                    created_devices=created_devices,
                    updated_devices=updated_devices,
                    unchanged_devices=unchanged_devices,
                )
            )
            matched_candidates.add(device.candidate_id)
        elif len(new_items) > 1 or len(old_ids) > 1:
            conflicts.append(
                IdentityConflict(
                    code="ambiguous-device-identity",
                    severity="error",
                    message="Multiple devices share evidence; refusing to guess identity",
                    entity_ids=old_ids,
                    candidate_refs=[item[1].candidate_id for item in new_items],
                    evidence=[f"display_text={text}"],
                )
            )

    for sheet, device, placement in still_unmatched:
        if device.candidate_id in matched_candidates:
            continue
        title_range = next(
            rack.title_range for rack in sheet.racks if rack.candidate_id == placement.rack_candidate_id
        )
        matched_rack_id = _rack_id_for_candidate(new_racks, sheet.name, title_range)
        if matched_rack_id is None:
            conflicts.append(
                IdentityConflict(
                    code="unmapped-device-rack",
                    severity="error",
                    message="Device candidate has no mapped rack identity",
                    candidate_refs=[device.candidate_id],
                )
            )
            continue
        created_id = _bind_device(
            old_device=None,
            device=device,
            placement=placement,
            rack_id=matched_rack_id,
            sheet_name=sheet.name,
            fingerprint=fingerprint.workbook_sha256,
            factory=factory,
            old_placements=old_placements,
            new_devices=new_devices,
            new_placements=new_placements,
            new_mappings=new_mappings,
            created_devices=created_devices,
            updated_devices=updated_devices,
            unchanged_devices=unchanged_devices,
        )
        assigned_device_ids.add(created_id)

    missing_device_ids = tuple(device_id for device_id in old_devices if device_id not in assigned_device_ids)
    for device_id in missing_device_ids:
        new_devices.append(old_devices[device_id])
        old_placement = old_placements.get(device_id)
        if old_placement is not None:
            new_placements.append(
                Placement(
                    placement_id=old_placement.placement_id,
                    device_id=old_placement.device_id,
                    rack_id=old_placement.rack_id,
                    start_u=old_placement.start_u,
                    end_u=old_placement.end_u,
                    status="missing",
                )
            )

    rebuilt = _with_occupancy(
        RackProject(
            project_id=project.project_id,
            source_workbook=str(workbook_path),
            workbook_fingerprint=fingerprint.workbook_sha256,
            layout_fingerprint=fingerprint.layout_sha256,
            profile_id=project.profile_id,
            racks=new_racks,
            devices=new_devices,
            placements=new_placements,
            mappings=new_mappings,
            conflicts=conflicts,
            metadata=dict(project.metadata),
        )
    )
    return RescanResult(
        project=rebuilt,
        created_rack_ids=tuple(created_racks),
        created_device_ids=tuple(created_devices),
        updated_device_ids=tuple(updated_devices),
        unchanged_device_ids=tuple(unchanged_devices),
        missing_device_ids=missing_device_ids,
    )
