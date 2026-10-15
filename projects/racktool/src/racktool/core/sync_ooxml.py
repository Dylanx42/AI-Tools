"""Merge planned cells into original OOXML, preserving unrelated parts and extensions."""
from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from openpyxl.styles.stylesheet import Stylesheet
from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from racktool.core.ooxml import _normalize_empty_fills
from racktool.core.source_export import (
    CONTENT,
    MAIN,
    PACKAGE_REL,
    REL,
    _merge_styles,
    _resolve,
    _xml,
)

if TYPE_CHECKING:
    from racktool.core.sync import WriteAction

_Bounds = tuple[int, int, int, int]


def _bounds(a1: str) -> _Bounds:
    values = range_boundaries(a1)
    if any(value is None for value in values):
        raise ValueError("Safe Sync cannot patch a partial cell range")
    return cast(_Bounds, values)


def _overlap(left: _Bounds, right: _Bounds) -> bool:
    return not (left[2] < right[0] or right[2] < left[0] or left[3] < right[1] or right[3] < left[1])


def _contains(bounds: Sequence[_Bounds], coordinate: str) -> bool:
    row, col = coordinate_to_tuple(coordinate)
    return any(lo_col <= col <= hi_col and lo_row <= row <= hi_row
               for lo_col, lo_row, hi_col, hi_row in bounds)


def _spans(xml: bytes, name: str) -> list[re.Match[bytes]]:
    # Counts and references are checked against the XML parser before these spans are used.
    return list(re.finditer(rb"<(?P<tag>(?:[\w.-]+:)?" + name.encode()
                           + rb")\b[^>]*?(?:/\s*>|>.*?</(?P=tag)\s*>)", xml, re.DOTALL))


def _attribute(xml: bytes, name: str) -> str:
    opening = xml[:xml.index(b">") + 1]
    found = re.search(rb"\b" + name.encode() + rb"\s*=\s*(['\"])(.*?)\1", opening)
    if found is None:
        raise ValueError(f"Safe Sync OOXML is missing {name}")
    return found.group(2).decode("utf-8")


def _body(xml: bytes) -> tuple[bytes, bytes, bytes]:
    end = xml.index(b">") + 1
    opening = xml[:end]
    if opening.rstrip().endswith(b"/>"):
        tag = re.match(rb"<([\w:.-]+)", opening)
        assert tag is not None
        return opening.rstrip()[:-2] + b">", b"", b"</" + tag.group(1) + b">"
    closing = xml.rfind(b"</")
    if closing < end:
        raise ValueError("Safe Sync OOXML element has no closing tag")
    return opening, xml[end:closing], xml[closing:]


def _sheet_parts(parts: dict[str, bytes]) -> dict[str, str]:
    workbook = ET.fromstring(parts["xl/workbook.xml"])
    relationships = ET.fromstring(parts["xl/_rels/workbook.xml.rels"])
    targets = {item.attrib["Id"]: _resolve("xl/workbook.xml", item.attrib["Target"])
               for item in relationships if item.tag == f"{{{PACKAGE_REL}}}Relationship"
               and item.attrib.get("Type") == f"{REL}/worksheet"}
    sheets = workbook.find(f"{{{MAIN}}}sheets")
    if sheets is None:
        raise ValueError("Safe Sync workbook has no sheets")
    return {sheet.attrib["name"]: targets[sheet.attrib[f"{{{REL}}}id"]] for sheet in sheets}


def _style_sequence(styles: Any, name: str) -> list[Any]:
    sequence = getattr(styles, name)
    if hasattr(sequence, "xf"):
        sequence = sequence.xf
    elif hasattr(sequence, "dxf"):
        sequence = sequence.dxf
    return list(sequence or ())


def _xf_equivalent(left: Any, right: Any, old: Any, new: Any, *, preserve_base: bool = False) -> bool:
    # OOXML cell XF apply flags are omitted by openpyxl. Keep original XFs raw;
    # new XFs may only refer to the same indexed objects, never remap an index.
    for name in ("numFmtId", "xfId", "alignment", "protection"):
        if getattr(left, name) != getattr(right, name):
            return False
    for identifier, collection in (("fontId", "fonts"), ("fillId", "fills"), ("borderId", "borders")):
        old_id, new_id = getattr(left, identifier), getattr(right, identifier)
        if old_id != new_id and getattr(old, collection)[old_id] != getattr(new, collection)[new_id]:
            return False
    for name in ("quotePrefix", "pivotButton"):
        if bool(getattr(left, name)) != bool(getattr(right, name)):
            return False
    for name in ("applyNumberFormat", "applyFont", "applyFill", "applyBorder"):
        if not preserve_base and getattr(left, name) is False and getattr(right, name) is not False:
            return False
    return True


def _preserved_styles(original: bytes, generated: bytes) -> bytes:
    normalized = _normalize_empty_fills(original) or original
    old = Stylesheet.from_tree(cast(Any, ET.fromstring(normalized)))
    new = Stylesheet.from_tree(cast(Any, ET.fromstring(generated)))
    for name in ("fonts", "fills", "borders", "cellStyleXfs", "cellXfs", "dxfs"):
        before, after = _style_sequence(old, name), _style_sequence(new, name)
        if len(after) < len(before) or (name == "cellStyleXfs" and len(after) != len(before)):
            raise ValueError(f"Safe Sync cannot preserve original {name} indices")
        for index, item in enumerate(before):
            # The entire original base-XF table remains raw and is never replaced
            # by the generated table. openpyxl drops its apply=False switches;
            # preserve those exact original flags, IDs and table size instead.
            matches = _xf_equivalent(item, after[index], old, new, preserve_base=name == "cellStyleXfs") if name in ("cellXfs", "cellStyleXfs") else item == after[index]
            if not matches:
                raise ValueError(f"Safe Sync cannot preserve original {name} index {index}")
    old_formats = {item.numFmtId: item.formatCode for item in old.numFmts.numFmt}
    for item in new.numFmts.numFmt:
        if old_formats.get(item.numFmtId) != item.formatCode:
            raise ValueError("Safe Sync cannot preserve custom number-format indices")
    # Excel/WPS accept empty fill records; normalize only those raw elements so
    # the written result can also be opened by plain openpyxl. Keep extensions raw.
    if _normalize_empty_fills(original) is not None:
        parsed_fills = ET.fromstring(original).find(f"{{{MAIN}}}fills")
        assert parsed_fills is not None
        parsed_fills.tail = None
        root_opening, _, root_closing = _body(_spans(original, "styleSheet")[0].group())
        containers = []
        for candidate in _spans(original, "fills"):
            try:
                parsed = ET.fromstring(root_opening + candidate.group() + root_closing).find(f"{{{MAIN}}}fills")
            except ET.ParseError:
                # An extension may use prefixes scoped outside this candidate.
                continue
            if parsed is not None and ET.tostring(parsed) == ET.tostring(parsed_fills):
                containers.append(candidate)
        if len(containers) != 1:
            raise ValueError("Safe Sync cannot identify the standard fills container")
        container = containers[0]
        fills_xml = container.group()
        matches = _spans(fills_xml, "fill")
        if len(matches) != len(parsed_fills) or any(child.tag != f"{{{MAIN}}}fill" for child in parsed_fills):
            raise ValueError("Safe Sync cannot preserve unknown fills container content")
        for match in reversed(matches):
            opening, body, closing = _body(match.group())
            if not body.strip():
                prefix = match.group("tag").removesuffix(b"fill")
                replacement = opening + b"<" + prefix + b"patternFill/>" + closing
                fills_xml = fills_xml[:match.start()] + replacement + fills_xml[match.end():]
        original = original[:container.start()] + fills_xml + original[container.end():]
    merged = _merge_styles(original, generated)
    output = Stylesheet.from_tree(cast(Any, ET.fromstring(_normalize_empty_fills(merged) or merged)))
    for name in ("fonts", "fills", "borders", "cellStyleXfs", "cellXfs", "dxfs"):
        if len(_style_sequence(output, name)) != len(_style_sequence(new, name)):
            raise ValueError(f"Safe Sync did not append the expected {name}")
    return merged


def _patch_row(raw: bytes, parsed: ET.Element, replacements: dict[str, bytes], bounds: Sequence[_Bounds]) -> bytes:
    opening, body, closing = _body(raw)
    cells = _spans(body, "c")
    parsed_cells = list(parsed)
    if len(cells) != len(parsed_cells) or any(cell.tag != f"{{{MAIN}}}c" for cell in parsed_cells):
        raise ValueError("Safe Sync cannot preserve unknown row content")
    leftovers = body
    for cell in reversed(cells):
        leftovers = leftovers[:cell.start()] + leftovers[cell.end():]
    if leftovers.strip():
        raise ValueError("Safe Sync cannot preserve non-cell row content")
    result: dict[str, bytes] = {}
    for match, element in zip(cells, parsed_cells, strict=True):
        coordinate = _attribute(match.group(), "r")
        if coordinate != element.attrib["r"] or coordinate in result:
            raise ValueError("Safe Sync encountered ambiguous cell XML")
        if not _contains(bounds, coordinate):
            result[coordinate] = match.group()
    result.update(replacements)
    ordered = sorted(result.items(), key=lambda pair: coordinate_to_tuple(pair[0])[1])
    return opening + b"".join(cell for _, cell in ordered) + leftovers + closing


def _patch_sheet_data(original: bytes, compiled: bytes, bounds: Sequence[_Bounds]) -> bytes:
    old_root, new_root = ET.fromstring(original), ET.fromstring(compiled)
    old_data, new_data = old_root.find(f"{{{MAIN}}}sheetData"), new_root.find(f"{{{MAIN}}}sheetData")
    spans = _spans(original, "sheetData")
    if old_data is None or new_data is None or len(spans) != 1:
        raise ValueError("Safe Sync cannot identify worksheet cell data")
    data_span = spans[0]
    opening, body, closing = _body(data_span.group())
    row_spans = _spans(body, "row")
    if len(row_spans) != len(old_data):
        raise ValueError("Safe Sync cannot identify worksheet row XML")
    desired: dict[int, dict[str, bytes]] = defaultdict(dict)
    for row in new_data:
        for cell in row:
            coordinate = cell.attrib.get("r", "")
            if _contains(bounds, coordinate):
                if cell.attrib.get("t") == "s":
                    raise ValueError("Patched cells cannot use generated shared-string indices")
                desired[int(row.attrib["r"])][coordinate] = _xml(cell)
    touched_rows = {row for _, lo_row, _, hi_row in bounds for row in range(lo_row, hi_row + 1)}
    rows: dict[int, bytes] = {}
    for span, parsed in zip(row_spans, old_data, strict=True):
        number = int(_attribute(span.group(), "r"))
        if parsed.tag != f"{{{MAIN}}}row" or str(number) != parsed.attrib["r"] or number in rows:
            raise ValueError("Safe Sync encountered ambiguous row XML")
        rows[number] = (_patch_row(span.group(), parsed, desired.pop(number, {}), bounds)
                        if number in touched_rows else span.group())
    for number, replacements in desired.items():
        row = ET.Element(f"{{{MAIN}}}row", {"r": str(number)})
        raw = _xml(row)
        row_opening, _, row_closing = _body(raw)
        rows[number] = row_opening + b"".join(value for _, value in sorted(
            replacements.items(), key=lambda pair: coordinate_to_tuple(pair[0])[1])) + row_closing
    leftovers = body
    for span in reversed(row_spans):
        leftovers = leftovers[:span.start()] + leftovers[span.end():]
    if leftovers.strip():
        raise ValueError("Safe Sync cannot preserve non-row worksheet data")
    patched = opening + b"".join(rows[number] for number in sorted(rows)) + leftovers + closing
    return original[:data_span.start()] + patched + original[data_span.end():]


def _patch_merges(original: bytes, compiled: bytes, bounds: Sequence[_Bounds]) -> bytes:
    old_root, new_root = ET.fromstring(original), ET.fromstring(compiled)
    old_merges, new_merges = old_root.find(f"{{{MAIN}}}mergeCells"), new_root.find(f"{{{MAIN}}}mergeCells")
    kept: list[bytes] = []
    spans = _spans(original, "mergeCells")
    if old_merges is not None:
        if len(spans) != 1:
            raise ValueError("Safe Sync cannot identify original merge XML")
        opening, body, closing = _body(spans[0].group())
        matches = _spans(body, "mergeCell")
        if len(matches) != len(old_merges):
            raise ValueError("Safe Sync cannot identify merged ranges")
        for match, merged in zip(matches, old_merges, strict=True):
            reference = _attribute(match.group(), "ref")
            if reference != merged.attrib["ref"]:
                raise ValueError("Safe Sync merge reference does not match its XML")
            if not any(_overlap(_bounds(reference), area) for area in bounds):
                kept.append(match.group())
    else:
        if spans:
            raise ValueError("Safe Sync merge XML is ambiguous")
        opening, closing = f'<mergeCells xmlns="{MAIN}">'.encode(), b"</mergeCells>"
    if new_merges is not None:
        for merged in new_merges:
            if any(_overlap(_bounds(merged.attrib["ref"]), area) for area in bounds):
                kept.append(_xml(merged))
    count = f'count="{len(kept)}"'.encode()
    if re.search(rb"\bcount\s*=\s*(['\"])\d+\1", opening):
        opening = re.sub(rb"\bcount\s*=\s*(['\"])\d+\1", count, opening)
    else:
        opening = opening[:-1] + b" " + count + b">"
    replacement = opening + b"".join(kept) + closing
    if spans:
        return original[:spans[0].start()] + replacement + original[spans[0].end():]
    if not kept:
        return original
    # mergeCells follows sheetProtection, autoFilter, sortState and customSheetViews.
    following = re.search(rb"<(?:[\w.-]+:)?(?:phoneticPr|conditionalFormatting|dataValidations|hyperlinks|printOptions|pageMargins|pageSetup|headerFooter|rowBreaks|colBreaks|customProperties|cellWatches|ignoredErrors|smartTags|drawing|legacyDrawing|picture|oleObjects|controls|webPublishItems|tableParts|extLst)\b", original)
    insertion = following.start() if following is not None else original.rfind(b"</")
    return original[:insertion] + replacement + original[insertion:]


def _append_child(xml: bytes, root: str, child: bytes) -> bytes:
    matches = _spans(xml, root)
    if len(matches) != 1:
        raise ValueError(f"Safe Sync cannot identify {root} XML")
    span = matches[0]
    opening, body, closing = _body(span.group())
    return xml[:span.start()] + opening + body + child + closing + xml[span.end():]


def _styles_part(parts: dict[str, bytes]) -> str | None:
    relationships = ET.fromstring(parts["xl/_rels/workbook.xml.rels"])
    matching = [item for item in relationships if item.attrib.get("Type") == f"{REL}/styles"]
    if len(matching) > 1:
        raise ValueError("Safe Sync found ambiguous styles relationships")
    if not matching:
        return None
    return _resolve("xl/workbook.xml", matching[0].attrib["Target"])


def _styles_updates(originals: dict[str, bytes], compiled: dict[str, bytes]) -> tuple[str, dict[str, bytes]]:
    old_part, new_part = _styles_part(originals), _styles_part(compiled)
    if new_part is None:
        raise ValueError("Safe Sync generated no styles part")
    if old_part is not None:
        return old_part, {old_part: _preserved_styles(originals[old_part], compiled[new_part])}
    part = "xl/styles.xml"
    index = 1
    while part in originals:
        part = f"xl/racktoolStyles{index}.xml"
        index += 1
    relationships = ET.fromstring(originals["xl/_rels/workbook.xml.rels"])
    identifiers = {item.attrib["Id"] for item in relationships}
    identifier = "rIdRackToolStyles"
    while identifier in identifiers:
        identifier += "_"
    relation = ET.Element(f"{{{PACKAGE_REL}}}Relationship", {
        "Id": identifier, "Type": f"{REL}/styles", "Target": "/" + part,
    })
    content = ET.Element(f"{{{CONTENT}}}Override", {
        "PartName": "/" + part,
        "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
    })
    return part, {part: compiled[new_part],
                  "xl/_rels/workbook.xml.rels": _append_child(originals["xl/_rels/workbook.xml.rels"], "Relationships", _xml(relation)),
                  "[Content_Types].xml": _append_child(originals["[Content_Types].xml"], "Types", _xml(content))}


def preserve_writeback_package(original_path: Path, generated_path: Path, actions: Sequence[WriteAction]) -> None:
    """Patch a temporary workbook against its immutable backup; never modify source."""
    affected: dict[str, list[_Bounds]] = defaultdict(list)
    for action in actions:
        if action.operation != "add":
            affected[action.source_sheet_name or action.sheet_name].append(_bounds(action.old_range))
        affected[action.sheet_name].append(_bounds(action.new_range))
    with ZipFile(original_path) as source, ZipFile(generated_path) as generated:
        originals = {info.filename.replace("\\", "/"): source.read(info) for info in source.infolist() if not info.is_dir()}
        compiled = {info.filename.replace("\\", "/"): generated.read(info) for info in generated.infolist() if not info.is_dir()}
        original_sheets, generated_sheets = _sheet_parts(originals), _sheet_parts(compiled)
        if list(original_sheets) != list(generated_sheets):
            raise ValueError("Safe Sync cannot change the worksheet list")
        styles_part, updates = _styles_updates(originals, compiled)
        for name, bounds in affected.items():
            old_part, new_part = original_sheets[name], generated_sheets[name]
            patched = _patch_sheet_data(originals[old_part], compiled[new_part], bounds)
            patched = _patch_merges(patched, compiled[new_part], bounds)
            result = ET.fromstring(patched)
            cell_styles = ET.fromstring(updates[styles_part]).find(f"{{{MAIN}}}cellXfs")
            cell_style_count = len(cell_styles) if cell_styles is not None else 0
            for cell in result.iter(f"{{{MAIN}}}c"):
                if int(cell.attrib.get("s", "0")) >= cell_style_count:
                    raise ValueError("Safe Sync patched cell references an invalid style index")
            updates[old_part] = patched
        output = BytesIO()
        with ZipFile(output, "w") as target:
            target.comment = source.comment
            for info in source.infolist():
                canonical = info.filename.replace("\\", "/")
                target.writestr(info, updates.get(canonical, source.read(info)))
            for name, payload in updates.items():
                if name not in originals:
                    target.writestr(name, payload)
    generated_path.write_bytes(output.getvalue())
