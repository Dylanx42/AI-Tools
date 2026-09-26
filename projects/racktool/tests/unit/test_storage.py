from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from racktool.core.backup import create_backup, list_backups
from racktool.core.storage import (
    cleanup_application_storage,
    default_project_database_path,
)


def test_default_database_is_outside_source_directory_and_path_specific(
    tmp_path: Path,
) -> None:
    first_directory = tmp_path / "first"
    second_directory = tmp_path / "second"
    first_directory.mkdir()
    second_directory.mkdir()
    first = first_directory / "layout.xlsx"
    second = second_directory / "layout.xlsx"
    first.touch()
    second.touch()

    first_database = default_project_database_path(first)
    second_database = default_project_database_path(second)

    assert first_database.parent != first.parent
    assert first_database.name == "project.sqlite"
    assert first_database != second_database
    assert default_project_database_path(first) == first_database


def test_recovery_backups_are_central_and_keep_only_three(tmp_path: Path) -> None:
    source = tmp_path / "layout.xlsx"
    source.write_bytes(b"workbook")

    created = [create_backup(source) for _ in range(4)]
    retained = list_backups(source)

    assert not list(tmp_path.glob("layout.xlsx.bak-*"))
    assert len(retained) == 3
    assert created[-1] in retained
    assert created[0] not in retained


def test_startup_cleanup_removes_expired_recovery_backup(tmp_path: Path) -> None:
    source = tmp_path / "layout.xlsx"
    source.write_bytes(b"workbook")
    backup = create_backup(source)
    expired = datetime.now(UTC) - timedelta(days=31)
    os.utime(backup, (expired.timestamp(), expired.timestamp()))

    removed = cleanup_application_storage(now=datetime.now(UTC))

    assert backup in removed
    assert not backup.exists()
