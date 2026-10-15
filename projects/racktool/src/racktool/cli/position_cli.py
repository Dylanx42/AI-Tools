"""Argparse adapter for validated position-table round trips."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from racktool.core.position_table import apply_position_table, preview_position_table


def register_position_cli(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("position-table", help="preview or apply an edited exported table")
    commands = parser.add_subparsers(dest="position_command", required=True)
    preview = commands.add_parser("preview", help="validate table changes without writing")
    apply = commands.add_parser("apply", help="apply exactly the validated table revision")
    for command in (preview, apply):
        command.add_argument("database", type=Path)
        command.add_argument("workbook", type=Path)
        command.add_argument("--sheet", help="position worksheet when several are present")
    apply.add_argument("--token", required=True, help="preview_token from the accepted preview")


def handle_position_cli(args: argparse.Namespace) -> int:
    if args.position_command == "preview":
        plan = preview_position_table(args.database, args.workbook, args.sheet)
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if plan.accepted else 2
    result = apply_position_table(
        args.database, args.workbook, args.sheet, expected_preview_token=args.token,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.status in {"applied", "unchanged"} else 2
