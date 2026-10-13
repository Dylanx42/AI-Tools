"""Generate an empty A/B rack workbook using RackCore's standard exporter.

Run from the project after installing it: python scripts/generate_empty_racks.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from racktool.core import create_empty_rack_project, export_project_workbook


def main() -> None:
    parser = argparse.ArgumentParser(description="生成两排单格设备位置的空机柜表")
    parser.add_argument("--count", type=int, default=18, help="每排机柜数量（默认 18）")
    parser.add_argument("--height", type=int, default=42, help="机柜高度 U（默认 42）")
    parser.add_argument("--output", type=Path, help="输出 .xlsx 路径")
    parser.add_argument("--overwrite", action="store_true", help="允许替换指定输出文件")
    args = parser.parse_args()
    output = args.output or Path(
        f"空机柜表_A01-A{args.count:02d}_B01-B{args.count:02d}_{args.height}U_单格版.xlsx"
    )
    try:
        project = create_empty_rack_project(args.count, args.height)
        destination = export_project_workbook(project, output, overwrite=args.overwrite)
    except (OSError, ValueError) as error:
        parser.exit(1, f"生成失败：{error}\n")
    print(destination)


if __name__ == "__main__":
    main()
