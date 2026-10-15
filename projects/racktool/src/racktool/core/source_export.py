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
        # Only copy the new position page's hidden, local round-trip constants.
        # Original global/local names and worksheet parts remain untouched.
        generated_names = generated_workbook.find(f"{{{MAIN}}}definedNames")
        new_names = []
        if generated_names is not None:
            generated_index = list(generated_sheets).index(generated_sheet)
            for definition in generated_names:
                if (definition.attrib.get("localSheetId") == str(generated_index)
                        and definition.attrib.get("name", "").startswith("_RackToolPositions_v1_")):
                    definition.set("localSheetId", str(len(sheets)))
                    new_names.append(_xml(definition))
        if new_names:
            names_xml = b"".join(new_names)
            if workbook_root.find(f"{{{MAIN}}}definedNames") is not None:
                raw = originals["xl/workbook.xml"]
                empty_names = re.search(rb"<([\w.-]+:)?definedNames\b[^>]*?\s*/>", raw)
                if empty_names is not None:
                    prefix = empty_names.group(1) or b""
                    replacement = (empty_names.group()[:-2] + b">" + names_xml
                                   + b"</" + prefix + b"definedNames>")
                    originals["xl/workbook.xml"] = (
                        raw[:empty_names.start()] + replacement + raw[empty_names.end():]
                    )
                else:
                    originals["xl/workbook.xml"] = _append(raw, "definedNames", names_xml)
            else:
                # Keep schema order: functionGroups/externalReferences may follow sheets.
                container = (f'<definedNames xmlns="{MAIN}">'.encode()
                             + names_xml + b"</definedNames>")
                raw = originals["xl/workbook.xml"]
                sheets_closing = re.search(rb"</(?:[\w.-]+:)?sheets\s*>", raw)
                assert sheets_closing is not None
                following = re.search(
                    rb"<(?:[\w.-]+:)?(?:calcPr|oleSize|customWorkbookViews|pivotCaches|"
                    rb"smartTagPr|smartTagTypes|webPublishing|fileRecoveryPr|webPublishObjects|extLst)\b",
                    raw[sheets_closing.end():],
                )
                if following is None:
                    originals["xl/workbook.xml"] = _append(raw, "workbook", container)
                else:
                    insertion = sheets_closing.end() + following.start()
                    originals["xl/workbook.xml"] = (
                        raw[:insertion] + container + raw[insertion:]
                    )
        new_relation = ET.Element(f"{{{PACKAGE_REL}}}Relationship", {
            "Id": identifier, "Type": f"{REL}/worksheet", "Target": "/" + new_part,
        })
        relations_xml = _xml(new_relation)
        overrides = [ET.Element(f"{{{CONTENT}}}Override", {
            "PartName": "/" + new_part,
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        })]
        if new_table in extras:
            overrides.append(ET.Element(f"{{{CONTENT}}}Override", {
                "PartName": "/" + new_table,
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml",
            }))
        generated_styles = compiled.read("xl/styles.xml")
        if "xl/styles.xml" in originals:
            originals["xl/styles.xml"] = _merge_styles(originals["xl/styles.xml"], generated_styles)
        else:
            # A stylesheet is optional in a valid XLSX. The compiled workbook's
            # index zero is openpyxl's default style, matching original unstyled
            # cells; new position cells retain their generated style indexes.
            style_relations = [item for item in relationships
                               if item.attrib.get("Type") == f"{REL}/styles"]
            if style_relations:
                raise ValueError("原版面导出失败：原样式关系引用缺失或不支持的样式部件。")
            extras["xl/styles.xml"] = generated_styles
            style_id = "rIdRackToolStyles"
            while style_id in occupied_ids or style_id == identifier:
                style_id += "_"
            relations_xml += _xml(ET.Element(f"{{{PACKAGE_REL}}}Relationship", {
                "Id": style_id, "Type": f"{REL}/styles", "Target": "/xl/styles.xml",
            }))
            content_root = ET.fromstring(originals["[Content_Types].xml"])
            if not any(item.attrib.get("PartName") == "/xl/styles.xml" for item in content_root):
                overrides.append(ET.Element(f"{{{CONTENT}}}Override", {
                    "PartName": "/xl/styles.xml",
                    "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
                }))
        originals["xl/_rels/workbook.xml.rels"] = _append(
            originals["xl/_rels/workbook.xml.rels"], "Relationships", relations_xml,
        )
        originals["[Content_Types].xml"] = _append(originals["[Content_Types].xml"], "Types", b"".join(map(_xml, overrides)))
        result = BytesIO()
        with ZipFile(result, "w", ZIP_DEFLATED) as archive:
            archive.comment = original.comment
            for name, payload in {**originals, **extras}.items():
                archive.writestr(name, payload)
    generated.write_bytes(result.getvalue())
