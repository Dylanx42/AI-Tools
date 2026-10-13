from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pytest

from racktool.core import analyze_workbook, export_project_workbook, import_project
from racktool.core.identity import sha256_file
from racktool.core.ooxml import load_xlsx_workbook

SOURCE = Path(__file__).resolve().parents[2] / "samples" / "private" / "1013-acceptance" / "source.xlsx"


@pytest.mark.parametrize("layout", ["standard", "source"])
def test_private_mixed_direction_room_export(tmp_path: Path, layout: str) -> None:
    if not SOURCE.is_file():
        pytest.skip("New private mixed-direction acceptance workbook is not installed")
    before = sha256_file(SOURCE)
    project = import_project(SOURCE, tmp_path / "project.sqlite")
    original = analyze_workbook(SOURCE)
    output = export_project_workbook(project, tmp_path / "export.xlsx", layout=layout)
    exported = analyze_workbook(output)
    expected = Counter((sheet.name, rack.rack_name, rack.height_u, rack.direction)
                       for sheet in original.sheets for rack in sheet.racks)
    actual = Counter((sheet.name, rack.rack_name, rack.height_u, rack.direction)
                     for sheet in exported.sheets for rack in sheet.racks)
    assert actual == expected
    assert len(project.racks) == 59 and len(project.devices) == 51
    assert sum(r.direction == "ascending" for r in project.racks) == 22
    workbook = load_xlsx_workbook(output)
    try:
        assert workbook.sheetnames == [sheet.name for sheet in original.sheets] + ["设备位置表"]
        positions = workbook["设备位置表"]
        assert positions.max_row == 52
        assert positions["A1"].value == "序号" and positions["F1"].value == "机房"
        assert all(str(positions.cell(row, 4).value).endswith("U") for row in range(2, 53))
    finally:
        workbook.close()
    if layout == "source":
        with ZipFile(SOURCE) as source, ZipFile(output) as target:
            assert all(source.read(name) == target.read(name)
                       for name in source.namelist() if name.startswith("xl/worksheets/"))
    assert sha256_file(SOURCE) == before
