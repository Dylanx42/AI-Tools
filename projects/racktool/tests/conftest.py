from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_racktool_storage(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Path]:
    storage = tmp_path_factory.mktemp("racktool-storage")
    monkeypatch.setenv("RACKTOOL_DATA_DIR", str(storage))
    yield storage
