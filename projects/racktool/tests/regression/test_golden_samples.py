import hashlib
import json
from pathlib import Path

import pytest

from racktool.core import analyze_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_GOLDEN_ROOT = PROJECT_ROOT / "samples" / "golden"
PRIVATE_GOLDEN_ROOT = PROJECT_ROOT / "samples" / "private" / "golden"
EXPECTED_FILES = sorted(
    [
        *PUBLIC_GOLDEN_ROOT.glob("*/expected.json"),
        *PRIVATE_GOLDEN_ROOT.glob("*/expected.json"),
    ]
)


def _case_id(path: Path) -> str:
    visibility = "private" if PRIVATE_GOLDEN_ROOT in path.parents else "public"
    return f"{visibility}:{path.parent.name}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_normalize(payload: object) -> object:
    """Compare the same JSON value shape that users persist in expected.json."""
    return json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))


@pytest.mark.parametrize(
    "expected_path",
    EXPECTED_FILES or [None],
    ids=[_case_id(path) for path in EXPECTED_FILES] or ["no-golden-samples"],
)
def test_golden_sample(expected_path: Path | None) -> None:
    if expected_path is None:
        pytest.skip("No sanitized, manually confirmed Golden Sample is installed")

    payload = json.loads(expected_path.read_text(encoding="utf-8"))
    workbook_path = (expected_path.parent / payload["workbook"]).resolve()

    assert workbook_path.is_file(), f"Golden workbook is missing: {workbook_path}"
    expected_hash = payload.get("workbook_sha256")
    if expected_hash is not None:
        assert _sha256(workbook_path) == expected_hash

    actual = _json_normalize(analyze_workbook(workbook_path).to_dict())
    scope = payload.get("scope")
    if scope is None:
        assert actual == payload["analysis"]
        return

    assert scope.get("kind") == "sheet"
    sheet_name = scope.get("name")
    matching_sheets = [sheet for sheet in actual["sheets"] if sheet["name"] == sheet_name]
    assert len(matching_sheets) == 1, f"Golden Sheet is missing or ambiguous: {sheet_name}"
    assert matching_sheets[0] == payload["analysis"]
