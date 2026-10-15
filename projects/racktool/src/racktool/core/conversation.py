"""Reviewable, restart-safe JSON edit protocol. No LLM or free-text interpretation."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import shutil
import tempfile
from pathlib import Path
from typing import Any

from racktool.core.editing import add_draft_device, edit_draft_device
from racktool.core.identity import new_entity_id, normalize_path, sha256_file
from racktool.core.query import unique_device, unique_rack
from racktool.core.service import commit_write_plan, load_project_state
from racktool.core.sync import WritePlan, plan_device_add, plan_device_edit
from racktool.models.project import RackProject


def _json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _state(database: Path) -> tuple[RackProject, str, str | None]:
    revision = sha256_file(database)
    project = load_project_state(database)
    if sha256_file(database) != revision:
        raise ValueError("读取期间项目发生变化，请重新查询。")
    source_hash = sha256_file(Path(project.source_workbook)) if project.source_workbook else None
    if source_hash is not None and source_hash != project.workbook_fingerprint:
        raise ValueError("源 Excel 已变化，请先 project rescan，再重新预览。")
    return project, revision, source_hash


def _key(database: Path, *, create: bool) -> bytes:
    path = database.with_name(f".{database.name}.conversation-key")
    if path.is_symlink():
        raise ValueError("计划密钥不能是符号链接。")
    if not path.exists() and create:
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(secrets.token_bytes(32))
    value = path.read_bytes()
    if len(value) != 32:
        raise ValueError("计划密钥缺失或损坏，请重新预览。")
    return value


def _normalize(project: RackProject, request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict) or set(request) - {
        "operation", "selector", "target", "start_u", "end_u", "text", "write_scope",
    }:
        raise ValueError("编辑请求包含未知字段。")
    operation = request.get("operation")
    if operation not in {"edit", "add"}:
        raise ValueError("operation 只支持 edit 或 add。")
    scope = request.get("write_scope")
    if scope not in {"working-copy", "original-authorized", "draft"}:
        raise ValueError("明确提供 write_scope：working-copy、original-authorized 或 draft；上传不代表授权覆盖原图。")
    if (project.source_workbook is None) != (scope == "draft"):
        raise ValueError("绑定 Excel 与 draft 编辑范围不能混用。")
    text = request.get("text")
    if text is not None and not isinstance(text, str):
        raise ValueError("text 必须是字符串。")
    start, end = request.get("start_u"), request.get("end_u")
    if (start is None) != (end is None):
        raise ValueError("必须同时指定 start_u 与 end_u。")
    if start is not None and (type(start) is not int or type(end) is not int):
        raise ValueError("U 位必须是整数。")
    if operation == "add":
        if "selector" in request or text is None or start is None:
            raise ValueError("新增需要 text、target 与 U 位，不接受 selector。")
        rack = unique_rack(project, request.get("target", {}))
        device_id = new_entity_id("DEV") if project.source_workbook else "allocated-on-commit"
    else:
        device = unique_device(project, request.get("selector", {}))
        rack = (unique_rack(project, request["target"]) if "target" in request
                else {"rack_id": device["rack_id"]})
        device_id = device["device_id"]
        if text is None and start is None and "target" not in request:
            raise ValueError("没有可预览的变更。")
        start = device["start_u"] if start is None else start
        end = device["end_u"] if end is None else end
    return {"operation": operation, "device_id": device_id, "rack_id": rack["rack_id"],
            "start_u": start, "end_u": end, "text": text, "write_scope": scope}


def _bound_plan(project: RackProject, change: dict[str, Any]) -> WritePlan:
    if change["operation"] == "add":
        return plan_device_add(project, change["rack_id"], change["start_u"], change["end_u"],
                               change["text"], device_id=change["device_id"])
    return plan_device_edit(project, change["device_id"], change["rack_id"],
                            change["start_u"], change["end_u"], display_text=change["text"])


def _draft_apply(database: Path, change: dict[str, Any]) -> RackProject:
    if change["operation"] == "add":
        return add_draft_device(database, change["rack_id"], change["start_u"],
                                change["end_u"], change["text"])
    return edit_draft_device(database, change["device_id"], rack_reference=change["rack_id"],
                             start_u=change["start_u"], end_u=change["end_u"],
                             display_text=change["text"])


def _description(project: RackProject, change: dict[str, Any]) -> dict[str, Any]:
    rack = next(rack for rack in project.racks if rack.rack_id == change["rack_id"])
    device = next((device for device in project.devices if device.device_id == change["device_id"]), None)
    old = next((placement for placement in project.placements if placement.device_id == change["device_id"]
                and placement.status == "active"), None)
    return {"operation": change["operation"], "device_id": change["device_id"],
            "before": None if old is None else {"rack_id": old.rack_id, "start_u": old.start_u,
                                                  "end_u": old.end_u, "text": device.display_text if device else None},
            "after": {"room": rack.source_sheet, "rack": rack.rack_name,
                      "rack_id": rack.rack_id, "start_u": change["start_u"], "end_u": change["end_u"],
                      "text": change["text"] if change["text"] is not None else device.display_text if device else None},
            "write_scope": change["write_scope"]}


def _preview_summary(database: Path, project: RackProject, change: dict[str, Any]) -> dict[str, Any]:
    description = _description(project, change)
    if project.source_workbook:
        plan = _bound_plan(project, change)
        if plan.conflicts:
            raise ValueError("; ".join(f"{item.code}: {item.message}" for item in plan.conflicts))
        description["write_plan"] = plan.to_dict()
    else:
        # Exercise exactly the existing draft validator on a disposable state copy.
        with tempfile.TemporaryDirectory(prefix="racktool-preview-") as directory:
            temporary = Path(directory) / "preview.sqlite"
            shutil.copy2(database, temporary)
            _draft_apply(temporary, change)
    return description


def preview_conversation_edit(database: Path, request: dict[str, Any], plan_path: Path) -> dict[str, Any]:
    """Persist an authenticated plan without modifying either business file or SQLite."""
    database = normalize_path(database)
    plan_path = normalize_path(plan_path)
    project, revision, source_hash = _state(database)
    change = _normalize(project, request)
    summary = _preview_summary(database, project, change)
    if sha256_file(database) != revision or (project.source_workbook and
            sha256_file(Path(project.source_workbook)) != source_hash):
        raise ValueError("预览期间项目或源文件变化，请重新预览。")
    payload = {"schema_version": 1, "database": str(database), "project_id": project.project_id,
               "database_sha256": revision, "source_sha256": source_hash,
               "nonce": secrets.token_hex(16), "request": request, "change": change, "summary": summary}
    token = hmac.new(_key(database, create=True), _json(payload), hashlib.sha256).hexdigest()
    envelope = {"payload": payload, "token": token}
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    with plan_path.open("x", encoding="utf-8") as stream:
        json.dump(envelope, stream, ensure_ascii=False, indent=2, sort_keys=True)
    return {"status": "previewed", "plan": str(plan_path), "token": token, "summary": summary,
            "next": "conversation apply DATABASE PLAN --token TOKEN --commit"}


def apply_conversation_edit(database: Path, plan_path: Path, token: str, *, commit: bool = False) -> dict[str, Any]:
    """Commit only the precise authenticated preview; never accept a replacement request."""
    if not commit:
        raise ValueError("apply 需要显式 --commit；只看预览不会写入。")
    database = normalize_path(database)
    if plan_path.stat().st_size > 2_000_000:
        raise ValueError("计划文件过大。")
    envelope = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "token"}:
        raise ValueError("计划结构不合法。")
    payload = envelope["payload"]
    expected = hmac.new(_key(database, create=False), _json(payload), hashlib.sha256).hexdigest()
    if not isinstance(token, str) or not isinstance(envelope["token"], str) or not (
        hmac.compare_digest(token, expected) and hmac.compare_digest(envelope["token"], expected)
    ):
        raise ValueError("预览 token 或计划内容不一致，请重新预览。")
    project, revision, source_hash = _state(database)
    if (payload["schema_version"] != 1 or payload["database"] != str(database)
            or payload["project_id"] != project.project_id or payload["database_sha256"] != revision
            or payload["source_sha256"] != source_hash):
        raise ValueError("计划已过期或属于另一个项目，请重新预览。")
    change = payload["change"]
    if _preview_summary(database, project, change) != payload["summary"]:
        raise ValueError("实际计划与已审阅摘要不同，请重新预览。")
    # A short-lived exclusive claim serializes this protocol; underlying Core validates again.
    lock = database.with_name(f".{database.name}.conversation-lock")
    marker_dir = database.with_name(f".{database.name}.conversation-applied")
    marker_dir.mkdir(exist_ok=True)
    marker = marker_dir / expected
    if marker.exists():
        raise ValueError("此预览已提交，不能重复执行。")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    warnings: list[str] = []
    try:
        if sha256_file(database) != revision or (project.source_workbook and
                sha256_file(Path(project.source_workbook)) != source_hash):
            raise ValueError("提交前项目或源文件变化，请重新预览。")
        if project.source_workbook:
            result = commit_write_plan(Path(project.source_workbook), database, _bound_plan(project, change))
            if result.status != "applied":
                return {"status": result.status, "message": result.message, "errors": list(result.errors),
                        "conflicts": [item.to_dict() for item in result.plan.conflicts], "warnings": warnings}
            backup = result.backup_path
            persisted = result.project
        else:
            persisted = _draft_apply(database, change)
            backup = None
        if persisted is None:
            warnings.append("编辑已提交；Core 未返回项目快照，请重新查询，勿重复提交。")
        # The Core has committed and verified the business state. Bookkeeping
        # failures must not turn that success into a rejected edit or invite retry.
        try:
            marker.touch(exist_ok=False)
        except OSError as error:
            warnings.append(f"编辑已提交；成功标记写入失败，请勿重复提交：{error}")

        def reported_hash(path: Path) -> str | None:
            try:
                return sha256_file(path)
            except OSError as error:
                warnings.append(f"编辑已提交；无法读取结果 Hash，请重新查询：{error}")
                return None
        return {"status": "applied", "project_id": project.project_id, "database": str(database),
                "database_sha256": reported_hash(database), "source_sha256": (
                    reported_hash(Path(project.source_workbook)) if project.source_workbook else None),
                "backup_path": backup, "summary": payload["summary"], "warnings": warnings,
                "created_device_ids": [item.device_id for item in persisted.devices
                                       if item.device_id not in {device.device_id for device in project.devices}] if persisted is not None else None,
                "next": "conversation query DATABASE --request QUERY.json; export DATABASE OUTPUT.xlsx"}
    finally:
        try:
            lock.unlink(missing_ok=True)
        except OSError as error:
            warnings.append(f"对话锁清理失败，请核对无写入任务后处理 {lock}：{error}")
