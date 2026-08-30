from __future__ import annotations

import uuid
from collections.abc import Callable

IdFactory = Callable[[str], str]


def new_entity_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16].upper()}"


def default_id_factory(prefix: str) -> str:
    return new_entity_id(prefix)
