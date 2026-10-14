"""Install an extracted, complete Skill bundle; never overwrite an existing install."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("codex", "trae-cn"), default="codex")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    folder = ".agents" if args.agent == "codex" else ".trae-cn"
    destination = (args.destination or Path.home() / folder / "skills" / "racktool")
    destination = destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        parser.error("目标已存在，已保留原安装；先将旧 Skill 移出技能目录备份，或指定新目录。")
    resolved_destination = destination.resolve()
    if resolved_destination == source or source in resolved_destination.parents:
        parser.error("安装目标不能位于待安装包内部。")
    spec = importlib.util.spec_from_file_location("bundle_runner", source / "scripts" / "run.py")
    if spec is None or spec.loader is None:
        parser.error("缺少运行入口，请重新解压完整包。")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    try:
        runner.verify()
    except (OSError, ValueError) as error:
        parser.error(str(error))
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"Skill installed: {destination}")
    print("刷新/重启 Agent，要求它运行 scripts/run.py --verify 和 --bundle-info 后再开始验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
