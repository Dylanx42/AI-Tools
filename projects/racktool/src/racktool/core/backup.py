from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from racktool.core.identity import normalize_path, sha256_file, unique_suffix
from racktool.core.ooxml import load_xlsx_workbook
from racktool.core.storage import (
    prune_workbook_backups,
    transaction_backup_directory,
    workbook_backup_directory,
)


def create_backup(
    source: Path,
    *,
    kind: Literal["recovery", "transaction"] = "recovery",
) -> Path:
    source_path = normalize_path(source)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    directory = (
        workbook_backup_directory(source_path)
        if kind == "recovery"
        else transaction_backup_directory(source_path)
    )
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = directory / (
        f"{source_path.name}.bak-{stamp}-{unique_suffix()}"
    )
    shutil.copy2(source_path, backup_path)
    backup_path.touch()
    if kind == "recovery":
        try:
            prune_workbook_backups(source_path)
        except OSError:
            pass
    return backup_path


def create_temp_copy(source: Path) -> Path:
    source_path = normalize_path(source)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    temp_path = source_path.with_name(
        f".{source_path.stem}.tmp-{stamp}-{unique_suffix()}{source_path.suffix}"
    )
    shutil.copy2(source_path, temp_path)
    return temp_path


def list_backups(source: Path) -> list[Path]:
    source_path = normalize_path(source)
    central = workbook_backup_directory(source_path).glob(f"{source_path.name}.bak-*")
    legacy = source_path.parent.glob(f"{source_path.name}.bak-*")
    return sorted(
        {
            item
            for item in (*central, *legacy)
            if item.is_file() and not item.is_symlink()
        },
        key=lambda item: (item.stat().st_mtime_ns, item.name),
        reverse=True,
    )


def discard_backup(backup: Path) -> bool:
    backup_path = normalize_path(backup)
    try:
        if not backup_path.is_file() or backup_path.is_symlink():
            return False
        backup_path.unlink()
    except OSError:
        return False
    return True


def _reload_xlsx(path: Path) -> None:
    workbook = load_xlsx_workbook(path)
    workbook.close()


def restore_backup(
    backup: Path,
    source: Path,
    *,
    validator: Callable[[Path], None] | None = None,
) -> Path:
    backup_path = normalize_path(backup)
    source_path = normalize_path(source)
    if not backup_path.is_file():
        raise FileNotFoundError(backup_path)
    if backup_path.name.startswith(f"{source_path.name}.bak-") is False:
        raise ValueError("Backup file does not belong to the source workbook")
    source_fingerprint = sha256_file(source_path)
    temp_path = create_temp_copy(source_path)
    try:
        shutil.copy2(backup_path, temp_path)
        if source_path.suffix.lower() == ".xlsx":
            _reload_xlsx(temp_path)
        if validator is not None:
            validator(temp_path)
        if sha256_file(source_path) != source_fingerprint:
            raise ValueError("Source changed while the backup was being validated")
        temp_path.replace(source_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
    return source_path
