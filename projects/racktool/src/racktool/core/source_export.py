"""Append a generated position sheet without reserializing original worksheet parts."""

from __future__ import annotations

import posixpath
import re
from io import BytesIO
from pathlib import Path
from typing import cast
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"


def _append(xml: bytes, local_name: str, children: bytes) -> bytes:
    # Preserve original namespace declarations, including mc:Ignorable prefix values.
    pattern = rb"</(?:[\w.-]+:)?" + local_name.encode() + rb"\s*>"
    closing = re.search(pattern, xml)
    if closing is None:
        raise ValueError(f"原版面导出失败：XML 缺少 {local_name} 结束标签。")
    return xml[:closing.start()] + children + xml[closing.start():]


def _xml(element: ET.Element) -> bytes:
    return cast(bytes, ET.tostring(element, encoding="utf-8"))


def _merge_styles(original: bytes, generated: bytes) -> bytes:
    original_root, generated_root = ET.fromstring(original), ET.fromstring(generated)
    for name in ("fonts", "fills", "borders", "cellStyleXfs", "cellXfs", "dxfs"):
        old = original_root.find(f"{{{MAIN}}}{name}")
        new = generated_root.find(f"{{{MAIN}}}{name}")
        old_count = len(old) if old is not None else 0
        new_count = len(new) if new is not None else 0
        if new_count < old_count:
            raise ValueError("原版面导出失败：原始样式索引不能安全保留。")
        if new_count == old_count:
            continue
        assert new is not None
        extra = b"".join(_xml(element) for element in list(new)[old_count:])
        if old is None:
            raise ValueError("原版面导出失败：缺少原始样式容器。")
        opening = re.search(rb"<(?:[\w.-]+:)?" + name.encode() + rb"\b[^>]*>", original)
        if opening is None:
            raise ValueError("原版面导出失败：无法定位样式容器。")
        tag = opening.group()
        if tag.endswith(b"/>"):
            # Only empty containers may use a self-closing tag.
            tag_name = re.match(rb"<([\w:.-]+)", tag)
            assert tag_name is not None and old_count == 0
            replacement = tag[:-2] + b">" + extra + b"</" + tag_name.group(1) + b">"
            original = original[:opening.start()] + replacement + original[opening.end():]
        else:
            original = _append(original, name, extra)
        opening = re.search(rb"<(?:[\w.-]+:)?" + name.encode() + rb"\b[^>]*>", original)
        assert opening is not None
        tag = opening.group()
        if re.search(rb"\bcount=['\"]\d+['\"]", tag):
            tag = re.sub(rb"\bcount=['\"]\d+['\"]", f'count="{new_count}"'.encode(), tag)
        else:
            tag = tag[:-1] + f' count="{new_count}">'.encode()
        original = original[:opening.start()] + tag + original[opening.end():]
    return original


def _resolve(base: str, target: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), target)).lstrip("/")


def append_position_sheet(source: bytes, generated: Path, position_name: str) -> None:
    """Replace only the temporary export package; never open source for writing."""
    with ZipFile(BytesIO(source)) as original, ZipFile(generated) as compiled:
        originals = {name.replace("\\", "/"): original.read(name) for name in original.namelist()}
        generated_workbook = ET.fromstring(compiled.read("xl/workbook.xml"))
        generated_relationships = ET.fromstring(compiled.read("xl/_rels/workbook.xml.rels"))
        generated_sheets = generated_workbook.find(f"{{{MAIN}}}sheets")
        assert generated_sheets is not None
        generated_sheet = next(sheet for sheet in generated_sheets if sheet.attrib["name"] == position_name)
        generated_id = generated_sheet.attrib[f"{{{REL}}}id"]
        relationship = next(r for r in generated_relationships if r.attrib["Id"] == generated_id)
        generated_part = _resolve("xl/workbook.xml", relationship.attrib["Target"])
        sheet_xml = compiled.read(generated_part)
        if any(cell.attrib.get("t") == "s" for cell in ET.fromstring(sheet_xml).iter(f"{{{MAIN}}}c")):
            raise ValueError("原版面导出失败：新表不能引用原文件的共享字符串索引。")
        index = 1
        while (f"xl/worksheets/racktoolPositions{index}.xml" in originals
               or f"xl/tables/racktoolPositions{index}.xml" in originals):
            index += 1
        new_part = f"xl/worksheets/racktoolPositions{index}.xml"
        new_table = f"xl/tables/racktoolPositions{index}.xml"
        generated_rels_part = posixpath.join(posixpath.dirname(generated_part), "_rels",
                                            posixpath.basename(generated_part) + ".rels")
        sheet_relationships = ET.fromstring(compiled.read(generated_rels_part)) if generated_rels_part in compiled.namelist() else None
        extras = {new_part: sheet_xml}
        if sheet_relationships is not None:
            for item in sheet_relationships:
                if item.attrib["Type"] != f"{REL}/table":
                    raise ValueError("原版面导出失败：新表含未支持的关系。")
                extras[new_table] = compiled.read(_resolve(generated_part, item.attrib["Target"]))
                item.set("Target", "../tables/" + posixpath.basename(new_table))
            extras[f"xl/worksheets/_rels/{posixpath.basename(new_part)}.rels"] = _xml(sheet_relationships)
        workbook_root = ET.fromstring(originals["xl/workbook.xml"])
        sheets = workbook_root.find(f"{{{MAIN}}}sheets")
        assert sheets is not None
        next_sheet_id = max(int(sheet.attrib["sheetId"]) for sheet in sheets) + 1
        relationships = ET.fromstring(originals["xl/_rels/workbook.xml.rels"])
        occupied_ids = {r.attrib["Id"] for r in relationships}
        identifier = "rIdRackToolPositions"
        while identifier in occupied_ids:
            identifier += "_"
        new_sheet = ET.Element(f"{{{MAIN}}}sheet", {
            "name": position_name, "sheetId": str(next_sheet_id), f"{{{REL}}}id": identifier,
        })
        originals["xl/workbook.xml"] = _append(originals["xl/workbook.xml"], "sheets", _xml(new_sheet))
        new_relation = ET.Element(f"{{{PACKAGE_REL}}}Relationship", {
            "Id": identifier, "Type": f"{REL}/worksheet", "Target": "/" + new_part,
        })
        originals["xl/_rels/workbook.xml.rels"] = _append(
            originals["xl/_rels/workbook.xml.rels"], "Relationships", _xml(new_relation),
        )
        overrides = [ET.Element(f"{{{CONTENT}}}Override", {
            "PartName": "/" + new_part,
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        })]
        if new_table in extras:
            overrides.append(ET.Element(f"{{{CONTENT}}}Override", {
                "PartName": "/" + new_table,
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml",
            }))
        originals["[Content_Types].xml"] = _append(originals["[Content_Types].xml"], "Types", b"".join(map(_xml, overrides)))
        originals["xl/styles.xml"] = _merge_styles(originals["xl/styles.xml"], compiled.read("xl/styles.xml"))
        result = BytesIO()
        with ZipFile(result, "w", ZIP_DEFLATED) as archive:
            archive.comment = original.comment
            for name, payload in {**originals, **extras}.items():
                archive.writestr(name, payload)
    generated.write_bytes(result.getvalue())
