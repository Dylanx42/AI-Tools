from pathlib import Path

import pytest

from racktool.core import analyze_workbook
from racktool.profiles import apply_profile, load_profile, select_profile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_WORKBOOK = PROJECT_ROOT / "samples" / "private" / "机柜图-0827.xlsx"
PROFILE_ROOT = PROJECT_ROOT / "src" / "racktool" / "profiles"


@pytest.mark.skipif(not PRIVATE_WORKBOOK.is_file(), reason="Private Golden workbook is not installed")
def test_private_layouts_match_distinct_profiles() -> None:
    analysis = analyze_workbook(PRIVATE_WORKBOOK)
    dual = load_profile(PROFILE_ROOT / "generic-dual-axis.yaml")
    mixed = load_profile(PROFILE_ROOT / "generic-mixed-axis.yaml")

    dual_selection = select_profile(dual, analysis)
    mixed_selection = select_profile(mixed, analysis)
    dual_apply = apply_profile(PRIVATE_WORKBOOK, dual, dry_run=True)
    mixed_apply = apply_profile(PRIVATE_WORKBOOK, mixed, dry_run=True)

    assert dual_selection.status == "matched"
    assert dual_selection.selected_sheet_name == "二期机柜图"
    assert dual_apply.status == "applied"
    assert dual_apply.selected_sheets == ("二期机柜图",)

    assert mixed_selection.status == "matched"
    assert mixed_selection.selected_sheet_name == "三期机柜图"
    assert mixed_apply.status == "applied"
    assert mixed_apply.selected_sheets == ("三期机柜图",)

    dual_by_sheet = {item.sheet_name: item.status for item in dual_selection.matches}
    mixed_by_sheet = {item.sheet_name: item.status for item in mixed_selection.matches}
    assert dual_by_sheet["三期机柜图"] == "rejected"
    assert mixed_by_sheet["二期机柜图"] == "rejected"
