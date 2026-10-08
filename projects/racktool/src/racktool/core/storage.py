from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from racktool.core.identity import normalize_path, sha256_file, unique_suffix

DATA_DIRECTORY_ENV = "RACKTOOL_DATA_DIR"
WORKBOOK_BACKUP_LIMIT = 3
WORKBOOK_BACKUP_MAX_AGE_DAYS = 30
TRANSACTION_BACKUP_MAX_AGE_DAYS = 7


def app_data_root() -> Path:
    override = os.environ.get(DATA_DIRECTORY_ENV)
    if override:
        return normalize_path(Path(override))
    if sys.platform == "darwin":
        return normalize_path(Path.home() / "Library" / "Application Support" / "RackTool")
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return normalize_path(base / "RackTool")
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return normalize_path(base / "RackTool")


def _storage_key(path: Path) -> str:
    normalized = normalize_path(path)
    path_text = os.path.normcase(str(normalized)) if os.name == "nt" else str(normalized)
    digest = hashlib.sha256(path_text.encode("utf-8")).hexdigest()[:16]
    readable = re.sub(r"[^\w.-]+", "-", normalized.stem, flags=re.UNICODE).strip("-._")
    return f"{(readable or 'project')[:48]}-{digest}"


def project_storage_directory(workbook: Path) -> Path:
    return app_data_root() / "projects" / _storage_key(workbook)


def default_project_database_path(workbook: Path) -> Path:
    return project_storage_directory(workbook) / "project.sqlite"


def workbook_backup_directory(workbook: Path) -> Path:
    return project_storage_directory(workbook) / "backups"


def transaction_backup_directory(database: Path) -> Path:
    return app_data_root() / "transactions" / _storage_key(database)


def legacy_database_path(workbook: Path) -> Path:
    source = normalize_path(workbook)
    return source.with_suffix(source.suffix + ".sqlite")


def _owned_backup_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return [
        item
        for item in directory.iterdir()
        if item.is_file() and not item.is_symlink() and ".bak-" in item.name
    ]


def _prune_directory(
    directory: Path,
    *,
    max_count: int | None,
    max_age_days: int,
    now: datetime | None = None,
) -> list[Path]:
    current = now or datetime.now(UTC)
    threshold = current - timedelta(days=max_age_days)
    candidates = sorted(
        _owned_backup_files(directory),
        key=lambda item: (item.stat().st_mtime_ns, item.name),
        reverse=True,
    )
    removed: list[Path] = []
    for index, candidate in enumerate(candidates):
        modified = datetime.fromtimestamp(candidate.stat().st_mtime, tz=UTC)
        beyond_count = max_count is not None and index >= max_count
        if beyond_count or modified < threshold:
            candidate.unlink()
            removed.append(candidate)
    return removed


def prune_workbook_backups(workbook: Path, *, now: datetime | None = None) -> list[Path]:
    return _prune_directory(
        workbook_backup_directory(workbook),
        max_count=WORKBOOK_BACKUP_LIMIT,
        max_age_days=WORKBOOK_BACKUP_MAX_AGE_DAYS,
        now=now,
    )


def cleanup_application_storage(*, now: datetime | None = None) -> list[Path]:
    root = app_data_root()
    if not root.is_dir():
        return []
    removed: list[Path] = []
    projects = root / "projects"
    if projects.is_dir():
        for project in projects.iterdir():
            if project.is_dir() and not project.is_symlink():
                removed.extend(
                    _prune_directory(
                        project / "backups",
                        max_count=WORKBOOK_BACKUP_LIMIT,
                        max_age_days=WORKBOOK_BACKUP_MAX_AGE_DAYS,
                        now=now,
                    )
                )
    transactions = root / "transactions"
    if transactions.is_dir():
        for transaction in transactions.iterdir():
            if transaction.is_dir() and not transaction.is_symlink():
                removed.extend(
                    _prune_directory(
                        transaction,
                        max_count=None,
                        max_age_days=TRANSACTION_BACKUP_MAX_AGE_DAYS,
                        now=now,
                    )
                )
    return removed


def _copy_then_remove(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    target = destination
    if target.exists():
        if sha256_file(target) == sha256_file(source):
            source.unlink()
            return target
        target = destination.with_name(f"{destination.name}-{unique_suffix()}")
    temporary = target.with_name(f".{target.name}.migrating-{unique_suffix()}")
    try:
        shutil.copy2(source, temporary)
        if sha256_file(temporary) != sha256_file(source):
            raise OSError("Migrated file verification failed")
        os.replace(temporary, target)
        source.unlink()
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return target


def migrate_legacy_workbook_backups(workbook: Path) -> list[Path]:
    source = normalize_path(workbook)
    destination = workbook_backup_directory(source)
    migrated: list[Path] = []
    for legacy in sorted(source.parent.glob(f"{source.name}.bak-*")):
        if legacy.is_file() and not legacy.is_symlink():
            migrated.append(_copy_then_remove(legacy, destination / legacy.name))
    prune_workbook_backups(source)
    return migrated


def discard_legacy_transaction_backups(database: Path) -> list[Path]:
    legacy_database = normalize_path(database)
    central = transaction_backup_directory(legacy_database)
    candidates = (
        *legacy_database.parent.glob(f"{legacy_database.name}.bak-*"),
        *central.glob(f"{legacy_database.name}.bak-*"),
    )
    removed: list[Path] = []
    for candidate in candidates:
        if candidate.is_file() and not candidate.is_symlink():
            candidate.unlink()
            removed.append(candidate)
    if central.is_dir() and not any(central.iterdir()):
        central.rmdir()
    return removed
