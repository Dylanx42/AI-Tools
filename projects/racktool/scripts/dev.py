"""Create and verify an isolated RackTool development environment."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ENVIRONMENT = PROJECT / ".venv"
PYTHON = ENVIRONMENT / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(*arguments: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(arguments), flush=True)
    subprocess.run(arguments, cwd=PROJECT, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "check"))
    parser.add_argument("--gui", action="store_true", help="Install/check Qt widgets offscreen")
    parser.add_argument(
        "--require-private", action="store_true", help="Fail if private regression data is missing"
    )
    args = parser.parse_args()
    if sys.version_info < (3, 11):  # noqa: UP036 - bootstrap runs before the package is installed
        parser.error("Python 3.11 or newer is required")
    if args.command == "setup":
        if args.require_private:
            parser.error("--require-private applies to check only")
        if not PYTHON.is_file():
            venv.EnvBuilder(with_pip=True).create(ENVIRONMENT)
        run(
            str(PYTHON), "-m", "pip", "install", "--constraint",
            str(PROJECT / "cloud-constraints.txt"), "-e", ".[dev,gui]" if args.gui else ".[dev]",
        )
        run(str(PYTHON), "-m", "pip", "check")
        print(f"Environment ready: {PYTHON}")
        return 0
    if not PYTHON.is_file():
        parser.error("Run setup first")
    private = PROJECT / "samples" / "private"
    workbook = private / "机柜图-0827.xlsx"
    expected = sorted((private / "golden").glob("*/expected.json"))
    if args.require_private and (not workbook.is_file() or len(expected) < 2):
        parser.error("Private workbook and two Sheet-scoped Golden cases have not been installed")
    print(
        f"Private workbook installed: {workbook.is_file()}; Golden cases found: {len(expected)}. "
        "Missing Golden data is skipped by pytest; this does not prove real-layout acceptance.",
        flush=True,
    )
    run(str(PYTHON), "-m", "pip", "check")
    with tempfile.TemporaryDirectory(prefix="racktool-check-") as directory:
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["XDG_CACHE_HOME"] = directory
        env["XDG_RUNTIME_DIR"] = directory
        run(str(PYTHON), "-m", "pytest", "-ra", env=env)
        run(str(PYTHON), "-m", "ruff", "check", ".")
        run(str(PYTHON), "-m", "mypy", "src")
        run(str(PYTHON), "-m", "racktool", "--help")
        if args.gui:
            run(str(PYTHON), str(PROJECT / "scripts" / "gui_smoke.py"), env=env)
    print("Automated checks passed. Desktop/Excel/WPS manual validation remains pending.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode)
