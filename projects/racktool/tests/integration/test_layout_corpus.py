from pathlib import Path

import pytest

from tests.corpus_checks import run_draft_case, run_layout_case
from tests.layout_corpus import DRAFT_CASES, LAYOUT_CASES, DraftCase, LayoutCase


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda case: case.case_id)
def test_layout_import_matches_independent_construction_facts(tmp_path: Path, case: LayoutCase) -> None:
    assert run_layout_case(case, tmp_path)["passed"]


@pytest.mark.parametrize("case", DRAFT_CASES, ids=lambda case: case.case_id)
def test_new_project_editing_variants(tmp_path: Path, case: DraftCase) -> None:
    assert run_draft_case(case, tmp_path)["passed"]
