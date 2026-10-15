"""Thin JSON-file CLI transport for conversational clients."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from racktool.core.conversation import apply_conversation_edit, preview_conversation_edit
from racktool.core.query import query_project
from racktool.core.service import load_project_state


def register_conversation_cli(subparsers: Any) -> None:
    parser = subparsers.add_parser("conversation", help="bounded queries and restart-safe reviewed edits")
    commands = parser.add_subparsers(dest="conversation_command", required=True)
    query = commands.add_parser("query", help="query devices, cabinets, or free U intervals")
    query.add_argument("database", type=Path)
    query.add_argument("--request", type=Path, required=True, help="UTF-8 JSON query request")
    preview = commands.add_parser("preview", help="validate edit intent and save an authenticated plan")
    preview.add_argument("database", type=Path)
    preview.add_argument("--request", type=Path, required=True, help="UTF-8 JSON edit request")
    preview.add_argument("--plan", type=Path, required=True, help="new output plan file; no overwrite")
    apply = commands.add_parser("apply", help="commit the exact previously reviewed plan")
    apply.add_argument("database", type=Path)
    apply.add_argument("plan", type=Path)
    apply.add_argument("--token", required=True)
    apply.add_argument("--commit", action="store_true")


def _request(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 1_000_000:
        raise ValueError("请求文件过大。")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("请求必须是 JSON 对象。")
    return value


def handle_conversation_cli(args: argparse.Namespace) -> int:
    try:
        if args.conversation_command == "query":
            result = query_project(load_project_state(args.database), _request(args.request))
        elif args.conversation_command == "preview":
            result = preview_conversation_edit(args.database, _request(args.request), args.plan)
        else:
            result = apply_conversation_edit(args.database, args.plan, args.token, commit=args.commit)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(json.dumps({"status": "rejected", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"ok", "previewed", "applied"} else 2
