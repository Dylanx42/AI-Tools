"""Thin argparse adapter for read-only layout adaptation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from racktool.profiles.adaptation import check_layout, inspect_layout, propose_layout


def register_layout_cli(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("layout", help="inspect, propose, or check unfamiliar layouts")
    commands = parser.add_subparsers(dest="layout_command", required=True)
    inspect = commands.add_parser("inspect", help="explain room candidates without choosing rules")
    propose = commands.add_parser("propose", help="generate validated YAML from reviewed geometry")
    check = commands.add_parser("check", help="validate a Profile and dry-run against unchanged input")
    for command in (inspect, propose, check):
        command.add_argument("workbook", type=Path)
        command.add_argument("--expected-sha256", help="reject input changed since inspection")
    propose.add_argument("output", type=Path)
    propose.add_argument("--sheet", required=True)
    propose.add_argument("--profile-id", required=True)
    for name in ("title-range", "left-axis", "right-axis", "device-range"):
        propose.add_argument(f"--{name}")
    for name in ("start-row", "end-row"):
        propose.add_argument(f"--{name}", type=int)
    propose.add_argument("--direction", choices=("ascending", "descending"))
    check.add_argument("profile", type=Path)


def handle_layout_cli(args: argparse.Namespace) -> int:
    if args.layout_command == "inspect":
        result = inspect_layout(args.workbook, expected_sha256=args.expected_sha256)
    elif args.layout_command == "check":
        result = check_layout(args.workbook, args.profile, expected_sha256=args.expected_sha256)
    else:
        hints = {
            key: value for key, value in (
                ("title_range", args.title_range), ("left_axis", args.left_axis),
                ("right_axis", args.right_axis), ("device_range", args.device_range),
                ("start_row", args.start_row), ("end_row", args.end_row),
                ("direction", args.direction),
            ) if value is not None
        }
        result = propose_layout(
            args.workbook, args.output, sheet_name=args.sheet, profile_id=args.profile_id,
            hints=hints or None, expected_sha256=args.expected_sha256,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    # Inspect is informational; propose/check distinguish a usable rule from review.
    return 0 if args.layout_command == "inspect" or result["status"] == "ready_for_import" else 1
