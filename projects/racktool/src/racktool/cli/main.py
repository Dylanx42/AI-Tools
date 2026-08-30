from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from racktool.core import analyze_workbook, scan_workbook
from racktool.core.project import import_workbook, rescan_workbook
from racktool.core.sync import apply_writeback, plan_device_move
from racktool.persistence import load_project, save_project
from racktool.profiles import apply_profile, fingerprint_workbook, load_profile, select_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="racktool", description="RackTool XLSX utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser(
        "inspect", help="emit a deterministic structural summary (not rack detection)"
    )
    inspect_parser.add_argument("workbook", type=Path)
    analyze_parser = subparsers.add_parser(
        "analyze", help="emit explainable U-axis, rack, and device candidates"
    )
    analyze_parser.add_argument("workbook", type=Path)
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
    import_parser = project_subparsers.add_parser("import", help="create a SQLite project from a workbook")
    import_parser.add_argument("workbook", type=Path)
    import_parser.add_argument("database", type=Path)
    import_parser.add_argument("--profile-id", dest="profile_id")
    rescan_parser = project_subparsers.add_parser("rescan", help="rescan a workbook against an existing SQLite project")
    rescan_parser.add_argument("workbook", type=Path)
    rescan_parser.add_argument("database", type=Path)
    sync_parser = subparsers.add_parser("sync", help="plan or apply a safe workbook write-back")
    sync_subparsers = sync_parser.add_subparsers(dest="sync_command", required=True)
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
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
        if args.command == "project":
            return _project_command(args)
        if args.command == "sync":
            return _sync_command(args)
    except (FileNotFoundError, OSError, ValueError) as error:
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
    if args.project_command == "import":
        project = import_workbook(args.workbook, profile_id=args.profile_id)
        save_project(args.database, project)
        print(json.dumps(project.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.project_command == "rescan":
        current = load_project(args.database)
        result = rescan_workbook(args.workbook, current)
        save_project(args.database, result.project)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if not any(item.severity == "error" for item in result.project.conflicts) else 2
    return 1


def _sync_command(args: argparse.Namespace) -> int:
    if args.sync_command != "move":
        return 1
    project = load_project(args.database)
    plan = plan_device_move(project, args.device_id, args.rack_id, args.start_u, args.end_u)
    if not args.commit:
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if not plan.conflicts else 2
    result = apply_writeback(args.workbook, project, plan)
    if result.status == "applied" and result.project is not None:
        save_project(args.database, result.project)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.status == "applied" else 2


if __name__ == "__main__":
    sys.exit(main())
