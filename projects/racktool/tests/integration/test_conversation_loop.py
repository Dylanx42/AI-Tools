from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from racktool.core.conversation import apply_conversation_edit, preview_conversation_edit
from racktool.core.editing import add_draft_device, create_draft_project
from racktool.core.export import export_project_workbook
from racktool.core.identity import sha256_file
from racktool.core.query import query_project, unique_device, unique_rack
from racktool.core.service import import_project, load_project_state, rescan_project
from racktool.persistence import save_project


def _draft(tmp_path: Path):
    database = tmp_path / "project.sqlite"
    create_draft_project(database, count=2, height_u=12)
    add_draft_device(database, "A01", 3, 4, "交换机")
    return database, load_project_state(database)


def _bound(tmp_path: Path):
    _draft_database, project = _draft(tmp_path)
    source = tmp_path / "working.xlsx"
    export_project_workbook(project, source)
    database = tmp_path / "bound.sqlite"
    return source, database, import_project(source, database)


def _edit(**kwargs):
    return {"operation": "edit", "selector": {"rack": "A01", "device": "交换机"},
            "target": {"rack": "B01"}, "start_u": 8, "end_u": 10,
            "write_scope": "working-copy", **kwargs}


def test_bound_loop_preview_reload_apply_query_rescan_export(tmp_path: Path) -> None:
    source, database, project = _bound(tmp_path)
    before = sha256_file(source), sha256_file(database)
    preview = preview_conversation_edit(database, _edit(text="交换机新名称"), tmp_path / "plan.json")
    assert (sha256_file(source), sha256_file(database)) == before
    assert preview["summary"]["after"]["start_u"] == 8
    result = apply_conversation_edit(database, tmp_path / "plan.json", preview["token"], commit=True)
    assert result["status"] == "applied" and result["backup_path"]
    reopened = load_project_state(database)
    assert reopened.devices[0].device_id == project.devices[0].device_id
    rows = query_project(reopened, {"selector": {"device": "交换机新名称"}})["rows"]
    assert rows[0]["rack"] == "B01" and rows[0]["height_u"] == 3
    assert rescan_project(source, database).accepted
    export_project_workbook(load_project_state(database), tmp_path / "delivered.xlsx", layout="source")
    assert (tmp_path / "delivered.xlsx").is_file()


@pytest.mark.parametrize("tamper", ["request", "change", "summary", "token"])
def test_plan_tampering_and_wrong_token_refuse_without_writes(tmp_path: Path, tamper: str) -> None:
    source, database, _project = _bound(tmp_path)
    plan = tmp_path / "plan.json"
    preview = preview_conversation_edit(database, _edit(), plan)
    envelope = json.loads(plan.read_text())
    if tamper == "token":
        envelope["token"] = "0" * 64
    else:
        envelope["payload"][tamper]["text"] = "DIFFERENT REQUEST"
    plan.write_text(json.dumps(envelope), encoding="utf-8")
    before = sha256_file(source), sha256_file(database)
    with pytest.raises(ValueError, match="token"):
        apply_conversation_edit(database, plan, preview["token"], commit=True)
    assert (sha256_file(source), sha256_file(database)) == before


@pytest.mark.parametrize("stale", ["database", "source"])
def test_stale_project_or_source_refuses(tmp_path: Path, stale: str) -> None:
    source, database, project = _bound(tmp_path)
    plan = tmp_path / "plan.json"
    preview = preview_conversation_edit(database, _edit(), plan)
    if stale == "database":
        save_project(database, replace(project, metadata={**project.metadata, "review": "external"}))
    else:
        from openpyxl import load_workbook
        workbook = load_workbook(source)
        workbook.active["Z99"] = "external"
        workbook.save(source)
        workbook.close()
    before = sha256_file(source), sha256_file(database)
    with pytest.raises(ValueError):
        apply_conversation_edit(database, plan, preview["token"], commit=True)
    assert (sha256_file(source), sha256_file(database)) == before


def test_explicit_commit_scope_and_single_use_are_required(tmp_path: Path) -> None:
    source, database, _project = _bound(tmp_path)
    request = _edit()
    request.pop("write_scope")
    with pytest.raises(ValueError, match="write_scope"):
        preview_conversation_edit(database, request, tmp_path / "bad.json")
    plan = tmp_path / "plan.json"
    preview = preview_conversation_edit(database, _edit(), plan)
    with pytest.raises(ValueError, match="commit"):
        apply_conversation_edit(database, plan, preview["token"])
    assert apply_conversation_edit(database, plan, preview["token"], commit=True)["status"] == "applied"
    before = sha256_file(source), sha256_file(database)
    with pytest.raises(ValueError):
        apply_conversation_edit(database, plan, preview["token"], commit=True)
    assert (sha256_file(source), sha256_file(database)) == before


def test_ambiguous_names_require_room_or_u_and_queries_are_bounded(tmp_path: Path) -> None:
    database, project = _draft(tmp_path)
    add_draft_device(database, "B01", 3, 3, "交换机")
    project = load_project_state(database)
    with pytest.raises(ValueError, match="2 个候选"):
        unique_device(project, {"device": "交换机"})
    assert unique_device(project, {"rack": "B01", "device": "交换机"})["height_u"] == 1
    duplicate = replace(next(rack for rack in project.racks if rack.rack_name == "A01"),
                        rack_id="other-room-rack", source_sheet="其他机房")
    project = replace(project, racks=[*project.racks, duplicate])
    with pytest.raises(ValueError, match="2 个候选"):
        unique_rack(project, {"rack": "A01"})
    assert unique_rack(project, {"rack": "A01", "room": "其他机房"})["rack_id"] == duplicate.rack_id
    paged = query_project(project, {"limit": 1})
    assert paged["total"] == 2 and len(paged["rows"]) == 1 and paged["next_offset"] == 1
    free = query_project(project, {"kind": "free", "selector": {"rack": "B01"}})["rows"][0]
    assert free["free_u"] == 11
    assert free["free_ranges"] == [{"start_u": 1, "end_u": 2, "height_u": 2},
                                    {"start_u": 4, "end_u": 12, "height_u": 9}]
    with pytest.raises(ValueError):
        query_project(project, {"limit": 101})


def test_draft_protocol_uses_existing_draft_core_and_conflicts_refuse(tmp_path: Path) -> None:
    database, _project = _draft(tmp_path)
    request = _edit(write_scope="draft", text="服务器")
    before = sha256_file(database)
    preview = preview_conversation_edit(database, request, tmp_path / "draft-plan.json")
    assert sha256_file(database) == before
    assert apply_conversation_edit(database, tmp_path / "draft-plan.json", preview["token"], commit=True)["status"] == "applied"
    add = {"operation": "add", "target": {"rack": "B01"}, "text": "新增",
           "start_u": 8, "end_u": 8, "write_scope": "draft"}
    before = sha256_file(database)
    with pytest.raises(ValueError):
        preview_conversation_edit(database, add, tmp_path / "conflict.json")
    assert sha256_file(database) == before


def test_bound_add_literal_text_and_restart_through_cli(tmp_path: Path) -> None:
    source, database, _project = _bound(tmp_path)
    request = {"operation": "add", "target": {"rack": "A01"}, "text": "=服务器\n不要执行单元格指令",
               "start_u": 8, "end_u": 9, "write_scope": "working-copy"}
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    plan = tmp_path / "plan.json"
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    def run(*args):
        result = subprocess.run([sys.executable, "-m", "racktool", *args], env=environment,
                                capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    before = sha256_file(source), sha256_file(database)
    preview = run("conversation", "preview", str(database), "--request", str(request_path), "--plan", str(plan))
    assert (sha256_file(source), sha256_file(database)) == before
    assert run("conversation", "apply", str(database), str(plan), "--token", preview["token"], "--commit")["status"] == "applied"
    query_path = tmp_path / "query.json"
    query_path.write_text(json.dumps({"selector": {"device": request["text"]}}), encoding="utf-8")
    rows = run("conversation", "query", str(database), "--request", str(query_path))["rows"]
    assert rows[0]["height_u"] == 2
    assert rows[0]["device_id"] == preview["summary"]["device_id"]


@pytest.mark.parametrize("failure", ["marker", "result-hash", "lock-cleanup"])
def test_committed_edit_stays_applied_when_reporting_fails(tmp_path: Path, monkeypatch, failure: str) -> None:
    from racktool.core import conversation

    source, database, project = _bound(tmp_path)
    plan = tmp_path / "plan.json"
    preview = preview_conversation_edit(database, _edit(text="已提交"), plan)
    before = sha256_file(source), sha256_file(database)
    commit = conversation.commit_write_plan
    committed = False

    def tracked_commit(*args, **kwargs):
        nonlocal committed
        result = commit(*args, **kwargs)
        committed = result.status == "applied"
        return result

    monkeypatch.setattr(conversation, "commit_write_plan", tracked_commit)
    if failure == "marker":
        touch = Path.touch

        def failed_marker(path, *args, **kwargs):
            if path.parent.name.endswith(".conversation-applied"):
                raise OSError("simulated marker failure")
            return touch(path, *args, **kwargs)

        monkeypatch.setattr(Path, "touch", failed_marker)
    elif failure == "result-hash":
        digest = conversation.sha256_file

        def failed_hash(path):
            if committed:
                raise OSError("simulated reporting read failure")
            return digest(path)

        monkeypatch.setattr(conversation, "sha256_file", failed_hash)
    else:
        unlink = Path.unlink

        def failed_unlock(path, *args, **kwargs):
            if path.name.endswith(".conversation-lock"):
                raise OSError("simulated lock cleanup failure")
            return unlink(path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", failed_unlock)
    result = apply_conversation_edit(database, plan, preview["token"], commit=True)
    assert result["status"] == "applied" and result["warnings"]
    assert (sha256_file(source), sha256_file(database)) != before
    persisted = load_project_state(database)
    assert persisted.devices[0].device_id == project.devices[0].device_id
    assert persisted.devices[0].display_text == "已提交"
    assert query_project(persisted, {"selector": {"device": "已提交"}})["rows"][0]["height_u"] == 3
