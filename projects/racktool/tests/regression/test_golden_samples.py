import json
from pathlib import Path

import pytest

from racktool.core import analyze_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = PROJECT_ROOT / "samples" / "golden"
EXPECTED_FILES = sorted(GOLDEN_ROOT.glob("*/expected.json"))


@pytest.mark.parametrize(
    "expected_path",
    EXPECTED_FILES or [None],
    ids=[path.parent.name for path in EXPECTED_FILES] or ["no-golden-samples"],
)
def test_golden_sample(expected_path: Path | None) -> None:
    if expected_path is None:
        pytest.skip("No sanitized, manually confirmed Golden Sample is installed")

    payload = json.loads(expected_path.read_text(encoding="utf-8"))
    workbook_path = expected_path.parent / payload["workbook"]

    assert workbook_path.is_file(), f"Golden workbook is missing: {workbook_path}"
    assert analyze_workbook(workbook_path).to_dict() == payload["analysis"]
