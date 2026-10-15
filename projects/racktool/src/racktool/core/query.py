"""Bounded, deterministic selectors for conversational clients; text stays data."""
from __future__ import annotations

from typing import Any

from racktool.models.project import RackProject

_SELECTOR_KEYS = {"room", "rack", "device", "contains", "start_u", "end_u", "device_id", "rack_id"}


def validate_selector(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - _SELECTOR_KEYS:
        raise ValueError("selector 必须是对象，且只包含已定义的定位字段。")
    for key, item in value.items():
        if key in {"start_u", "end_u"}:
            if type(item) is not int or not 1 <= item <= 1000:
                raise ValueError("定位 U 位必须为 1–1000 的整数。")
        elif not isinstance(item, str) or not item or len(item) > 32767:
            raise ValueError("定位文字必须是非空字符串。")
    return dict(value)


def device_rows(project: RackProject, selector: dict[str, Any]) -> list[dict[str, Any]]:
    racks = {rack.rack_id: rack for rack in project.racks if rack.status == "active"}
    devices = {device.device_id: device for device in project.devices}
    rows: list[dict[str, Any]] = []
    for placement in project.placements:
        rack = racks.get(placement.rack_id)
        device = devices.get(placement.device_id)
        if placement.status != "active" or rack is None or device is None:
            continue
        row = {"device_id": device.device_id, "rack_id": rack.rack_id,
               "room": rack.source_sheet, "rack": rack.rack_name,
               "device": device.display_text, "start_u": placement.start_u,
               "end_u": placement.end_u, "height_u": placement.height_u}
        if _matches(row, selector):
            rows.append(row)
    return rows


def _matches(row: dict[str, Any], selector: dict[str, Any]) -> bool:
    for key, item in selector.items():
        if key == "contains":
            if item.casefold() not in str(row.get("device", "")).casefold():
                return False
        elif key in {"start_u", "end_u"}:
            if row.get(key) != item:
                return False
        elif str(row.get(key, "")).casefold() != item.casefold():
            return False
    return True


def rack_rows(project: RackProject, selector: dict[str, Any]) -> list[dict[str, Any]]:
    if set(selector) - {"room", "rack", "rack_id"}:
        raise ValueError("机柜定位只允许 room、rack、rack_id。")
    return [{"rack_id": rack.rack_id, "room": rack.source_sheet, "rack": rack.rack_name,
             "height_u": rack.height_u, "direction": rack.direction}
            for rack in project.racks if rack.status == "active" and _matches(
                {"rack_id": rack.rack_id, "room": rack.source_sheet, "rack": rack.rack_name}, selector)]


def query_project(project: RackProject, request: dict[str, Any]) -> dict[str, Any]:
    """Return at most 100 rows with explicit pagination, never guess an ambiguous identity."""
    if not isinstance(request, dict) or set(request) - {"kind", "selector", "limit", "offset"}:
        raise ValueError("查询请求包含未知字段。")
    kind = request.get("kind", "devices")
    selector = validate_selector(request.get("selector", {}))
    limit, offset = request.get("limit", 50), request.get("offset", 0)
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError("limit 必须为 1–100，offset 必须是非负整数。")
    if kind == "devices":
        rows = device_rows(project, selector)
    elif kind in {"racks", "free"}:
        rows = rack_rows(project, selector)
        if kind == "free":
            for row in rows:
                rack = next(r for r in project.racks if r.rack_id == row["rack_id"])
                occupied: set[int] = set()
                for placement in project.placements:
                    if placement.status == "active" and placement.rack_id == row["rack_id"]:
                        occupied.update(unit for unit in rack.u_to_row
                                        if min(placement.start_u, placement.end_u) <= unit <=
                                        max(placement.start_u, placement.end_u))
                available = sorted(set(rack.u_to_row) - occupied)
                intervals: list[dict[str, int]] = []
                for unit in available:
                    if intervals and intervals[-1]["end_u"] == unit - 1:
                        intervals[-1]["end_u"] = unit
                        intervals[-1]["height_u"] += 1
                    else:
                        intervals.append({"start_u": unit, "end_u": unit, "height_u": 1})
                row.update(free_u=len(available), free_ranges=intervals)
    else:
        raise ValueError("kind 只支持 devices、racks、free。")
    return {"status": "ok", "project_id": project.project_id, "kind": kind,
            "total": len(rows), "offset": offset, "limit": limit,
            "next_offset": offset + limit if offset + limit < len(rows) else None,
            "rows": rows[offset:offset + limit]}


def unique_device(project: RackProject, selector: dict[str, Any]) -> dict[str, Any]:
    if not selector:
        raise ValueError("请提供机房、机柜、设备文字或 U 位定位，不选择默认设备。")
    rows = device_rows(project, validate_selector(selector))
    if len(rows) != 1:
        raise ValueError(f"设备定位得到 {len(rows)} 个候选，请补充机房、机柜、完整设备文字或 U 位；无需用户填写 ID。")
    return rows[0]


def unique_rack(project: RackProject, selector: dict[str, Any]) -> dict[str, Any]:
    if not selector:
        raise ValueError("请提供目标机房或机柜，不选择默认机柜。")
    rows = rack_rows(project, validate_selector(selector))
    if len(rows) != 1:
        raise ValueError(f"机柜定位得到 {len(rows)} 个候选，请补充机房和机柜名；无需用户填写 ID。")
    return rows[0]
