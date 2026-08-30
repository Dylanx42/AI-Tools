from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path


def create_backup(source: Path) -> Path:
    source_path = source.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = source_path.with_name(f"{source_path.name}.bak-{stamp}")
    shutil.copy2(source_path, backup_path)
    return backup_path


def create_temp_copy(source: Path) -> Path:
    source_path = source.expanduser().resolve()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    temp_path = source_path.with_name(f".{source_path.stem}.tmp-{stamp}{source_path.suffix}")
    shutil.copy2(source_path, temp_path)
    return temp_path


def list_backups(source: Path) -> list[Path]:
    source_path = source.expanduser().resolve()
    return sorted(source_path.parent.glob(f"{source_path.name}.bak-*"), reverse=True)


def restore_backup(backup: Path, source: Path) -> Path:
    backup_path = backup.expanduser().resolve()
    source_path = source.expanduser().resolve()
    if not backup_path.is_file():
        raise FileNotFoundError(backup_path)
    if backup_path.name.startswith(f"{source_path.name}.bak-") is False:
        raise ValueError("Backup file does not belong to the source workbook")
    shutil.copy2(backup_path, source_path)
    return source_path
