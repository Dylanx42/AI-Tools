from __future__ import annotations

import uuid
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path

IdFactory = Callable[[str], str]


def new_entity_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16].upper()}"


def default_id_factory(prefix: str) -> str:
    return new_entity_id(prefix)


def normalize_path(path: Path) -> Path:
    return path.expanduser().resolve()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with normalize_path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]
