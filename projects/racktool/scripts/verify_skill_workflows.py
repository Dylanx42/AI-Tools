"""Reproduce public CLI workflows without an Agent, Office, Qt, or private inputs.

This is a deterministic tool smoke test. It does not certify Agent discovery,
natural-language behavior, or Excel/WPS visual acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_workbook(path: Path) -> None:
    """Independent 12U fixture: Room-Z descends, Room-A ascends, same device text."""
    files = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<workbook xmlns="{NS}" xmlns:r="{REL}"><sheets>'
        '<sheet name="Room-Z" sheetId="1" r:id="rId1"/>'
        '<sheet name="Room-A" sheetId="2" r:id="rId2"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{REL}/worksheet" Target="worksheets/sheet1.xml"/>'
        f'<Relationship Id="rId2" Type="{REL}/worksheet" Target="worksheets/sheet2.xml"/></Relationships>',
    }
    for number, cabinet, ascending, occupied in ((1, "A01", False, (9, 10)), (2, "B01", True, (6, 7))):
        start = occupied[0] + 3 if ascending else 16 - occupied[1]
        rows = [f'<row r="3"><c r="C3" t="inlineStr"><is><t>{cabinet}</t></is></c></row>']
        for row, unit in enumerate(range(1, 13) if ascending else range(12, 0, -1), 4):
            device = (f'<c r="D{row}" t="inlineStr"><is><t>SYNTHETIC-SERVER</t></is></c>'
                      if row == start else "")
            rows.append(f'<row r="{row}"><c r="C{row}" t="n"><v>{unit}</v></c>{device}'
                        f'<c r="E{row}" t="n"><v>{unit}</v></c></row>')
        files[f"xl/worksheets/sheet{number}.xml"] = (
            f'<worksheet xmlns="{NS}"><sheetData>{"".join(rows)}</sheetData>'
            '<mergeCells count="2"><mergeCell ref="C3:E3"/>'
            f'<mergeCell ref="D{start}:D{start + 1}"/></mergeCells></worksheet>'
        )
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)


def _edit_position_table(path: Path, device_id: str, values: dict[str, str | int]) -> None:
    """Mimic user edits of the exported position sheet, preserving hidden metadata."""
    with ZipFile(path) as archive:
        entries = {info.filename: (info, archive.read(info.filename)) for info in archive.infolist()}
    changed = False
    for name, (info, raw) in list(entries.items()):
        if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
            continue
        sheet = ET.fromstring(raw)
        for row in sheet.findall(f"{{{NS}}}sheetData/{{{NS}}}row"):
            cells = {cell.attrib["r"].rstrip("0123456789"): cell for cell in row}
            identity = "".join(cells.get("H", ET.Element("missing")).itertext())
            if identity != device_id:
                continue
            for column, value in values.items():
                cell = cells[column]
                for child in list(cell):
                    cell.remove(child)
                cell.attrib["t"] = "n" if isinstance(value, int) else "inlineStr"
                if isinstance(value, int):
                    ET.SubElement(cell, f"{{{NS}}}v").text = str(value)
                else:
                    ET.SubElement(ET.SubElement(cell, f"{{{NS}}}is"), f"{{{NS}}}t").text = value
            changed = True
        if changed:
            entries[name] = info, ET.tostring(sheet, encoding="utf-8", xml_declaration=True)
            break
    if not changed:
        raise AssertionError("Synthetic device ID absent from exported position table")
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for info, raw in entries.values():
            archive.writestr(info, raw)


def verify(output: Path, runner: Path | None = None) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("Use a new evidence directory; existing data is never overwritten")
    output.mkdir(parents=True)
    prefix = [sys.executable, "-S", str(runner.resolve())] if runner else [sys.executable, "-m", "racktool"]
    events: list[dict[str, Any]] = []
    checks: list[str] = []
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", RACKTOOL_DATA_DIR=str(output / "runtime"))

    def cli(*arguments: object, success: bool = True) -> dict[str, Any]:
        arguments = tuple(str(argument) for argument in arguments)
        result = subprocess.run(prefix + list(arguments), capture_output=True, text=True,
                                encoding="utf-8", env=environment, check=False)
        if (result.returncode == 0) != success:
            raise AssertionError(f"Command {arguments} exited {result.returncode}: {result.stdout} {result.stderr}")
        value = json.loads(result.stdout)
        events.append({"command": list(arguments), "exit_code": result.returncode, "result": value})
        return value

    def request(name: str, value: dict[str, Any]) -> Path:
        path = output / f"{name}.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def query(kind: str, selector: dict[str, Any]) -> dict[str, Any]:
        return cli("conversation", "query", database, "--request", request(f"query-{len(events)}", {
            "kind": kind, "selector": selector,
        }))

    original, working, database = output / "original.xlsx", output / "working.xlsx", output / "project.sqlite"
    make_workbook(original)
    original_hash = _hash(original)
    working.write_bytes(original.read_bytes())
    inspected = cli("layout", "inspect", working)
    assert inspected["source_sha256"] == original_hash
    profile, profiled_database = output / "reviewed-room.yaml", output / "reviewed-room.sqlite"
    proposed = cli("layout", "propose", working, profile, "--sheet", "Room-A", "--profile-id", "synthetic-reviewed",
                   "--title-range", "C3:E3", "--left-axis", "C", "--right-axis", "E", "--device-range", "D4:D15",
                   "--start-row", 4, "--end-row", 15, "--direction", "ascending", "--expected-sha256", original_hash)
    assert proposed["status"] == "ready_for_import"
    assert cli("layout", "check", working, profile, "--expected-sha256", original_hash)["status"] == "ready_for_import"
    cli("project", "import", working, profiled_database, "--profile", profile, "--expected-sha256", original_hash)
    selected = cli("project", "show", profiled_database)
    assert len(selected["racks"]) == 1 and selected["racks"][0]["source_sheet"] == "Room-A"
    assert len(selected["devices"]) == 1 and _hash(working) == original_hash
    checks.append("layout-inspect-reviewed-fixed-profile-check-import-hash")
    cli("project", "import", working, database)
    rows = query("devices", {})["rows"]
    assert sorted((row["room"], row["rack"], row["start_u"], row["end_u"]) for row in rows) == [
        ("Room-A", "B01", 6, 7), ("Room-Z", "A01", 9, 10),
    ]
    identities = {row["room"]: row["device_id"] for row in rows}
    assert {(row["room"], row["direction"]) for row in query("racks", {})["rows"]} == {
        ("Room-Z", "descending"), ("Room-A", "ascending"),
    }
    assert query("free", {"room": "Room-A"})["rows"][0]["free_ranges"] == [
        {"start_u": 1, "end_u": 5, "height_u": 5}, {"start_u": 8, "end_u": 12, "height_u": 5},
    ]
    checks.append("read-query-free-mixed-directions")
    before = _hash(working), _hash(database)
    ambiguous = request("ambiguous", {"operation": "edit", "selector": {"device": "SYNTHETIC-SERVER"},
                                       "text": "should-not-apply", "write_scope": "working-copy"})
    cli("conversation", "preview", database, "--request", ambiguous, "--plan", output / "ambiguous-plan.json", success=False)
    assert before == (_hash(working), _hash(database))
    checks.append("ambiguous-edit-refused-without-writing")
    edit = request("move-resize", {"operation": "edit", "selector": {"room": "Room-Z", "rack": "A01"},
                                   "target": {"room": "Room-A", "rack": "B01"}, "start_u": 2, "end_u": 4,
                                   "text": "MOVED-SYNTHETIC", "write_scope": "working-copy"})
    plan = output / "move-plan.json"
    preview = cli("conversation", "preview", database, "--request", edit, "--plan", plan)
    assert preview["status"] == "previewed" and before == (_hash(working), _hash(database))
    cli("conversation", "apply", database, plan, "--token", "invalid", "--commit", success=False)
    assert before == (_hash(working), _hash(database))
    assert cli("conversation", "apply", database, plan, "--token", preview["token"], "--commit")["status"] == "applied"
    after = query("devices", {"device": "MOVED-SYNTHETIC"})["rows"][0]
    assert (after["device_id"], after["room"], after["start_u"], after["end_u"]) == (
        identities["Room-Z"], "Room-A", 2, 4,
    )
    checks.append("preview-no-writes-token-rejected-cross-room-resize-id-preserved")
    stale_before = _hash(working), _hash(database)
    cli("conversation", "apply", database, plan, "--token", preview["token"], "--commit", success=False)
    assert stale_before == (_hash(working), _hash(database))
    conflict = request("occupied", {"operation": "edit", "selector": {"device": "MOVED-SYNTHETIC"},
                                     "start_u": 6, "end_u": 8, "write_scope": "working-copy"})
    cli("conversation", "preview", database, "--request", conflict, "--plan", output / "conflict-plan.json", success=False)
    assert stale_before == (_hash(working), _hash(database))
    checks.append("replay-and-overlap-refused")
    exported = output / "positions.xlsx"
    cli("export", database, exported, "--layout", "source")
    with ZipFile(working) as source, ZipFile(exported) as result:
        assert all(source.read(name) == result.read(name) for name in source.namelist()
                   if name.startswith("xl/worksheets/"))
    _edit_position_table(exported, identities["Room-Z"], {
        "B": "RETURNED-SYNTHETIC", "C": "A01", "D": "1-2U", "E": 2, "F": "Room-Z",
    })
    before = _hash(working), _hash(database)
    table_preview = cli("position-table", "preview", database, exported)
    assert table_preview["accepted"] is True and len(table_preview["changes"]) == 1
    assert before == (_hash(working), _hash(database))
    assert cli("position-table", "apply", database, exported, "--token", table_preview["preview_token"])["status"] == "applied"
    returned = query("devices", {"device": "RETURNED-SYNTHETIC"})["rows"][0]
    assert (returned["device_id"], returned["room"], returned["rack"], returned["start_u"], returned["end_u"]) == (
        identities["Room-Z"], "Room-Z", "A01", 1, 2,
    )
    before = _hash(working), _hash(database)
    cli("position-table", "preview", database, exported, success=False)
    assert before == (_hash(working), _hash(database))
    assert _hash(original) == original_hash
    checks.append("source-layout-export-table-return-stale-table-rejected-original-unchanged")
    report = {"status": "passed", "scope": "scripted-cli-synthetic", "checks": checks,
              "original_sha256": original_hash, "runner": str(runner) if runner else "python -m racktool",
              "agent_manual_acceptance": {"Codex": "pending", "WorkBuddy": "pending", "TRAE": "pending"},
              "excel_wps_visual_acceptance": "pending"}
    (output / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new isolated evidence directory")
    parser.add_argument("--runner", type=Path, help="installed full Skill scripts/run.py (runs with -S)")
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.output, arguments.runner), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
