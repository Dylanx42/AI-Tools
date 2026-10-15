from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from racktool.cli.conversation_cli import handle_conversation_cli, register_conversation_cli
from racktool.cli.layout_cli import handle_layout_cli, register_layout_cli
from racktool.cli.position_cli import handle_position_cli, register_position_cli
from racktool.core import (
    add_draft_device,
    add_draft_rack,
    analyze_workbook,
    create_draft_project,
    edit_draft_device,
    export_analysis_package,
    export_project_workbook,
    scan_workbook,
)
from racktool.core.service import (
    commit_write_plan,
    import_project,
    load_project_state,
    rescan_project,
)
from racktool.core.sync import (
    plan_device_add,
    plan_device_edit,
    plan_device_move,
    plan_device_rename,
)
from racktool.profiles import apply_profile, fingerprint_workbook, load_profile, select_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="racktool", description="RackTool XLSX utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_conversation_cli(subparsers)
    register_layout_cli(subparsers)
    register_position_cli(subparsers)
    inspect_parser = subparsers.add_parser(
        "inspect", help="emit a deterministic structural summary (not rack detection)"
    )
    inspect_parser.add_argument("workbook", type=Path)
    analyze_parser = subparsers.add_parser(
        "analyze", help="emit explainable U-axis, rack, and device candidates"
    )
    analyze_parser.add_argument("workbook", type=Path)
    package_parser = subparsers.add_parser(
        "analysis-package", help="export a read-only ZIP for unfamiliar layout adaptation"
    )
    package_parser.add_argument("workbook", type=Path)
    package_parser.add_argument("output", type=Path)
    package_parser.add_argument(
        "--include-source", action="store_true", help="include a complete copy of the source workbook"
    )
    package_parser.add_argument("--force", action="store_true", help="replace an existing package")
    profile_parser = subparsers.add_parser(
        "profile", help="validate, match, fingerprint, or apply a YAML layout Profile"
    )
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", required=True)
    validate_parser = profile_subparsers.add_parser("validate", help="validate a YAML Profile")
    validate_parser.add_argument("profile", type=Path)
    fingerprint_parser = profile_subparsers.add_parser(
        "fingerprint", help="emit a deterministic workbook/layout fingerprint"
    )
    fingerprint_parser.add_argument("workbook", type=Path)
    match_parser = profile_subparsers.add_parser(
        "match", help="score a Profile against an analyzed workbook without applying it"
    )
    match_parser.add_argument("workbook", type=Path)
    match_parser.add_argument("profile", type=Path)
    apply_parser = profile_subparsers.add_parser(
        "apply",
        help="apply a Profile; defaults to dry-run and never writes the source workbook",
    )
    apply_parser.add_argument("workbook", type=Path)
    apply_parser.add_argument("profile", type=Path)
    apply_parser.add_argument(
        "--commit",
        action="store_true",
        help="emit the applied analysis JSON instead of a dry-run selection",
    )
    apply_parser.add_argument(
        "--force",
        action="store_true",
        help="apply a review_required match after explicit confirmation",
    )
    project_parser = subparsers.add_parser("project", help="import or rescan stable rack/device identities")
    project_subparsers = project_parser.add_subparsers(dest="project_command", required=True)
    create_parser = project_subparsers.add_parser("create", help="create a new editable A/B rack project")
    create_parser.add_argument("database", type=Path)
    create_parser.add_argument("--count", type=int, default=18, help="cabinets per row (default: 18)")
    create_parser.add_argument("--height", type=int, default=42, help="rack height in U (default: 42)")
    show_parser = project_subparsers.add_parser("show", help="show saved identities and placements")
    show_parser.add_argument("database", type=Path)
    rack_parser = project_subparsers.add_parser("add-rack", help="append a cabinet to a new project")
    rack_parser.add_argument("database", type=Path)
    rack_parser.add_argument("name")
    rack_parser.add_argument("--height", type=int, default=42)
    rack_parser.add_argument("--row", type=int, default=1, help="one-based rack row, or the next new row")
    add_parser = project_subparsers.add_parser("add-device", help="add a placed device to a new project")
    add_parser.add_argument("database", type=Path)
    add_parser.add_argument("--rack", required=True, help="cabinet ID or unique name")
    add_parser.add_argument("--start-u", type=int, required=True)
    add_parser.add_argument("--end-u", type=int, required=True)
    add_parser.add_argument("--text", required=True, help="device display text; original newlines are kept")
    edit_parser = project_subparsers.add_parser("edit-device", help="edit a new project's device text or location")
    edit_parser.add_argument("database", type=Path)
    edit_parser.add_argument("device_id")
    edit_parser.add_argument("--text")
    edit_parser.add_argument("--rack", help="cabinet ID or unique name")
    edit_parser.add_argument("--start-u", type=int)
    edit_parser.add_argument("--end-u", type=int)
    import_parser = project_subparsers.add_parser(
        "import",
        help="create a SQLite project from a workbook",
        allow_abbrev=False,
    )
    import_parser.add_argument("workbook", type=Path)
    import_parser.add_argument("database", type=Path)
    import_parser.add_argument("--expected-sha256", help="source hash from the checked layout")
    import_parser.add_argument(
        "--profile",
        type=Path,
        help="load and persist a validated YAML layout Profile",
    )
    rescan_parser = project_subparsers.add_parser("rescan", help="rescan a workbook against an existing SQLite project")
    rescan_parser.add_argument("workbook", type=Path)
    rescan_parser.add_argument("database", type=Path)
    sync_parser = subparsers.add_parser("sync", help="plan or apply a safe workbook write-back")
    sync_subparsers = sync_parser.add_subparsers(dest="sync_command", required=True)
    bound_edit = sync_subparsers.add_parser("edit", help="safely resize, move, or rename a bound device")
    bound_edit.add_argument("workbook", type=Path)
    bound_edit.add_argument("database", type=Path)
    bound_edit.add_argument("device_id")
    bound_edit.add_argument("rack_id")
    bound_edit.add_argument("start_u", type=int)
    bound_edit.add_argument("end_u", type=int)
    bound_edit.add_argument("--text", help="optional literal replacement text")
    bound_edit.add_argument("--commit", action="store_true")
    add_sync = sync_subparsers.add_parser("add-device", help="plan or safely add a device to a bound XLSX")
    add_sync.add_argument("workbook", type=Path)
    add_sync.add_argument("database", type=Path)
    add_sync.add_argument("rack_id")
    add_sync.add_argument("start_u", type=int)
    add_sync.add_argument("end_u", type=int)
    add_sync.add_argument("--text", required=True)
    add_sync.add_argument("--commit", action="store_true", help="commit after backups and validation")
    rename_sync = sync_subparsers.add_parser("rename", help="plan or safely edit device text in a bound XLSX")
    rename_sync.add_argument("workbook", type=Path)
    rename_sync.add_argument("database", type=Path)
    rename_sync.add_argument("device_id")
    rename_sync.add_argument("--text", required=True)
    rename_sync.add_argument("--commit", action="store_true", help="commit after backups and validation")
    move_parser = sync_subparsers.add_parser("move", help="move a device to a rack/U range")
    move_parser.add_argument("workbook", type=Path)
    move_parser.add_argument("database", type=Path)
    move_parser.add_argument("device_id")
    move_parser.add_argument("rack_id")
    move_parser.add_argument("start_u", type=int)
    move_parser.add_argument("end_u", type=int)
    move_parser.add_argument(
        "--commit",
        action="store_true",
        help="apply the write-back after backup, temporary write, reload, and validation",
    )
    export_parser = subparsers.add_parser(
        "export", help="export a project as rack diagram and device position sheets"
    )
    export_parser.add_argument("database", type=Path)
    export_parser.add_argument("output", type=Path)
    export_parser.add_argument(
        "--layout", choices=("standard", "source"), default="standard",
        help="standard: one diagram per room; source: preserve original sheets and layout",
    )
    export_parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing export after explicit confirmation",
    )
    gui_parser = subparsers.add_parser("gui", help="open the local RackTool cockpit")
    gui_parser.add_argument("workbook", type=Path, nargs="?")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # JSON transport is UTF-8 even when Windows redirects a legacy-codepage
    # console to an Agent pipe. StringIO/capture streams need no reconfiguration.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "conversation":
            return handle_conversation_cli(args)
        if args.command == "layout":
            return handle_layout_cli(args)
        if args.command == "position-table":
            return handle_position_cli(args)
        if args.command == "inspect":
            scan_result = scan_workbook(args.workbook)
            print(json.dumps(scan_result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "analyze":
            analysis_result = analyze_workbook(args.workbook)
            print(
                json.dumps(
                    analysis_result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
                )
            )
            return 0
        if args.command == "profile":
            return _profile_command(args)
        if args.command == "analysis-package":
            output = export_analysis_package(
                args.workbook, args.output, include_source=args.include_source, overwrite=args.force,
            )
            print(json.dumps({
                "status": "exported", "output": str(output),
                "source_included": args.include_source, "redacted": False,
            }, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "project":
            return _project_command(args)
        if args.command == "sync":
            return _sync_command(args)
        if args.command == "export":
            project = load_project_state(args.database)
            output = export_project_workbook(project, args.output, overwrite=args.force, layout=args.layout)
            print(
                json.dumps(
                    {"status": "exported", "output": str(output)},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "gui":
            from racktool.gui.window import launch

            return launch(args.workbook)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as error:
        parser.exit(2, f"racktool: error: {error}\n")
    return 1


def _profile_command(args: argparse.Namespace) -> int:
    if args.profile_command == "validate":
        profile = load_profile(args.profile)
        print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.profile_command == "fingerprint":
        print(
            json.dumps(
                fingerprint_workbook(args.workbook).to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    profile = load_profile(args.profile)
    if args.profile_command == "match":
        analysis = analyze_workbook(args.workbook)
        print(
            json.dumps(
                select_profile(profile, analysis).to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.profile_command == "apply":
        result = apply_profile(
            args.workbook,
            profile,
            dry_run=not args.commit,
            force=args.force,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result.status == "applied" else 2
    return 1


def _project_command(args: argparse.Namespace) -> int:
    if args.project_command in {"create", "show", "add-rack", "add-device", "edit-device"}:
        if args.project_command == "create":
            project = create_draft_project(args.database, args.count, args.height)
        elif args.project_command == "show":
            project = load_project_state(args.database)
        elif args.project_command == "add-rack":
            project = add_draft_rack(args.database, args.name, height_u=args.height, row=args.row)
        elif args.project_command == "add-device":
            project = add_draft_device(args.database, args.rack, args.start_u, args.end_u, args.text)
        else:
            project = edit_draft_device(
                args.database, args.device_id, display_text=args.text,
                rack_reference=args.rack, start_u=args.start_u, end_u=args.end_u,
            )
        print(json.dumps(project.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.project_command == "import":
        profile = load_profile(args.profile) if args.profile is not None else None
        project = import_project(
            args.workbook,
            args.database,
            profile=profile,
            expected_sha256=args.expected_sha256,
        )
        print(json.dumps(project.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.project_command == "rescan":
        result = rescan_project(args.workbook, args.database)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result.accepted else 2
    return 1


def _sync_command(args: argparse.Namespace) -> int:
    project = load_project_state(args.database)
    if args.sync_command == "move":
        plan = plan_device_move(
            project, args.device_id, args.rack_id, args.start_u, args.end_u, workbook_path=args.workbook,
        )
    elif args.sync_command == "edit":
        plan = plan_device_edit(
            project, args.device_id, args.rack_id, args.start_u, args.end_u,
            display_text=args.text, workbook_path=args.workbook,
        )
    elif args.sync_command == "add-device":
        plan = plan_device_add(
            project, args.rack_id, args.start_u, args.end_u, args.text, workbook_path=args.workbook,
        )
    elif args.sync_command == "rename":
        plan = plan_device_rename(project, args.device_id, args.text, workbook_path=args.workbook)
    else:
        return 1
    if not args.commit:
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if not plan.conflicts else 2
    result = commit_write_plan(args.workbook, args.database, plan)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.status == "applied" else 2


if __name__ == "__main__":
    sys.exit(main())
