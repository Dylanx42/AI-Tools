from __future__ import annotations

from pathlib import Path

from racktool.core.backup import create_backup, restore_backup
from racktool.core.identity import normalize_path
from racktool.core.project import (
    _rescan_snapshot,
    import_workbook,
    project_error_conflicts,
    rescan_workbook,
)
from racktool.core.sync import WritePlan, WriteResult, apply_writeback
from racktool.models.project import RackProject, RescanResult
from racktool.persistence import load_project, save_project
from racktool.profiles.schema import LayoutProfile


def _validate_database(path: Path) -> None:
    load_project(path)


def _restore_database(backup: Path | None, database: Path) -> None:
    if backup is not None:
        restore_backup(backup, database, validator=_validate_database)


def _validated_rescan(
    snapshot: Path,
    source: Path,
    project: RackProject,
) -> RackProject:
    result = _rescan_snapshot(snapshot, source, project)
    if not result.accepted:
        raise ValueError("; ".join(item.message for item in result.conflicts))
    errors = [item for item in result.project.conflicts if item.severity == "error"]
    if errors:
        raise ValueError("; ".join(item.message for item in errors))
    return result.project


def load_project_state(database: Path) -> RackProject:
    return load_project(normalize_path(database))


def import_project(
    workbook: Path,
    database: Path,
    *,
    profile: LayoutProfile | None = None,
) -> RackProject:
    source = normalize_path(workbook)
    database_path = normalize_path(database)
    project = import_workbook(source, profile=profile)
    errors = project_error_conflicts(project)
    if errors:
        raise ValueError("; ".join(item.message for item in errors))
    database_backup = create_backup(database_path) if database_path.is_file() else None
    try:
        save_project(database_path, project)
    except Exception:
        _restore_database(database_backup, database_path)
        raise
    return load_project(database_path)


def rescan_project(workbook: Path, database: Path) -> RescanResult:
    source = normalize_path(workbook)
    database_path = normalize_path(database)
    current = load_project(database_path)
    result = rescan_workbook(source, current)
    if not result.accepted:
        return result
    database_backup = create_backup(database_path)
    try:
        save_project(database_path, result.project)
    except Exception:
        _restore_database(database_backup, database_path)
        raise
    return RescanResult(
        project=load_project(database_path),
        accepted=result.accepted,
        conflicts=result.conflicts,
        created_rack_ids=result.created_rack_ids,
        missing_rack_ids=result.missing_rack_ids,
        created_device_ids=result.created_device_ids,
        updated_device_ids=result.updated_device_ids,
        unchanged_device_ids=result.unchanged_device_ids,
        missing_device_ids=result.missing_device_ids,
    )


def commit_write_plan(
    workbook: Path,
    database: Path,
    plan: WritePlan,
) -> WriteResult:
    source = normalize_path(workbook)
    database_path = normalize_path(database)
    current = load_project(database_path)
    database_backup = create_backup(database_path)
    result = apply_writeback(source, current, plan)
    if result.status != "applied" or result.project is None:
        return result
    if not result.plan.actions:
        return WriteResult(
            status=result.status,
            plan=result.plan,
            backup_path=result.backup_path,
            output_path=result.output_path,
            project=current,
            message=result.message,
            errors=result.errors,
        )
    try:
        save_project(database_path, result.project)
        persisted = load_project(database_path)
    except Exception as error:  # noqa: BLE001
        rollback_errors: list[str] = []
        try:
            _restore_database(database_backup, database_path)
        except Exception as rollback_error:  # noqa: BLE001
            rollback_errors.append(f"database rollback failed: {rollback_error}")
        if result.backup_path is not None:
            try:
                def validate_workbook_rollback(path: Path) -> None:
                    _validated_rescan(path, source, current)

                restore_backup(
                    Path(result.backup_path),
                    source,
                    validator=validate_workbook_rollback,
                )
            except Exception as rollback_error:  # noqa: BLE001
                rollback_errors.append(f"workbook rollback failed: {rollback_error}")
        return WriteResult(
            status="failed",
            plan=result.plan,
            backup_path=result.backup_path,
            output_path=str(source),
            project=current,
            message="Project persistence failed; workbook and database rollback was attempted",
            errors=(str(error), *rollback_errors),
        )
    return WriteResult(
        status=result.status,
        plan=result.plan,
        backup_path=result.backup_path,
        output_path=result.output_path,
        project=persisted,
        message=result.message,
        errors=result.errors,
    )


def restore_project_backup(
    workbook: Path,
    database: Path,
    backup: Path,
) -> RackProject:
    source = normalize_path(workbook)
    database_path = normalize_path(database)
    current = load_project(database_path)
    errors = project_error_conflicts(current)
    if errors:
        raise ValueError("; ".join(item.message for item in errors))
    workbook_rollback = create_backup(source)
    database_rollback = create_backup(database_path)
    restored_project: RackProject | None = None

    def validate_restore(candidate: Path) -> None:
        nonlocal restored_project
        restored_project = _validated_rescan(candidate, source, current)

    restore_backup(backup, source, validator=validate_restore)
    if restored_project is None:
        raise RuntimeError("Backup validation did not produce a project state")
    try:
        save_project(database_path, restored_project)
        return load_project(database_path)
    except Exception:
        rollback_errors: list[str] = []
        try:
            _restore_database(database_rollback, database_path)
        except Exception as rollback_error:  # noqa: BLE001
            rollback_errors.append(f"database rollback failed: {rollback_error}")
        try:
            def validate_workbook_rollback(path: Path) -> None:
                _validated_rescan(path, source, current)

            restore_backup(
                workbook_rollback,
                source,
                validator=validate_workbook_rollback,
            )
        except Exception as rollback_error:  # noqa: BLE001
            rollback_errors.append(f"workbook rollback failed: {rollback_error}")
        if rollback_errors:
            raise RuntimeError("; ".join(rollback_errors))
        raise
