"""Install the repository-owned RackTool skill for a local Codex agent."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path.home() / ".agents" / "skills" / "racktool")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    source = project / "skills" / "racktool"
    destination = args.destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        parser.error("目标已存在，保留原 Skill；请选择新的 --destination 或先自行备份。")
    shutil.copytree(source, destination)
    (destination / "runtime.json").write_text(json.dumps({"project_root": str(project)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Skill installed: {destination}")
    print("在支持 skills 的本地 Codex 环境加载/刷新后，用 $racktool 发出自然语言请求。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
