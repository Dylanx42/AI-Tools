"""Shared validation of user text before persisting projects or writing XLSX."""

from __future__ import annotations

import re

_ILLEGAL_XML_CHARACTERS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\uFFFE\uFFFF]")


def validate_excel_text(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("名称或设备文字不能为空。")
    if len(value) > 32_767:
        raise ValueError("名称或设备文字不能超过 Excel 的 32767 字符上限。")
    if _ILLEGAL_XML_CHARACTERS.search(value):
        raise ValueError("名称或设备文字含有 XLSX 不支持的控制字符。")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise ValueError("名称或设备文字含有无效的 Unicode 字符。") from error
