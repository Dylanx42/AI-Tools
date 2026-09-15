from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import cast
from xml.etree import ElementTree
from zipfile import ZipFile

from openpyxl import load_workbook as _openpyxl_load_workbook
from openpyxl.workbook.workbook import Workbook

_STYLES_PART = "xl/styles.xml"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _namespace(tag: str) -> str | None:
    if not tag.startswith("{") or "}" not in tag:
        return None
    return tag[1:].split("}", 1)[0]


def _normalize_empty_fills(styles_xml: bytes) -> bytes | None:
    """Treat an empty OOXML fill as the semantically equivalent no-fill pattern.

    Excel and WPS tolerate ``<fill/>`` entries, but openpyxl rejects the entire
    workbook because a fill has no pattern or gradient child.  The normalization
    is applied only to an in-memory package used by RackCore; the selected source
    workbook is never rewritten while it is being opened or scanned.
    """

    root = ElementTree.fromstring(styles_xml)
    fills = next((item for item in root if _local_name(item.tag) == "fills"), None)
    if fills is None:
        return None

    namespace = _namespace(fills.tag)
    pattern_tag = f"{{{namespace}}}patternFill" if namespace else "patternFill"
    changed = False
    for fill in fills:
        if _local_name(fill.tag) != "fill" or len(fill):
            continue
        ElementTree.SubElement(fill, pattern_tag, {"patternType": "none"})
        changed = True

    if not changed:
        return None
    if namespace:
        ElementTree.register_namespace("", namespace)
    return cast(
        bytes,
        ElementTree.tostring(root, encoding="utf-8", xml_declaration=True),
    )


def _normalized_package(path: Path) -> BytesIO | None:
    with ZipFile(path) as source:
        try:
            styles_xml = source.read(_STYLES_PART)
        except KeyError:
            return None
        normalized_styles = _normalize_empty_fills(styles_xml)
        if normalized_styles is None:
            return None

        output = BytesIO()
        with ZipFile(output, "w") as target:
            target.comment = source.comment
            for member in source.infolist():
                payload = (
                    normalized_styles
                    if member.filename == _STYLES_PART
                    else source.read(member.filename)
                )
                target.writestr(member, payload)
        output.seek(0)
        return output


def load_xlsx_workbook(
    path: Path,
    *,
    read_only: bool = False,
    data_only: bool = False,
) -> Workbook:
    """Load an editable XLSX, tolerating Excel/WPS empty-fill style records."""

    normalized = _normalized_package(path)
    source: Path | BytesIO = normalized if normalized is not None else path
    return _openpyxl_load_workbook(
        source,
        read_only=read_only,
        data_only=data_only,
    )
