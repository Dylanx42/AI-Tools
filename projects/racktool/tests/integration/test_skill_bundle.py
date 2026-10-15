from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from racktool.core import analyze_workbook
from tests.integration.test_room_export import make_rooms

PROJECT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("portable skill with spaces")
    archive = directory / "bundle.zip"
    subprocess.run([
        sys.executable, str(PROJECT / "scripts" / "build_skill_bundle.py"),
        "--version", "test.1", "--output", str(archive),
    ], check=True, capture_output=True, encoding="utf-8")
    with ZipFile(archive) as zipped:
        names = zipped.namelist()
        assert "SKILL.md" in names
        assert all(not any(part in {"gui", "samples", "tests", ".venv", "__pycache__"}
                           for part in Path(name).parts) for name in names)
        assert not any(name.endswith((".so", ".pyd", ".xlsx", ".sqlite")) for name in names)
        assert any("dist-info/" in name and "LICENSE" in name for name in names)
        zipped.extractall(directory / "racktool")
    expected = archive.with_suffix(".zip.sha256").read_text().split()[0]
    assert expected == hashlib.sha256(archive.read_bytes()).hexdigest()
    return directory / "racktool"


def run(bundle: Path, *arguments: str, success: bool = True) -> subprocess.CompletedProcess[str]:
    # -S removes site-packages; even an unrelated PYTHONPATH cannot replace bundled modules.
    env = dict(os.environ, PYTHONPATH=str(bundle.parent / "unrelated"), PYTHONIOENCODING="ascii")
    result = subprocess.run([
        sys.executable, "-S", str(bundle / "scripts" / "run.py"), *arguments,
    ], cwd=bundle.parent, env=env, encoding="utf-8", capture_output=True, check=False)
    assert (result.returncode == 0) is success, result.stderr + result.stdout
    return result


def test_bundle_is_detached_and_uses_only_pure_python_dependencies(bundle: Path) -> None:
    assert json.loads(run(bundle, "--verify").stdout) == {"verified": True}
    info = json.loads(run(bundle, "--bundle-info").stdout)
    assert info["bundle_version"] == "test.1"
    assert info["yaml_native_extension"] is False
    assert all(Path(path).is_relative_to(bundle) for path in info["loaded_from"].values())
    assert "project" in run(bundle, "--help").stdout
    run(bundle, "profile", "validate",
        str(bundle / "core" / "src" / "racktool" / "profiles" / "generic-mixed-axis.yaml"))
    run(bundle, "gui", success=False)


def test_bundle_includes_detached_workflow_verification(bundle: Path, tmp_path: Path) -> None:
    evidence = tmp_path / "workflow evidence"
    result = subprocess.run([
        sys.executable, "-S", str(bundle / "scripts" / "verify_skill_workflows.py"),
        "--runner", str(bundle / "scripts" / "run.py"), "--output", str(evidence),
    ], cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(tmp_path / "unrelated")),
        encoding="utf-8", capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((evidence / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed"


def test_bundle_runs_draft_edits_and_refuses_conflicts(bundle: Path, tmp_path: Path) -> None:
    database, output = tmp_path / "draft.sqlite", tmp_path / "empty.xlsx"
    run(bundle, "project", "create", str(database), "--count", "18", "--height", "42")
    run(bundle, "export", str(database), str(output))
    analyzed = analyze_workbook(output)
    assert sum(len(sheet.racks) for sheet in analyzed.sheets) == 36
    run(bundle, "project", "add-device", str(database), "--rack", "A01",
        "--start-u", "21", "--end-u", "22", "--text", "portable 测试")
    before = database.read_bytes()
    run(bundle, "project", "add-device", str(database), "--rack", "A01",
        "--start-u", "22", "--end-u", "23", "--text", "collision", success=False)
    assert database.read_bytes() == before
    state = json.loads(run(bundle, "project", "show", str(database)).stdout)
    device_id = state["devices"][0]["device_id"]
    run(bundle, "project", "edit-device", str(database), device_id,
        "--rack", "B18", "--start-u", "31", "--end-u", "32", "--text", "renamed 设备")
    run(bundle, "export", str(database), str(tmp_path / "edited.xlsx"))
    state = json.loads(run(bundle, "project", "show", str(database)).stdout)
    assert state["devices"][0]["device_id"] == device_id
    assert state["devices"][0]["display_text"] == "renamed 设备"


@pytest.mark.parametrize("rack_name", ["A01", "B01"])
def test_bundle_edits_bound_rooms_and_preserves_source_layout(
    bundle: Path, tmp_path: Path, rack_name: str,
) -> None:
    source = tmp_path / "original.xlsx"
    make_rooms(source)
    original = source.read_bytes()
    working = tmp_path / "working.xlsx"
    working.write_bytes(original)
    database = tmp_path / "portable.sqlite"
    run(bundle, "project", "import", str(working), str(database))
    state = json.loads(run(bundle, "project", "show", str(database)).stdout)
    rack_id = next(r["rack_id"] for r in state["racks"] if r["rack_name"] == rack_name)
    arguments = ("sync", "add-device", str(working), str(database), rack_id, "1", "2",
                 "--text", "portable-bound")
    before = working.read_bytes(), database.read_bytes()
    run(bundle, *arguments)
    assert before == (working.read_bytes(), database.read_bytes())
    run(bundle, *arguments, "--commit")
    state = json.loads(run(bundle, "project", "show", str(database)).stdout)
    device_id = next(d["device_id"] for d in state["devices"]
                     if d["display_text"] == "portable-bound")
    run(bundle, "sync", "rename", str(working), str(database), device_id,
        "--text", "portable-renamed", "--commit")
    run(bundle, "sync", "move", str(working), str(database), device_id,
        rack_id, "3", "4", "--commit")
    state = json.loads(run(bundle, "project", "show", str(database)).stdout)
    placement = next(p for p in state["placements"] if p["device_id"] == device_id)
    assert (placement["start_u"], placement["end_u"]) == (3, 4)
    output = tmp_path / "source-layout.xlsx"
    run(bundle, "export", str(database), str(output), "--layout", "source")
    with ZipFile(working) as before_zip, ZipFile(output) as after_zip:
        assert all(before_zip.read(name) == after_zip.read(name)
                   for name in before_zip.namelist() if name.startswith("xl/worksheets/"))
    assert source.read_bytes() == original


@pytest.mark.parametrize("change", ["modified", "missing", "extra"])
def test_bundle_integrity_rejects_corruption(bundle: Path, tmp_path: Path, change: str) -> None:
    import shutil

    copied = tmp_path / "damaged"
    shutil.copytree(bundle, copied)
    path = copied / "SKILL.md"
    if change == "modified":
        path.write_text("changed", encoding="utf-8")
    elif change == "missing":
        path.unlink()
    else:
        (copied / "extra.py").write_text("", encoding="utf-8")
    run(copied, "--verify", success=False)
    destination = tmp_path / "installed"
    result = subprocess.run([
        sys.executable, "-S", str(copied / "install.py"), "--destination", str(destination),
    ], encoding="utf-8", capture_output=True, check=False)
    assert result.returncode != 0 and not destination.exists()


def test_install_is_complete_and_preserves_existing_install(bundle: Path, tmp_path: Path) -> None:
    import shutil

    copied = tmp_path / "Finder-extracted"
    shutil.copytree(bundle, copied)
    for name in (".DS_Store", "Thumbs.db", "desktop.ini"):
        (copied / name).write_bytes(b"operating system metadata")
    run(copied, "--verify")
    destination = tmp_path / "skills with spaces" / "racktool"
    command = [sys.executable, "-S", str(copied / "install.py"), "--destination", str(destination)]
    subprocess.run(command, check=True, capture_output=True, encoding="utf-8")
    assert not (destination / ".DS_Store").exists()
    run(destination, "--verify")
    info = json.loads(run(destination, "--bundle-info").stdout)
    assert Path(info["loaded_from"]["racktool"]).is_relative_to(destination)
    before = (destination / "checksums.json").read_bytes()
    result = subprocess.run(command, capture_output=True, encoding="utf-8", check=False)
    assert result.returncode != 0
    assert (destination / "checksums.json").read_bytes() == before
