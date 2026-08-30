from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from racktool.core import scan_workbook


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="racktool", description="RackTool XLSX utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser(
        "inspect", help="emit a deterministic structural summary (not rack detection)"
    )
    inspect_parser.add_argument("workbook", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = scan_workbook(args.workbook)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
            return 0
    except (FileNotFoundError, OSError, ValueError) as error:
        parser.exit(2, f"racktool: error: {error}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
