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
