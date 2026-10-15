"""Build a portable root-SKILL ZIP containing only Core/CLI and pure Python dependencies."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PROJECT = Path(__file__).resolve().parents[1]
PACKAGES = {"openpyxl": "openpyxl", "et_xmlfile": "et_xmlfile", "PyYAML": "yaml"}
VERSIONS = {"openpyxl": "3.1.5", "et_xmlfile": "2.0.0", "PyYAML": "6.0.3"}
CORE_DIRECTORIES = {"core", "cli", "models", "persistence", "profiles"}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(output: Path, version: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version):
        raise ValueError("Invalid bundle version")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True,
    ).strip()
    dirty = bool(subprocess.check_output(
        ["git", "status", "--porcelain", "--", "."], cwd=PROJECT, text=True,
    ).strip())
    with tempfile.TemporaryDirectory(prefix="racktool-skill-build-") as temporary:
        root = Path(temporary)
        source = PROJECT / "skills" / "racktool"
        for path in source.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".py"}:
                target = root / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        # Ship the public, stdlib-only workflow check with the finished Skill.
        # It creates synthetic inputs outside the install directory, never private samples.
        workflow_check = root / "scripts" / "verify_skill_workflows.py"
        workflow_check.parent.mkdir(parents=True, exist_ok=True)
        workflow_check.write_bytes((PROJECT / "scripts" / "verify_skill_workflows.py").read_bytes())
        for path in (PROJECT / "src" / "racktool").rglob("*"):
            relative = path.relative_to(PROJECT / "src" / "racktool")
            if (path.is_file() and path.suffix in {".py", ".yaml"}
                    and (len(relative.parts) == 1 or relative.parts[0] in CORE_DIRECTORIES)):
                target = root / "core" / "src" / "racktool" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        dependencies = {}
        for distribution_name, module in PACKAGES.items():
            distribution = importlib.metadata.distribution(distribution_name)
            if distribution.version != VERSIONS[distribution_name]:
                raise ValueError(f"Install bundle-requirements.txt: {distribution_name} version differs")
            dependencies[distribution_name] = distribution.version
            for relative in distribution.files or []:
                name = relative.as_posix()
                # Include metadata/licenses; omit compiled PyYAML extensions and install records.
                allowed = ((relative.parts[0] == module and relative.suffix == ".py")
                           or (relative.parts[0].endswith(".dist-info")
                               and relative.name not in {"RECORD", "INSTALLER", "direct_url.json", "WHEEL"}))
                if not allowed or "__pycache__" in relative.parts:
                    continue
                target = root / "vendor" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(Path(distribution.locate_file(relative)).read_bytes())
        write_json(root / "bundle.json", {
            "name": "racktool", "bundle_version": version, "source_commit": commit,
            "source_dirty": dirty, "python_requires": ">=3.11", "dependencies": dependencies,
            "includes": ["RackCore", "CLI", "profiles", "Skill", "pure Python dependencies"],
            "excludes": ["GUI", "Python interpreter", "private data", "project SQLite"],
        })
        files = sorted(path for path in root.rglob("*") if path.is_file())
        write_json(root / "checksums.json", {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        })
        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(path for path in root.rglob("*") if path.is_file()):
                info = ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(build(args.output, args.version))
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
