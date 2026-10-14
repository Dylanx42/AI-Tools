"""Run the bundled RackCore without a repository or a pip installation."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify() -> None:
    expected = json.loads((ROOT / "checksums.json").read_text(encoding="utf-8"))
    actual = {path.relative_to(ROOT).as_posix(): path for path in ROOT.rglob("*")
              if path.is_file() and path != ROOT / "checksums.json"
              and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    if set(actual) != set(expected):
        raise ValueError("包文件清单不一致；请重新解压完整安装包。")
    for name, digest in expected.items():
        if hashlib.sha256(actual[name].read_bytes()).hexdigest() != digest:
            raise ValueError(f"包文件校验失败：{name}")


def main() -> int:
    if sys.version_info < (3, 11):  # noqa: UP036 - standalone bootstrap
        print("RackTool Skill 需要 Python 3.11+。", file=sys.stderr)
        return 2
    if not (ROOT / "bundle.json").is_file():
        print("此入口需要完整独立包；仓库开发请使用 python -m racktool。", file=sys.stderr)
        return 2
    if sys.argv[1:] == ["--verify"]:
        try:
            verify()
        except (OSError, ValueError) as error:
            print(str(error), file=sys.stderr)
            return 2
        print(json.dumps({"verified": True}, ensure_ascii=False))
        return 0
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(ROOT / "core" / "src"), str(ROOT / "vendor")]
    os.environ["OPENPYXL_LXML"] = "False"
    os.environ["OPENPYXL_DEFUSEDXML"] = "False"
    if sys.argv[1:] == ["--bundle-info"]:
        import openpyxl
        import yaml

        import racktool

        info = json.loads((ROOT / "bundle.json").read_text(encoding="utf-8"))
        info["python"] = sys.version.split()[0]
        info["loaded_from"] = {
            "racktool": racktool.__file__, "openpyxl": openpyxl.__file__, "yaml": yaml.__file__,
        }
        info["yaml_native_extension"] = yaml.__with_libyaml__
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0
    if sys.argv[1:2] == ["gui"]:
        print("Skill 独立包不包含 GUI；请以对话调用 Core 命令。", file=sys.stderr)
        return 2
    from racktool.cli.main import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
