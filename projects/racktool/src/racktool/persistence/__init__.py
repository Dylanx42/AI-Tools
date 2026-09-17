from __future__ import annotations

from pathlib import Path

from racktool.models.project import RackProject


def load_project(path: Path) -> RackProject:
    from racktool.persistence.sqlite import load_project as load_sqlite_project

    return load_sqlite_project(path)


def save_project(path: Path, project: RackProject) -> None:
    from racktool.persistence.sqlite import save_project as save_sqlite_project

    save_sqlite_project(path, project)

__all__ = ["load_project", "save_project"]
