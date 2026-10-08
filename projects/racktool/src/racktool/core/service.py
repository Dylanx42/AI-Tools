from __future__ import annotations

import os
import shutil
from pathlib import Path

from racktool.core.backup import create_backup, discard_backup, restore_backup
from racktool.core.identity import normalize_path, sha256_file, unique_suffix
from racktool.core.project import (
    _rescan_snapshot,
    import_workbook,
    project_error_conflicts,
    rescan_workbook,
)
from racktool.core.storage import (
    cleanup_application_storage,
    default_project_database_path,
    discard_legacy_transaction_backups,
    legacy_database_path,
    migrate_legacy_workbook_backups,
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


def _discard(backup: Path | None) -> None:
    if backup is not None:
        discard_backup(backup)


def prepare_default_project_database(workbook: Path) -> tuple[Path, str | None]:
    source = normalize_path(workbook)
    try:
        cleanup_application_storage()
    except OSError:
        pass
    try:
        migrated_workbook_backups = migrate_legacy_workbook_backups(source)
    except OSError:
        migrated_workbook_backups = []
    target = default_project_database_path(source)
    legacy = legacy_database_path(source)
    message: str | None = None
    if migrated_workbook_backups:
        message = "已整理旧版 Excel 备份"
    if not legacy.is_file() or legacy.is_symlink():
        return target, message

    if target.is_file():
        try:
            current = load_project(target)
            previous = load_project(legacy)
        except Exception:  # noqa: BLE001
            return target, message
        if current.to_dict() != previous.to_dict():
            raise ValueError(
                "发现两份内容不同的项目数据，RackTool 为避免覆盖已停止自动整理。"
            )
        try:
            legacy.unlink()
        except OSError:
            return target, "已使用 RackTool 专用目录；旧版项目文件将在下次继续清理"
        try:
            discard_legacy_transaction_backups(legacy)
        except OSError:
            return target, "已清理旧版项目文件；旧事务备份将在下次继续清理"
        return target, "已清理重复的旧版项目文件"

    previous = load_project(legacy)
    if previous.source_workbook is None:
        raise ValueError("旧版项目文件没有记录对应的 Excel，无法安全迁移。")
    if normalize_path(Path(previous.source_workbook)) != source:
        raise ValueError("旧版项目文件与当前 Excel 不匹配，无法安全迁移。")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.migrating-{unique_suffix()}")
    target_created = False
    try:
        shutil.copy2(legacy, temporary)
        if sha256_file(temporary) != sha256_file(legacy):
            raise OSError("项目数据迁移校验失败")
        migrated = load_project(temporary)
        if migrated.to_dict() != previous.to_dict():
            raise ValueError("项目数据迁移后内容不一致")
        os.replace(temporary, target)
        target_created = True
        if load_project(target).to_dict() != previous.to_dict():
            raise ValueError("项目数据迁移后重新打开校验失败")
    except Exception:
        if temporary.exists():
            temporary.unlink()
        if target_created and target.exists():
            target.unlink()
        raise
    try:
        legacy.unlink()
    except OSError:
        return target, "已迁入 RackTool 专用目录；旧版项目文件将在下次继续清理"
    try:
        discard_legacy_transaction_backups(legacy)
    except OSError:
        return target, "已迁入 RackTool 专用目录；旧事务备份将在下次继续清理"
    return target, "已把旧版项目数据移到 RackTool 专用目录"


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
    database_backup = (
        create_backup(database_path, kind="transaction") if database_path.is_file() else None
    )
    try:
        save_project(database_path, project)
    except Exception:
        _restore_database(database_backup, database_path)
        _discard(database_backup)
        raise
    _discard(database_backup)
    return load_project(database_path)


def rescan_project(workbook: Path, database: Path) -> RescanResult:
    source = normalize_path(workbook)
    database_path = normalize_path(database)
    current = load_project(database_path)
    result = rescan_workbook(source, current)
    if not result.accepted:
        return result
    database_backup = create_backup(database_path, kind="transaction")
    try:
        save_project(database_path, result.project)
    except Exception:
        _restore_database(database_backup, database_path)
        _discard(database_backup)
        raise
    _discard(database_backup)
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
    if not plan.actions:
        return apply_writeback(source, current, plan)
    database_backup = create_backup(database_path, kind="transaction")
    result = apply_writeback(source, current, plan)
    if result.status != "applied" or result.project is None:
        _discard(database_backup)
        return result
    if not result.plan.actions:
        _discard(database_backup)
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
        database_restored = False
        workbook_restored = False
        try:
            _restore_database(database_backup, database_path)
            database_restored = True
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
                workbook_restored = True
            except Exception as rollback_error:  # noqa: BLE001
                rollback_errors.append(f"workbook rollback failed: {rollback_error}")
        if database_restored:
            _discard(database_backup)
        if workbook_restored and result.backup_path is not None:
            _discard(Path(result.backup_path))
        return WriteResult(
            status="failed",
            plan=result.plan,
            backup_path=None if workbook_restored else result.backup_path,
            output_path=str(source),
            project=current,
            message="Project persistence failed; workbook and database rollback was attempted",
            errors=(str(error), *rollback_errors),
        )
    _discard(database_backup)
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
    try:
        database_rollback = create_backup(database_path, kind="transaction")
    except Exception:
        _discard(workbook_rollback)
        raise
    restored_project: RackProject | None = None

    def validate_restore(candidate: Path) -> None:
        nonlocal restored_project
        restored_project = _validated_rescan(candidate, source, current)

    try:
        restore_backup(backup, source, validator=validate_restore)
    except Exception:
        _discard(workbook_rollback)
        _discard(database_rollback)
        raise
    if restored_project is None:
        _discard(workbook_rollback)
        _discard(database_rollback)
        raise RuntimeError("Backup validation did not produce a project state")
    try:
        save_project(database_path, restored_project)
        persisted = load_project(database_path)
    except Exception:
        rollback_errors: list[str] = []
        database_restored = False
        workbook_restored = False
        try:
            _restore_database(database_rollback, database_path)
            database_restored = True
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
            workbook_restored = True
        except Exception as rollback_error:  # noqa: BLE001
            rollback_errors.append(f"workbook rollback failed: {rollback_error}")
        if database_restored:
            _discard(database_rollback)
        if workbook_restored:
            _discard(workbook_rollback)
        if rollback_errors:
            raise RuntimeError("; ".join(rollback_errors))
        raise
    _discard(database_rollback)
    return persisted
